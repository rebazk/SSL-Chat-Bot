"""Copy eval/metrics_snapshot.json into docs/metrics_visuals.html embedded block."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "eval" / "metrics_snapshot.json"
HTML_PATH = ROOT / "docs" / "metrics_visuals.html"


def main() -> int:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    blob = json.dumps(data, separators=(",", ":"))
    html = HTML_PATH.read_text(encoding="utf-8")
    pattern = re.compile(
        r'(<script type="application/json" id="metrics-embedded">)(.*?)(</script>)',
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        print("Could not find metrics-embedded block in metrics_visuals.html", file=sys.stderr)
        return 1

    def _inject(m: re.Match[str]) -> str:
        return m.group(1) + blob + m.group(3)

    new_html = pattern.sub(_inject, html, count=1)
    HTML_PATH.write_text(new_html, encoding="utf-8")
    print(f"Updated embedded metrics ({len(blob)} chars) in {HTML_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
