from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import threading
from collections import OrderedDict, deque
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from llm_answer import is_insufficient_llm_response, is_low_quality_llm_response, summarize_with_llm


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKER_SCRIPT = PROJECT_ROOT / "src" / "BeaconWorker.ps1"
CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.jsonl"
SEARCH_INDEX_CACHE_PATH = PROJECT_ROOT / "data" / "processed" / "search_index.clixml"
QUESTION_LIMIT = 400
MAX_BODY_BYTES = 64 * 1024
TOP_MIN = 1
TOP_MAX = 25
CACHE_MAX_ENTRIES = 128
WORKER_READ_TIMEOUT_SEC = 120.0
SESSION_MAX_ENTRIES = 128
SESSION_TURN_LIMIT = 5
SESSION_ID_MAX_LENGTH = 64
MAX_ANSWER_WORDS = 80
MAX_ANSWER_SENTENCES = 2


PII_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    re.compile(r"\b(?:passport|driver'?s?\s+license|bank account|routing number|social security|ssn)\b", re.IGNORECASE),
    re.compile(r"\b(?:my|our)\s+(?:email|phone|address|ssn|social security|date of birth|dob)\s+(?:is|:)\b", re.IGNORECASE),
)

SSL_CONTEXT_PATTERN = re.compile(
    r"\b("
    r"ssl|sustainable solutions lab|umass boston|climate justice|climate resilience|"
    r"east boston|mvp program|resilience|environmental justice|"
    r"who counts in climate resilience|northeast climate justice"
    r")\b",
    re.IGNORECASE,
)

FOLLOW_UP_CUE_PATTERN = re.compile(
    r"^(and|also|what about|how about|can you|could you|do they|does it|is it|that|those|these|it)\b",
    re.IGNORECASE,
)

FOLLOW_UP_PRONOUN_PATTERN = re.compile(
    r"\b(it|that|those|these|they|them|its|their|this)\b",
    re.IGNORECASE,
)
FOLLOW_UP_ROLE_PATTERN = re.compile(
    r"^\s*who\s+is\s+(the\s+)?(current|associate|research)\s+director\??\s*$",
    re.IGNORECASE,
)
# Short staff/role questions without "SSL" in the text; allow when session memory exists.
FOLLOW_UP_STAFF_WHO_PATTERN = re.compile(
    r"^\s*who\s+is\s+(the\s+)?("
    r"community\s+engagement\s+manager|"
    r"dean(\s+of\s+faculty)?(\s+and\s+inter-faculty\s+initiatives)?(\s+at\s+ssl)?"
    r")\b",
    re.IGNORECASE,
)

SESSION_ID_SAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")

SESSION_MEMORY_LOCK = threading.Lock()
SESSION_MEMORY: OrderedDict[str, deque[dict[str, str]]] = OrderedDict()


def _contains_sensitive_personal_info(question: str) -> bool:
    compact = " ".join(question.split())
    return any(pattern.search(compact) for pattern in PII_PATTERNS)


def _is_ssl_in_scope(question: str) -> bool:
    return bool(SSL_CONTEXT_PATTERN.search(question))


def _looks_like_follow_up(question: str) -> bool:
    compact = " ".join(question.split())
    if not compact:
        return False
    if FOLLOW_UP_ROLE_PATTERN.match(compact):
        return True
    if FOLLOW_UP_STAFF_WHO_PATTERN.search(compact):
        return True
    if FOLLOW_UP_CUE_PATTERN.search(compact):
        return True
    # If the user explicitly names SSL/topic context, treat it as a standalone ask.
    if _is_ssl_in_scope(compact):
        return False
    return len(compact) <= 120 and bool(FOLLOW_UP_PRONOUN_PATTERN.search(compact))


def _should_skip_llm_rewrite(resolved_question: str) -> bool:
    """Keep extractive pipeline answers for staff/role questions — LLM polish can drop exact names/titles."""
    rq = str(resolved_question or "").lower()
    return bool(
        re.search(
            r"\b(research|associate|current|executive)\s+director\b|"
            r"\bdirector\b.*\bssl\b|\bssl\b.*\bdirector\b|"
            r"\bcommunity\s+engagement\s+manager\b|"
            r"\bdean\s+of\s+faculty\b|"
            r"\binter-faculty\s+initiatives\b|"
            r"\bssl\s+staff\b.*\broles\b|"
            r"\bstaff\b.*\broles\b",
            rq,
        )
    )


