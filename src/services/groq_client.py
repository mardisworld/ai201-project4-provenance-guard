import json
import re
import urllib.error
import urllib.request

from src.config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL


def _extract_first_float(text: str) -> float | None:
    match = re.search(r"(0(?:\.\d+)?|1(?:\.0+)?)", text)
    if not match:
        return None
    value = float(match.group(1))
    return max(0.0, min(1.0, value))


def groq_ai_likelihood_signal(content: str) -> dict:
    if not GROQ_API_KEY:
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": False,
            "aiLikelihood": 0.5,
            "error": "GROQ_API_KEY is not set",
        }

    prompt = (
        "You are scoring writing provenance risk. "
        "Return ONLY compact JSON with keys ai_likelihood and rationale. "
        "ai_likelihood must be a float between 0 and 1 where 1 means very likely AI-generated and 0 means very likely human-written. "
        "Do not include markdown.\n\n"
        f"Content:\n{content}"
    )

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Score attribution risk conservatively to reduce false positive AI accusations.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    request = urllib.request.Request(
        GROQ_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": False,
            "aiLikelihood": 0.5,
            "error": f"Groq HTTP error: {exc.code}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": False,
            "aiLikelihood": 0.5,
            "error": f"Groq request failed: {str(exc)}",
        }

    try:
        content_text = body["choices"][0]["message"]["content"]
        parsed = json.loads(content_text)
        ai_likelihood = float(parsed["ai_likelihood"])
        ai_likelihood = max(0.0, min(1.0, ai_likelihood))
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": True,
            "aiLikelihood": ai_likelihood,
            "rationale": parsed.get("rationale", ""),
        }
    except Exception:  # noqa: BLE001
        fallback_value = _extract_first_float(str(body))
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": fallback_value is not None,
            "aiLikelihood": fallback_value if fallback_value is not None else 0.5,
            "error": "Could not parse model JSON response",
        }
