import argparse
import json
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "pypdf is required for extract_pdf_with_pypdf.py. Install it with 'python -m pip install --user pypdf'."
    ) from exc


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PDF text using pypdf.")
    parser.add_argument("--pdf-path", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    output_path = Path(args.output_path)

    reader = PdfReader(str(pdf_path))
    page_texts = []
    combined_parts = []

    for index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        page_texts.append(
            {
                "page_number": index,
                "text": text,
            }
        )
        if text:
            combined_parts.append(text)

    payload = {
        "page_count": len(page_texts),
        "page_texts": page_texts,
        "text": "\n\n".join(combined_parts).strip(),
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
