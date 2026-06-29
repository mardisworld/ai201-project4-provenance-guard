LABEL_VARIANTS = {
    "HIGH_CONFIDENCE_AI": "Transparency Notice: This content is likely AI-generated (high confidence: {{confidence}}%). If this is incorrect, the creator can submit an appeal for human review.",
    "HIGH_CONFIDENCE_HUMAN": "Transparency Notice: This content is likely human-written (high confidence: {{confidence}}%). If new evidence appears, this decision can still be re-reviewed.",
    "UNCERTAIN": "Transparency Notice: We could not confidently determine whether this content is AI-generated or human-written (current confidence: {{confidence}}%). No enforcement action is taken while the decision is uncertain.",
}


def render_label(template: str, confidence: float) -> str:
    percent = round(confidence * 100)
    return template.replace("{{confidence}}", str(percent))


def build_transparency_label(result: str, confidence: float) -> str:
    if result == "likely_ai":
        return render_label(LABEL_VARIANTS["HIGH_CONFIDENCE_AI"], confidence)

    if result == "likely_human":
        return render_label(LABEL_VARIANTS["HIGH_CONFIDENCE_HUMAN"], confidence)

    return render_label(LABEL_VARIANTS["UNCERTAIN"], confidence)