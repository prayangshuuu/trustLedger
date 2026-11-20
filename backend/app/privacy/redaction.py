"""PII redaction engine using Microsoft Presidio with Bangladeshi recognizers.

Redacts sensitive PII (Bangladeshi phone numbers, national IDs, account numbers)
prior to any external LLM invocation, in accordance with PLAN_CONTEXT.md §6.
"""

from functools import lru_cache
from typing import Any

import spacy
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine

# Bangladeshi mobile phone format: (+8801[3-9]XXXXXXXX, 8801[3-9]XXXXXXXX, 01[3-9]XXXXXXXX)
BD_PHONE_REGEX = r"(?:\+?880|0)?1[3-9]\d{8}\b"

# Bangladeshi National ID (NID) formats: 10-digit smart card, 13-digit, or 17-digit legacy
BD_NID_REGEX = r"\b(?:\d{10}|\d{13}|\d{17})\b"


class OfflineSpacyNlpEngine(SpacyNlpEngine):
    """Custom spaCy NLP engine using blank English model to avoid downloading 380MB models."""

    def __init__(self) -> None:
        super().__init__(models=[{"lang_code": "en", "model_name": "blank"}])

    def load(self) -> None:
        self.nlp = {"en": spacy.blank("en")}  # type: ignore[assignment]


@lru_cache(maxsize=1)
def get_analyzer_engine() -> AnalyzerEngine:
    """Initialize and configure Presidio AnalyzerEngine with custom BD recognizers."""
    engine = OfflineSpacyNlpEngine()
    analyzer = AnalyzerEngine(nlp_engine=engine)

    # 1. Custom Bangladeshi Phone Recognizer
    phone_pattern = Pattern(name="bd_phone_pattern", regex=BD_PHONE_REGEX, score=0.95)
    phone_recognizer = PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        patterns=[phone_pattern],
        supported_language="en",
    )
    analyzer.registry.add_recognizer(phone_recognizer)

    # 2. Custom Bangladeshi NID Recognizer
    nid_pattern = Pattern(name="bd_nid_pattern", regex=BD_NID_REGEX, score=0.85)
    nid_recognizer = PatternRecognizer(
        supported_entity="BD_NID",
        patterns=[nid_pattern],
        supported_language="en",
    )
    analyzer.registry.add_recognizer(nid_recognizer)

    return analyzer


@lru_cache(maxsize=1)
def get_anonymizer_engine() -> AnonymizerEngine:
    """Initialize Presidio AnonymizerEngine singleton."""
    return AnonymizerEngine()  # type: ignore[no-untyped-call]


def redact_pii(text: str) -> str:
    """Scrub PII from text before passing to external LLMs.

    Replaces detected entities with generic anonymized tokens like <PHONE_NUMBER>, <BD_NID>.
    """
    if not text or not text.strip():
        return text

    try:
        analyzer = get_analyzer_engine()
        anonymizer = get_anonymizer_engine()

        results = analyzer.analyze(
            text=text,
            entities=["PHONE_NUMBER", "BD_NID", "EMAIL_ADDRESS", "IBAN_CODE", "CREDIT_CARD"],
            language="en",
        )
        anonymized: Any = anonymizer.anonymize(
            text=text,
            analyzer_results=results,  # type: ignore[arg-type]
        )
        return str(anonymized.text)
    except Exception:  # noqa: BLE001
        # Fallback to regex-only scrub if NLP engine encounters unexpected errors
        import re

        scrubbed = re.sub(BD_PHONE_REGEX, "<PHONE_NUMBER>", text)
        return re.sub(BD_NID_REGEX, "<BD_NID>", scrubbed)
