from __future__ import annotations

import json
import sys
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import serve_ui  # noqa: E402


def _serve(handler_class, host: str = "127.0.0.1"):
    server = serve_ui.ThreadingHTTPServer((host, 0), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class ServeUiApiTests(unittest.TestCase):
    def tearDown(self) -> None:
        if hasattr(self, "_server"):
            self._server.shutdown()
            self._server.server_close()

    def test_health_has_no_project_root(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        conn = HTTPConnection(host, port, timeout=5)
        conn.request("GET", "/api/health")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 200)
        raw = resp.read()
        body = json.loads(raw.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertIn("backend_ready", body)
        self.assertNotIn("project_root", body)
        conn.close()

    def test_ask_happy_path_sanitizes_source_url(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        fake = {
            "question": "Test?",
            "answer": "Answer.",
            "supported": True,
            "citations": [],
            "top_results": [
                {
                    "score": 1.0,
                    "citation": "c",
                    "source_id": "x",
                    "title": "t",
                    "source_type": "webpage",
                    "source_url": "javascript:alert(1)",
                    "page_number": None,
                    "snippet": "s",
                }
            ],
            "generated_at": "now",
        }

        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = dict(fake)
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What is SSL?", "top": 5}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        self.assertEqual(payload.get("answer"), "Answer.")
        rows = payload.get("top_results") or []
        self.assertEqual(rows[0].get("source_url"), "")

    def test_ask_sanitizes_mojibake_answer_text(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        fake = {
            "question": "Test?",
            "answer": "Ante l\ufffd?\ufffdi\ufffd\ufffd (Fall 2023 - Spring 2024)",
            "supported": True,
            "citations": [],
            "top_results": [],
            "generated_at": "now",
        }
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = dict(fake)
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What is SSL?", "top": 5}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        self.assertNotIn("\ufffd", payload.get("answer", ""))

    def test_ask_rejects_oversize_body(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        big = b"x" * (serve_ui.MAX_BODY_BYTES + 1)
        conn = HTTPConnection(host, port, timeout=5)
        conn.request(
            "POST",
            "/api/ask",
            body=big,
            headers={"Content-Type": "application/octet-stream", "Content-Length": str(len(big))},
        )
        resp = conn.getresponse()
        self.assertEqual(resp.status, 413)
        resp.read()
        conn.close()

    def test_ask_rejects_invalid_json(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        conn = HTTPConnection(host, port, timeout=5)
        conn.request(
            "POST",
            "/api/ask",
            body=b"{",
            headers={"Content-Type": "application/json", "Content-Length": "1"},
        )
        resp = conn.getresponse()
        self.assertEqual(resp.status, 400)
        resp.read()
        conn.close()

    def test_ask_clamps_top(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = {"answer": "ok", "supported": True, "citations": [], "top_results": []}
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What does SSL focus on?", "top": 9999}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            resp.read()
            conn.close()
        backend.ask.assert_called_once()
        _args, kwargs = backend.ask.call_args
        self.assertEqual(kwargs.get("top"), serve_ui.TOP_MAX)

    def test_ask_denies_sensitive_personal_information(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "My SSN is 123-45-6789, can SSL help me?"}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        backend.ask.assert_not_called()
        self.assertEqual(payload.get("guardrail"), "personal_information_denied")
        self.assertFalse(payload.get("supported"))

    def test_ask_denies_out_of_scope_questions(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "Who won last night's basketball game?"}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        backend.ask.assert_not_called()
        self.assertEqual(payload.get("guardrail"), "out_of_scope_denied")
        self.assertFalse(payload.get("supported"))

    def test_ask_allows_in_scope_ssl_question(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = {"answer": "ok", "supported": True, "citations": [], "top_results": []}
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What does the Sustainable Solutions Lab focus on?"}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            resp.read()
            conn.close()

        backend.ask.assert_called_once()

    def test_follow_up_uses_session_memory_context(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.side_effect = [
                {"answer": "SSL studies climate justice.", "supported": True, "citations": [], "top_results": []},
                {"answer": "It discusses financing approaches.", "supported": True, "citations": [], "top_results": []},
            ]

            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps(
                    {"question": "What does the Sustainable Solutions Lab focus on?", "session_id": "demo_session_1"}
                ),
                headers={"Content-Type": "application/json"},
            )
            first_resp = conn.getresponse()
            self.assertEqual(first_resp.status, 200)
            first_payload = json.loads(first_resp.read().decode("utf-8"))

            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What about funding?", "session_id": "demo_session_1"}),
                headers={"Content-Type": "application/json"},
            )
            second_resp = conn.getresponse()
            self.assertEqual(second_resp.status, 200)
            second_payload = json.loads(second_resp.read().decode("utf-8"))
            conn.close()

        self.assertFalse(first_payload.get("memory_applied"))
        self.assertTrue(second_payload.get("memory_applied"))
        self.assertEqual(second_payload.get("session_id"), "demo_session_1")
        self.assertEqual(backend.ask.call_count, 2)
        second_args, second_kwargs = backend.ask.call_args_list[1]
        self.assertIn("funding mechanisms", second_args[0].lower())
        self.assertIn("climate resilience financing", second_args[0].lower())
        self.assertEqual(second_kwargs.get("top"), 5)

    def test_ssl_about_short_form_canonicalized_for_worker(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = {
                "answer": "Climate justice and historically excluded communities.",
                "supported": True,
                "citations": [],
                "top_results": [],
                "generated_at": "now",
            }
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What is SSL about?", "top": 5}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        backend.ask.assert_called_once()
        asked = backend.ask.call_args[0][0]
        self.assertIn("Sustainable Solutions Lab", asked)
        self.assertIn("focus on", asked)
        self.assertEqual(payload.get("question"), "What is SSL about?")
        self.assertIn("focus on", str(payload.get("resolved_question") or ""))

    def test_follow_up_money_rewrites_to_financing_question(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.side_effect = [
                {"answer": "SSL studies climate justice.", "supported": True, "citations": [], "top_results": []},
                {"answer": "Mechanisms include bonds.", "supported": True, "citations": [], "top_results": []},
            ]
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps(
                    {"question": "What does SSL focus on?", "session_id": "demo_session_money"}
                ),
                headers={"Content-Type": "application/json"},
            )
            conn.getresponse().read()

            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "how about money?", "session_id": "demo_session_money"}),
                headers={"Content-Type": "application/json"},
            )
            conn.getresponse().read()
            conn.close()

        second_args, _ = backend.ask.call_args_list[1]
        self.assertIn("funding mechanisms", second_args[0].lower())

    def test_explicit_ssl_question_not_forced_as_follow_up(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.side_effect = [
                {"answer": "first", "supported": True, "citations": [], "top_results": []},
                {"answer": "second", "supported": True, "citations": [], "top_results": []},
            ]
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "Who is the current director of SSL?", "session_id": "sticky_1"}),
                headers={"Content-Type": "application/json"},
            )
            first_resp = conn.getresponse()
            self.assertEqual(first_resp.status, 200)
            first_resp.read()

            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps(
                    {"question": "What is the Sustainable Solutions Lab, and what does it focus on?", "session_id": "sticky_1"}
                ),
                headers={"Content-Type": "application/json"},
            )
            second_resp = conn.getresponse()
            self.assertEqual(second_resp.status, 200)
            second_payload = json.loads(second_resp.read().decode("utf-8"))
            conn.close()

        self.assertFalse(second_payload.get("memory_applied"))
        second_args, _second_kwargs = backend.ask.call_args_list[1]
        self.assertEqual(
            second_args[0],
            "What is the Sustainable Solutions Lab, and what does it focus on?",
        )

    def test_role_only_director_follow_up_uses_recent_context(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.side_effect = [
                {"answer": "first", "supported": True, "citations": [], "top_results": []},
                {"answer": "second", "supported": True, "citations": [], "top_results": []},
            ]
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "Who is the associate director of the SSL?", "session_id": "roles_1"}),
                headers={"Content-Type": "application/json"},
            )
            first_resp = conn.getresponse()
            self.assertEqual(first_resp.status, 200)
            first_resp.read()

            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "Who is the research director?", "session_id": "roles_1"}),
                headers={"Content-Type": "application/json"},
            )
            second_resp = conn.getresponse()
            self.assertEqual(second_resp.status, 200)
            second_payload = json.loads(second_resp.read().decode("utf-8"))
            conn.close()

        self.assertTrue(second_payload.get("memory_applied"))
        backend.ask.assert_called()

    def test_llm_low_quality_summary_falls_back_to_extractive(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend, patch.object(serve_ui, "summarize_with_llm") as summarize:
            backend.ask.return_value = {
                "answer": "Extractive answer.",
                "supported": True,
                "citations": [],
                "top_results": [{"snippet": "SSL focuses on climate justice and resilience.", "source_url": "https://www.umb.edu/ssl/"}],
            }
            summarize.return_value = "It is not an o cial document from theBoston."

            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What does SSL focus on?"}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        self.assertEqual(payload.get("answer"), "Extractive answer.")
        self.assertFalse(payload.get("llm_used"))

    def test_answer_is_trimmed_to_concise_length(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        long_answer = (
            "SSL focuses on climate justice research across sectors. "
            "It supports collaborative policy design with community and academic partners. "
            "It also includes additional detailed implementation notes that should not appear "
            "in the default concise answer card."
        )
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = {
                "answer": long_answer,
                "supported": True,
                "citations": [],
                "top_results": [],
            }
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "What does SSL focus on?"}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        answer = payload.get("answer", "")
        self.assertNotIn("additional detailed implementation notes", answer)
        self.assertLessEqual(answer.count("."), 2)

    def test_initials_not_truncated_by_concise_sentence_split(self) -> None:
        self._server = _serve(serve_ui.BeaconHandler)
        host, port = self._server.server_address
        with patch.object(serve_ui, "BACKEND") as backend:
            backend.ask.return_value = {
                "answer": "The SSL public pages list Dr. B. R. (Balakrishnan) Balachandran as the current director.",
                "supported": True,
                "citations": [],
                "top_results": [],
            }
            conn = HTTPConnection(host, port, timeout=5)
            conn.request(
                "POST",
                "/api/ask",
                body=json.dumps({"question": "Who is the current director of SSL?"}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            self.assertEqual(resp.status, 200)
            payload = json.loads(resp.read().decode("utf-8"))
            conn.close()

        answer = payload.get("answer", "")
        self.assertIn("Balachandran", answer)
        self.assertIn("Dr.", answer)

    def test_concise_split_preserves_name_diacritics_and_spacing(self) -> None:
        text = "The SSL public people page lists Rosalyn Negrón as research director."
        cleaned = serve_ui._enforce_concise_answer(text)
        self.assertIn("Rosalyn Negrón", cleaned)
        self.assertNotIn("Negr ón", cleaned)


if __name__ == "__main__":
    unittest.main()
