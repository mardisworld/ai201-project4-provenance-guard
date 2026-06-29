import re

from src.services.groq_client import groq_ai_likelihood_signal


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def get_words(text: str) -> list[str]:
    return re.findall(r"[a-z']+", text.lower())


def split_sentences(text: str) -> list[str]:
    segments = [segment.strip() for segment in re.split(r"[.!?]+", text) if segment.strip()]
    return segments or ([text.strip()] if text.strip() else [])


def stylometric_signal(text: str) -> dict:
    words = get_words(text)
    sentences = split_sentences(text)

    if not words:
        return {
            "name": "stylometric_heuristics",
            "aiLikelihood": 0.5,
            "components": {
                "lexicalDiversityRisk": 0.5,
                "sentenceBurstinessRisk": 0.5,
            },
        }

    unique_count = len(set(words))
    type_token_ratio = unique_count / len(words)
    lexical_diversity_risk = clamp(1 - type_token_ratio)

    sentence_lengths = [len(sentence.split()) for sentence in sentences] or [1]
    mean_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
    burstiness = (
        sum(abs(length - mean_sentence_length) for length in sentence_lengths)
        / max(1.0, len(sentence_lengths) * mean_sentence_length)
    )
    sentence_burstiness_risk = clamp(1 - burstiness)

    ai_likelihood = clamp(lexical_diversity_risk * 0.55 + sentence_burstiness_risk * 0.45)
    return {
        "name": "stylometric_heuristics",
        "aiLikelihood": ai_likelihood,
        "components": {
            "lexicalDiversityRisk": lexical_diversity_risk,
            "sentenceBurstinessRisk": sentence_burstiness_risk,
        },
    }


def classify_content(input_text: str) -> dict:
    text = normalize_whitespace(input_text)

    groq_signal = groq_ai_likelihood_signal(text)
    style_signal = stylometric_signal(text)

    groq_weight = 0.65 if groq_signal.get("available") else 0.0
    style_weight = 0.35 if groq_signal.get("available") else 1.0

    ai_likelihood = clamp(
        groq_weight * float(groq_signal["aiLikelihood"]) + style_weight * float(style_signal["aiLikelihood"])
    )

    # Confidence reflects both decisiveness and cross-signal agreement.
    distance_from_mid = abs(ai_likelihood - 0.5) * 2
    agreement = 1 - abs(float(groq_signal["aiLikelihood"]) - float(style_signal["aiLikelihood"]))
    confidence = clamp(0.35 + 0.45 * distance_from_mid + 0.20 * agreement)

    # False-positive AI labels are treated as more harmful, so AI threshold is stricter.
    if ai_likelihood >= 0.86 and confidence >= 0.75 and groq_signal.get("available"):
        result = "likely_ai"
    elif ai_likelihood <= 0.30 and confidence >= 0.70:
        result = "likely_human"
    else:
        result = "uncertain"

    if not groq_signal.get("available"):
        confidence = clamp(confidence * 0.75)
        result = "uncertain"

    return {
        "result": result,
        "confidence": clamp(confidence),
        "aiLikelihood": ai_likelihood,
        "signals": {
            "groqSignal": groq_signal,
            "stylometricSignal": style_signal,
            "weights": {
                "groq": groq_weight,
                "stylometric": style_weight,
            },
        },
    }