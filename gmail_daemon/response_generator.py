from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .actions import TaskCandidate
from .classifier import EmailClassification
from .gmail import EmailMessage


@dataclass(frozen=True)
class ResponseGenerator:
    enabled: bool
    model: str
    base_url: str

    def generate(
        self,
        message: EmailMessage,
        classification: EmailClassification,
        candidate: TaskCandidate,
    ) -> str:
        fallback = template_reply(candidate)
        if not self.enabled:
            return fallback

        prompt = _prompt(message, classification, candidate)
        for model in _model_names(self.model):
            generated = self._generate_with_model(model, prompt)
            if generated:
                return generated

        print("AI response generation failed for every configured model; using template reply.")
        return fallback

    def _generate_with_model(self, model: str, prompt: str) -> str | None:
        request = urllib.request.Request(
            f"{self.base_url.rstrip('/')}/api/generate",
            data=json.dumps(
                {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 180,
                    },
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"AI response generation failed for {model}; trying fallback: {exc}")
            return None

        if payload.get("error"):
            print(f"AI response generation failed for {model}; trying fallback: {payload['error']}")
            return None

        generated = _clean_response(payload.get("response", ""))
        if not generated:
            print(f"AI response generation returned no text for {model}; trying fallback.")
            return None

        return generated


def template_reply(candidate: TaskCandidate) -> str:
    if candidate.reason == "Reschedule required":
        return "Thanks for letting me know. Please send over a few times that work for you, and I will confirm one."

    if candidate.reason == "Meeting changed or cancelled":
        return "Thanks for the update. I saw the change and will adjust accordingly."

    if candidate.reason == "Payment or invoice follow-up":
        return "Thanks for sending this over. I will review the details and follow up if anything is missing."

    if candidate.reason == "Support issue needs review":
        return "Thanks for flagging this. I will take a look and get back to you."

    return "Thanks for reaching out. I will review this and follow up shortly."


def _prompt(
    message: EmailMessage,
    classification: EmailClassification,
    candidate: TaskCandidate,
) -> str:
    labels = ", ".join(classification.labels) if classification.labels else "none"
    original = (message.body.strip() or message.snippet.strip())[:4000]
    return f"""Write a concise email reply.

Rules:
- Reply as me.
- Be direct, natural, and professional.
- Do not invent times, dates, locations, calendar links, or commitments.
- If the sender asks to reschedule or asks for dates, ask them to send a few times that work.
- Return only the email body, no subject line, no markdown.

Context:
Reason: {candidate.reason}
Labels: {labels}
From: {message.sender}
Subject: {message.subject}

Email I received:
{original}
"""


def _model_names(model: str) -> list[str]:
    return [name.strip() for name in model.split(",") if name.strip()]


def _clean_response(response: str) -> str:
    response = response.strip()
    for prefix in ("Subject:", "Response:", "Reply:", "Email:"):
        if response.lower().startswith(prefix.lower()):
            response = response[len(prefix) :].strip()
    return response.strip("\"' \n")