def _sanitize_session_id(raw: str) -> str:
    compact = SESSION_ID_SAFE_PATTERN.sub("", str(raw or "").strip())
    return compact[:SESSION_ID_MAX_LENGTH]


def _get_session_history(session_id: str) -> list[dict[str, str]]:
    if not session_id:
        return []
    with SESSION_MEMORY_LOCK:
        history = SESSION_MEMORY.get(session_id)
        if not history:
            return []
        SESSION_MEMORY.move_to_end(session_id)
        return [dict(turn) for turn in history]


def _append_session_turn(session_id: str, question: str, answer: str) -> None:
    if not session_id:
        return
    with SESSION_MEMORY_LOCK:
        history = SESSION_MEMORY.get(session_id)
        if history is None:
            history = deque(maxlen=SESSION_TURN_LIMIT)
            SESSION_MEMORY[session_id] = history
        history.append({"question": question, "answer": answer})
        SESSION_MEMORY.move_to_end(session_id)
        while len(SESSION_MEMORY) > SESSION_MAX_ENTRIES:
            SESSION_MEMORY.popitem(last=False)


def _canonicalize_worker_question(resolved: str) -> str:
    """Map fragile short phrasings to a retrieval-stable question the worker already handles well."""
    compact = " ".join(str(resolved or "").split())
    if re.fullmatch(r"(?i)what is ssl about\??", compact):
        return "What is the Sustainable Solutions Lab, and what does it focus on?"
    if re.fullmatch(r"(?i)what'?s ssl about\??", compact):
        return "What is the Sustainable Solutions Lab, and what does it focus on?"
    return str(resolved or "").strip()


def _resolve_question_with_history(question: str, history: list[dict[str, str]]) -> tuple[str, bool]:
    if not history or not _looks_like_follow_up(question):
        return question, False
    prior_question = str(history[-1].get("question") or "").strip()
    if not prior_question:
        return question, False

    # Targeted follow-up expansions keep retrieval stable and reduce drift.
    if re.search(
        r"\b(funding|finance|financing|budget|money|revenue|grants?)\b",
        question,
        re.IGNORECASE,
    ):
        return "What kinds of funding mechanisms are discussed in SSL's climate resilience financing work?", True

    # Keep follow-up rewrites lightweight so lexical retrieval stays focused on the new ask.
    prior_is_general = bool(
        re.search(
            r"\b(what does .* focus on|what is ssl\b|what is the sustainable solutions lab|"
            r"tell me about ssl|what does ssl\b|overview|mission|purpose)\b",
            prior_question,
            re.IGNORECASE,
        )
    )
    if _is_ssl_in_scope(question):
        resolved = question
    elif prior_is_general:
        resolved = f"For the Sustainable Solutions Lab (SSL), {question}"
    else:
        resolved = f"In the same SSL context as '{prior_question}', {question}"
    return resolved, True


def _guardrail_response(question: str, *, has_recent_context: bool = False) -> dict | None:
    if _contains_sensitive_personal_info(question):
        return {
            "question": question,
            "answer": "I cannot process personal or sensitive information. Please ask a general SSL question.",
            "supported": False,
            "citations": [],
            "top_results": [],
            "guardrail": "personal_information_denied",
        }

    if not _is_ssl_in_scope(question):
        if has_recent_context and _looks_like_follow_up(question):
            return None
        return {
            "question": question,
            "answer": "This assistant only answers public SSL questions. Please rephrase in SSL context.",
            "supported": False,
            "citations": [],
            "top_results": [],
            "guardrail": "out_of_scope_denied",
        }

    return None


