from __future__ import annotations

import os
from pathlib import Path

try:
    import requests
except ImportError:  # Optional dependency for LLM answer polish.
    requests = None

try:
    from dotenv import load_dotenv
except ImportError:  # Optional dependency; .env loading is skipped when unavailable.
    load_dotenv = None

_REPO_ROOT = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(_REPO_ROOT / ".env")

API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
URL = "https://openrouter.ai/api/v1/chat/completions"

# Model must reply starting with this prefix (case-insensitive) to trigger server-side fallback.
INSUFFICIENT_ANSWER_PREFIX = "not enough information"


def is_insufficient_llm_response(text: str) -> bool:
    return bool(text.strip()) and text.strip().lower().startswith(INSUFFICIENT_ANSWER_PREFIX)


def is_low_quality_llm_response(text: str) -> bool:
    cleaned = str(text or "").strip()
    if not cleaned:
        return True

    # Catch classic OCR/encoding artifacts and awkward tokenization.
    if "\ufffd" in cleaned:
        return True
    if "theBoston" in cleaned or "fromvehicles" in cleaned:
        return True
    if "  " in cleaned:
        return True

    spaced_letters = 0
    tokens = cleaned.split()
    for idx in range(len(tokens) - 2):
        a, b, c = tokens[idx], tokens[idx + 1], tokens[idx + 2]
        if len(a) == 1 and len(b) == 1 and len(c) >= 3 and a.isalpha() and b.isalpha() and c.isalpha():
            spaced_letters += 1
    if spaced_letters >= 1:
        return True

    return False


def summarize_with_llm(question: str, results: list) -> str | None:
    """Rewrite an answer from top retrieval rows using OpenRouter, or return None to keep extractive text."""
    if not API_KEY or requests is None:
        return None

    chunks: list[str] = []
    for row in results[:3]:
        if not isinstance(row, dict):
            continue
        chunk = row.get("snippet") or row.get("text") or row.get("content") or ""
        chunks.append(str(chunk))

    context = "\n\n".join(chunks).strip()
    if not context:
        return None

    prompt = f"""
You are answering questions about the Sustainable Solutions Lab (SSL) at UMass Boston.

Question: {question}

Here are retrieved passages from the SSL corpus:
{context}

Instructions:
- Use only the retrieved passages
- Do not use outside knowledge
- SSL refers to the Sustainable Solutions Lab
- Pay close attention to the question and answer exactly what is being asked
- If the question is about "who", focus on people, roles, or groups
- If the question is about "what", focus on topics or areas of work
- First give a general answer, then include specific details if relevant
- Combine information from multiple passages when available
- Summarize the full range of SSL's work when multiple aspects are mentioned
- Include all relevant mechanisms, topics, or examples from the text
- Keep important names and details from the text
- Write a clear 1-2 sentence answer
- Keep the answer concise (at most about 70 words)

If the passages clearly contain enough information, provide the answer.

If the passages do NOT contain enough information, respond ONLY with:
Not enough information in the retrieved SSL sources.
"""

    try:
        response = requests.post(
            URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 90,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None
