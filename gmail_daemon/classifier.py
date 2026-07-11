from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from .gmail import EmailMessage


DEFAULT_LABELS = {
    "urgent time-sensitive email": "urgent",
    "calendar scheduling or meeting request": "meeting",
    "invoice payment or billing email": "payment",
    "email that needs a reply": "needs reply",
    "newsletter or informational update": "newsletter",
    "sales pitch or prospecting email": "sales",
    "customer support issue": "support",
    "personal message": "personal",
    "spam or phishing email": "spam",
}


@dataclass(frozen=True)
class EmailClassification:
    labels: list[str]
    scores: dict[str, float]
    model_name: str


class EmailClassifier(Protocol):
    def classify(self, message: EmailMessage) -> EmailClassification:
        ...


class NullEmailClassifier:
    def classify(self, message: EmailMessage) -> EmailClassification:
        return EmailClassification(labels=[], scores={}, model_name="none")


class ZeroShotEmailClassifier:
    def __init__(
        self,
        model_path: str,
        threshold: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.model_path = model_path
        self.threshold = threshold
        self.labels = labels or DEFAULT_LABELS
        self._pipeline = None

    def classify(self, message: EmailMessage) -> EmailClassification:
        pipeline = self._load_pipeline()
        result = pipeline(
            _classification_text(message),
            candidate_labels=list(self.labels.keys()),
            multi_label=True,
        )

        scores = {
            self.labels[label]: float(score)
            for label, score in zip(result["labels"], result["scores"], strict=True)
        }
        selected = [label for label, score in scores.items() if score >= self.threshold]

        if not selected and result["labels"]:
            selected = [self.labels[result["labels"][0]]]

        return EmailClassification(
            labels=selected,
            scores=scores,
            model_name=self.model_path,
        )

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline

        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

        try:
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "Email classification requires transformers and torch. "
                "Install dependencies with: pip install -r requirements.txt"
            ) from exc

        self._pipeline = pipeline(
            "zero-shot-classification",
            model=self.model_path,
            tokenizer=self.model_path,
            local_files_only=True,
        )
        return self._pipeline


def build_classifier(enabled: bool, model_path: str, threshold: float) -> EmailClassifier:
    if not enabled:
        return NullEmailClassifier()
    return ZeroShotEmailClassifier(model_path=model_path, threshold=threshold)


def _classification_text(message: EmailMessage) -> str:
    text = "\n".join(
        part
        for part in (
            f"Subject: {message.subject}",
            f"From: {message.sender}",
            message.snippet,
            message.body,
        )
        if part
    )
    return text[:4000]