def get_powershell_command() -> list[str]:
    pwsh = shutil.which("pwsh")
    if pwsh:
        return [pwsh, "-NoProfile", "-File"]

    powershell = shutil.which("powershell")
    if powershell:
        return [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"]

    raise RuntimeError("Neither 'pwsh' nor 'powershell' was found in PATH.")


def _safe_http_url(url: str) -> str:
    try:
        parsed = urlparse(url.strip())
    except (ValueError, TypeError):
        return ""
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return url.strip()
    return ""


def _clean_display_text(value: str) -> str:
    text = str(value or "")
    text = text.replace("\ufeff", "")
    text = text.replace("\ufffd", "")
    text = re.sub(r"[\u200b-\u200f\u2060]", "", text)
    text = re.sub(r"\btheBoston\b", "the Boston", text)
    text = re.sub(r"\bfromvehicles\b", "from vehicles", text)
    text = re.sub(r"\bo cial\b", "official", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _sanitize_answer_payload(payload: dict) -> dict:
    out = dict(payload)
    for field in ("answer", "extractive_answer", "question", "resolved_question", "reason"):
        if field in out and out.get(field) is not None:
            out[field] = _clean_display_text(str(out.get(field)))

    top_results = out.get("top_results")
    if isinstance(top_results, list):
        cleaned: list[dict] = []
        for row in top_results:
            if isinstance(row, dict):
                row = dict(row)
                row["source_url"] = _safe_http_url(str(row.get("source_url") or ""))
                for field in ("title", "citation", "snippet", "text"):
                    if field in row and row.get(field) is not None:
                        row[field] = _clean_display_text(str(row.get(field)))
            cleaned.append(row)
        out["top_results"] = cleaned
    return out


def _enforce_concise_answer(answer: str) -> str:
    text = _clean_display_text(answer)
    if not text:
        return text

    # Prevent initials like "B. R." from being split into fake sentences.
    initial_token = "<INIT_DOT>"
    text_for_split = re.sub(r"\b([A-Z])\.\s+([A-Z])\.", rf"\1{initial_token}\2{initial_token}", text)

    sentence_candidates = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_for_split) if s.strip()]
    if sentence_candidates:
        text = " ".join(sentence_candidates[:MAX_ANSWER_SENTENCES])
        text = text.replace(initial_token, ". ")
        text = re.sub(r"\.\s+\.", ".", text)
        text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    if len(words) > MAX_ANSWER_WORDS:
        text = " ".join(words[:MAX_ANSWER_WORDS]).rstrip(" ,;:-")
        if text and text[-1] not in ".!?":
            text = f"{text}."

    return text


