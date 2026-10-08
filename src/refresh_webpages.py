#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import html
import re
import ssl
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "data" / "processed" / "sources_manifest.csv"

BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "ul",
    "ol",
    "table",
    "thead",
    "tbody",
    "tr",
    "blockquote",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "br",
}
SKIP_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "form",
    "button",
    "input",
    "select",
    "option",
    "header",
    "footer",
    "nav",
    "aside",
}
NOISE_PATTERNS = [
    re.compile(r"^(skip to main content|skip to content)$", re.I),
    re.compile(r"^(menu|close menu|search|open search|toggle search)$", re.I),
    re.compile(r"^(apply|give|visit|directory|campus map|myumb|events)$", re.I),
    re.compile(r"^(students|faculty staff|alumni|parents|news|about)$", re.I),
    re.compile(r"^(facebook|instagram|linkedin|youtube|x|twitter)$", re.I),
    re.compile(r"^(back to top)$", re.I),
    re.compile(r"^(copyright|all rights reserved).*$", re.I),
]
MAIN_FRAGMENT_PATTERNS = [
    re.compile(r"(?is)<main\b[^>]*>(.*?)</main>"),
    re.compile(r"(?is)<article\b[^>]*>(.*?)</article>"),
    re.compile(r'(?is)<div\b[^>]*id=["\']main-content["\'][^>]*>(.*?)</div>'),
    re.compile(r'(?is)<div\b[^>]*id=["\']content["\'][^>]*>(.*?)</div>'),
    re.compile(
        r'(?is)<div\b[^>]*class=["\'][^"\']*(?:page-content|main-content|content|entry-content|region-content)[^"\']*["\'][^>]*>(.*?)</div>'
    ),
    re.compile(r"(?is)<body\b[^>]*>(.*?)</body>"),
]


def normalize_whitespace(text: str | None) -> str:
    if text is None:
        return ""
    normalized = text.replace("\r", "")
    normalized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def get_webpage_rows(manifest_path: Path, source_ids: set[str]) -> list[dict[str, str]]:
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    filtered = [
        row
        for row in rows
        if row.get("source_type") == "webpage" and row.get("dedup_status") != "duplicate"
    ]
    if source_ids:
        filtered = [row for row in filtered if row.get("source_id", "").strip() in source_ids]
    return filtered


def get_html_title(html_text: str) -> str:
    match = re.search(r"(?is)<title\b[^>]*>(.*?)</title>", html_text)
    if not match:
        return ""
    return normalize_whitespace(html.unescape(match.group(1)))


def get_main_fragment(html_text: str) -> str:
    for pattern in MAIN_FRAGMENT_PATTERNS:
        match = pattern.search(html_text)
        if match:
            return match.group(1)
    return html_text


class SnapshotTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        tag = tag.lower()
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS or tag == "li":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def should_skip_line(line: str) -> bool:
    lowered = line.lower()
    return any(pattern.match(lowered) for pattern in NOISE_PATTERNS)


def convert_html_to_lines(html_text: str) -> list[str]:
    fragment = get_main_fragment(html_text)
    extractor = SnapshotTextExtractor()
    extractor.feed(fragment)
    extractor.close()

    working = extractor.get_text().replace("\xa0", " ")
    lines: list[str] = []
    last_line = ""
    for raw_line in working.splitlines():
        line = normalize_whitespace(raw_line)
        if not line:
            continue
        if should_skip_line(line):
            continue
        if line == last_line:
            continue
        lines.append(line)
        last_line = line
    return lines


def build_snapshot_markdown(html_text: str, source_url: str, snapshot_title: str | None) -> str:
    title = snapshot_title.strip() if snapshot_title else ""
    if not title:
        title = get_html_title(html_text) or source_url

    lines = convert_html_to_lines(html_text)
    if not lines:
        lines = ["No extractable text was found during refresh."]

    markdown_lines = [
        f"# {title} Snapshot",
        "",
        f"Source URL: {source_url}",
        f"Captured: {__import__('datetime').date.today().isoformat()}",
        f"Title: {title}",
        "",
        "Content",
        "",
        *lines,
        "",
    ]
    return "\n".join(markdown_lines)


def is_safe_public_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
    except (ValueError, TypeError):
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    return bool(parsed.netloc)


def fetch_html(url: str, timeout_seconds: int) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SSL-Project-Refresh/1.0)",
            "Accept-Language": "en-US,en;q=0.8",
        },
    )
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read()
    return body.decode(charset, errors="replace")


def refresh_rows(rows: Iterable[dict[str, str]], timeout_seconds: int, dry_run: bool) -> tuple[int, list[str]]:
    updated = 0
    failures: list[str] = []

    for row in rows:
        source_id = row.get("source_id", "").strip()
        source_url = row.get("source_url", "").strip()
        local_path = row.get("local_path", "").strip()
        title = row.get("title", "").strip()

        if not source_url:
            failures.append(f"{source_id}: missing source_url in manifest")
            continue
        if not is_safe_public_http_url(source_url):
            failures.append(f"{source_id}: only http/https URLs with a host are allowed")
            continue
        if not local_path:
            failures.append(f"{source_id}: missing local_path in manifest")
            continue

        snapshot_path = resolve_project_path(local_path)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)

        if dry_run:
            print(f"[DRY RUN] {source_url} -> {snapshot_path}")
            continue

        print(f"Refreshing {source_id} from {source_url}")
        try:
            html_text = fetch_html(source_url, timeout_seconds)
            snapshot_text = build_snapshot_markdown(html_text, source_url, title)
            snapshot_path.write_text(snapshot_text, encoding="utf-8")
            updated += 1
            print(f"Updated snapshot: {snapshot_path}")
        except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as exc:
            failures.append(f"{source_id}: {exc}")
            print(f"WARNING: Failed to refresh {source_id}: {exc}", file=sys.stderr)

    return updated, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh manifest-driven SSL webpage snapshots using Python."
    )
    parser.add_argument(
        "--source-id",
        action="append",
        default=[],
        help="Refresh only the specified source_id. May be repeated.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="HTTP timeout for each page request.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show which snapshots would be refreshed without writing files.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to the source manifest CSV.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest if args.manifest.is_absolute() else resolve_project_path(str(args.manifest))
    rows = get_webpage_rows(manifest_path, {item.strip() for item in args.source_id if item.strip()})

    if not rows:
        print("No matching webpage rows were found in the manifest.", file=sys.stderr)
        return 1

    updated, failures = refresh_rows(rows, args.timeout_seconds, args.dry_run)
    if args.dry_run:
        print(f"Dry run complete. Matched {len(rows)} webpage sources.")
        return 0

    print(f"Refreshed {updated} webpage snapshots.")
    if failures:
        print("Webpage refresh completed with failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
