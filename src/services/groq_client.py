import json
import re
import ssl
import urllib.error
import urllib.request

import certifi

from src.config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL

# Groq is fronted by Cloudflare, which blocks the default urllib User-Agent
# (HTTP 403 / error 1010). Verify TLS against certifi's CA bundle so the call
# does not depend on the machine's system certificate store.
_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
_USER_AGENT = "provenance-guard/0.1"


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
            "ai_likelihood": 0.5,
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
                "content": (
                    "You are a careful, well-calibrated detector of AI-generated writing. "
                    "Use the full 0-1 range and base the score on concrete evidence such as "
                    "generic or formulaic phrasing, lack of personal voice, and uniform structure "
                    "(higher) versus specificity, personal experience, and natural irregularity (lower). "
                    "Formal, academic, or domain-expert writing is NOT by itself evidence of AI. "
                    "Score it high only when it is ALSO generic, hedging, or filler-heavy (e.g. 'paradigm shift', "
                    "'it is important to note', 'furthermore, stakeholders must collaborate') rather than conveying "
                    "specific, substantive domain knowledge. "
                    "Do not systematically under-score; genuinely AI-like text should score high."
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }
        # Note: On trial 3, I updated the system prompt to emphasize that formal, academic, or
        # domain-expert writing is not by itself evidence of AI, and that high scores
        # should only be given when the text is ALSO generic, hedging, or filler-heavy
        # rather than conveying specific, substantive domain knowledge.
        #  "content": (
        #             "You are a careful, well-calibrated detector of AI-generated writing. "
        #             "Use the full 0-1 range and base the score on concrete evidence such as "
        #             "generic or formulaic phrasing, lack of personal voice, and uniform structure "
        #             "(higher) versus specificity, personal experience, and natural irregularity (lower). "
        #             "Formal, academic, or domain-expert writing is NOT by itself evidence of AI. "
        #             "Score it high only when it is ALSO generic, hedging, or filler-heavy (e.g. 'paradigm shift', "
        #             "'it is important to note', 'furthermore, stakeholders must collaborate') rather than conveying "
        #             "specific, substantive domain knowledge. "
        #             "Do not systematically under-score; genuinely AI-like text should score high."
        #         ),

    request = urllib.request.Request(
        GROQ_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": _USER_AGENT,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=25, context=_SSL_CONTEXT) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": False,
            "ai_likelihood": 0.5,
            "error": f"Groq HTTP error: {exc.code}",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": False,
            "ai_likelihood": 0.5,
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
            "ai_likelihood": ai_likelihood,
            "rationale": parsed.get("rationale", ""),
        }
    except Exception:  # noqa: BLE001
        fallback_value = _extract_first_float(str(body))
        return {
            "name": "groq_llama_3_3_70b",
            "model": GROQ_MODEL,
            "available": fallback_value is not None,
            "ai_likelihood": fallback_value if fallback_value is not None else 0.5,
            "error": "Could not parse model JSON response",
        }