class BeaconBackend:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._cache: OrderedDict[tuple[str, int], dict] = OrderedDict()
        self._corpus_signature: tuple | None = None

    def ensure_started(self) -> None:
        with self._lock:
            self._refresh_if_stale()
            self._ensure_process()

    def is_ready(self) -> bool:
        process = self._process
        return process is not None and process.poll() is None

    def ask(self, question: str, top: int = 5) -> dict:
        top = max(TOP_MIN, min(int(top), TOP_MAX))
        cache_key = (question.strip().lower(), top)
        with self._lock:
            self._refresh_if_stale()
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                return _sanitize_answer_payload(self._cache[cache_key])

            self._ensure_process()
            assert self._process is not None
            assert self._process.stdin is not None
            assert self._process.stdout is not None

            request_payload = json.dumps({"question": question, "top": top}, separators=(",", ":"))
            self._process.stdin.write(f"{request_payload}\n")
            self._process.stdin.flush()

            stdout = self._process.stdout
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(stdout.readline)
                try:
                    response_line = future.result(timeout=WORKER_READ_TIMEOUT_SEC)
                except FutureTimeout:
                    self._restart_process()
                    raise RuntimeError("Beacon BOT worker timed out waiting for a response.") from None
            if not response_line:
                stderr = self._read_stderr()
                self._restart_process()
                message = stderr or "Beacon BOT backend stopped unexpectedly."
                raise RuntimeError(message)

            try:
                payload = self._parse_payload(response_line)
            except RuntimeError:
                self._restart_process()
                raise

            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))

            payload = _sanitize_answer_payload(payload)
            self._cache[cache_key] = payload
            while len(self._cache) > CACHE_MAX_ENTRIES:
                self._cache.popitem(last=False)
            return payload

    def _get_file_signature(self, path: Path) -> tuple[str, int, int] | tuple[str, None, None]:
        if not path.exists():
            return (str(path), None, None)

        stat = path.stat()
        return (str(path), stat.st_size, stat.st_mtime_ns)

    def _get_corpus_signature(self) -> tuple:
        return (
            self._get_file_signature(CHUNKS_PATH),
            self._get_file_signature(SEARCH_INDEX_CACHE_PATH),
        )

    def _refresh_if_stale(self) -> None:
        current_signature = self._get_corpus_signature()
        if self._corpus_signature is None:
            self._corpus_signature = current_signature
            return

        if current_signature == self._corpus_signature:
            return

        self._cache.clear()
        self._restart_process()
        self._corpus_signature = current_signature

    def _ensure_process(self) -> None:
        if self._process is not None and self._process.poll() is None:
            return

        command = get_powershell_command() + [str(WORKER_SCRIPT)]
        self._process = subprocess.Popen(
            command,
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

    def _parse_payload(self, raw_response: str) -> dict:
        candidates: list[str] = []
        cleaned = raw_response.strip().lstrip("\ufeff")
        if cleaned:
            candidates.append(cleaned)

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end >= start:
            extracted = cleaned[start : end + 1]
            if extracted and extracted not in candidates:
                candidates.append(extracted)

        last_error: json.JSONDecodeError | None = None
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError as exc:
                last_error = exc

        raise RuntimeError(f"Backend returned invalid JSON: {last_error}")

    def _read_stderr(self) -> str:
        process = self._process
        if process is None or process.stderr is None:
            return ""

        return process.stderr.read().strip()

    def _restart_process(self) -> None:
        process = self._process
        self._process = None

        if process is None:
            return

        try:
            process.kill()
        except OSError:
            pass
        finally:
            process.wait(timeout=5)


BACKEND = BeaconBackend()


class BeaconHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)

    def _discard_request_body(self, length: int) -> None:
        remaining = max(0, int(length))
        while remaining > 0:
            chunk = self.rfile.read(min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.path = "/ui/index.html"
        elif parsed.path == "/api/health":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            payload = {"ok": True, "backend_ready": BACKEND.is_ready()}
            self.wfile.write(json.dumps(payload).encode("utf-8"))
            return

        return super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/ask":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown API route.")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        if content_length > MAX_BODY_BYTES:
            self._discard_request_body(content_length)
            self.close_connection = True
            self.send_json(
                {"error": f"Request body must be {MAX_BODY_BYTES} bytes or fewer."},
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                connection_close=True,
            )
            return

        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Request body must be valid JSON."}, status=HTTPStatus.BAD_REQUEST)
            return

        question = str(payload.get("question", "")).strip()
        top = max(TOP_MIN, min(int(payload.get("top", 5) or 5), TOP_MAX))
        session_id = _sanitize_session_id(str(payload.get("session_id", "")))
        history = _get_session_history(session_id)

        if not question:
            self.send_json({"error": "A non-empty question is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        if len(question) > QUESTION_LIMIT:
            self.send_json(
                {"error": f"Questions must be {QUESTION_LIMIT} characters or fewer."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        guardrail_payload = _guardrail_response(question, has_recent_context=bool(history))
        if guardrail_payload is not None:
            if session_id:
                guardrail_payload["session_id"] = session_id
            self.send_json(guardrail_payload)
            return

        resolved_question, memory_applied = _resolve_question_with_history(question, history)
        resolved_question = _canonicalize_worker_question(resolved_question)

        try:
            answer_payload = BACKEND.ask(resolved_question, top=top)
        except Exception as exc:  # noqa: BLE001
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if (
            answer_payload.get("answer")
            and answer_payload.get("top_results")
            and not _should_skip_llm_rewrite(resolved_question)
        ):
            try:
                summary = summarize_with_llm(question=resolved_question, results=answer_payload.get("top_results", []))
            except Exception:  # noqa: BLE001
                summary = None

            if summary:
                if is_insufficient_llm_response(summary) or is_low_quality_llm_response(summary):
                    answer_payload["llm_used"] = False
                else:
                    answer_payload["extractive_answer"] = answer_payload.get("answer")
                    answer_payload["answer"] = summary
                    answer_payload["llm_used"] = True
            else:
                answer_payload["llm_used"] = False
        else:
            answer_payload["llm_used"] = False

        if answer_payload.get("answer"):
            answer_payload["answer"] = _enforce_concise_answer(str(answer_payload.get("answer")))

        answer_payload["question"] = question
        answer_payload["resolved_question"] = resolved_question
        answer_payload["memory_applied"] = memory_applied
        if session_id:
            answer_payload["session_id"] = session_id
            _append_session_turn(session_id, question, str(answer_payload.get("answer") or ""))

        self.send_json(_sanitize_answer_payload(answer_payload))

    def send_json(
        self, payload: dict, status: HTTPStatus = HTTPStatus.OK, *, connection_close: bool = False
    ) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        if connection_close:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the local Beacon BOT UI prototype.")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Host to bind (default 127.0.0.1). Using 0.0.0.0 exposes the UI and /api routes on all "
            "interfaces; only do this on trusted networks and behind appropriate controls."
        ),
    )
    parser.add_argument("--port", type=int, default=8765, help="Port to bind. Default: 8765")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    BACKEND.ensure_started()
    server = ThreadingHTTPServer((args.host, args.port), BeaconHandler)
    server_addr = f"http://{args.host}:{args.port}"
    print(f"Beacon BOT UI available at {server_addr}", flush=True)
    print("Beacon BOT backend warmed and ready.", flush=True)
    print("Press Ctrl+C to stop the server.", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Beacon BOT UI server.", flush=True)
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
