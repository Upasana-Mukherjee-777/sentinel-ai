"""
services/agents/counterfeit_currency.py

Counterfeit Currency Intelligence Agent (Blueprint Section 7.1, Agent #3).

IMPORTANT SCOPE NOTE: The blueprint (Section 11) specifies a
YOLOv8-region-detection + per-feature CNN pipeline trained on labeled
genuine/counterfeit currency image datasets, checking watermark,
security thread, micro-print, and color consistency independently. That
requires trained model weights and labeled image data this scaffold
does not ship with.

What this module DOES do, honestly: a functional, real OpenCV-based
image-quality heuristic that checks signals a genuine, well-handled
banknote photo tends to have (sufficient sharpness/focus, a plausible
aspect ratio, sufficient color variance across the note) and flags
images that fail these basic checks for manual review. This is
deliberately framed as a triage/pre-filter, NOT a genuineness
determination -- the verdict is capped at CAUTION, never SAFE or
DANGEROUS, because this heuristic has no ground-truth security-feature
model behind it. Swapping in the real trained pipeline from Section 11
only requires replacing `_extract_signals()` and the verdict thresholds
below; the AgentResponse contract stays identical.
"""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from .base import AgentResponse, BaseAgent, Verdict

EXPECTED_AR_RANGE = (2.0, 2.5)  # Indian banknotes are roughly this width:height ratio


class CounterfeitCurrencyAgent(BaseAgent):
    name = "counterfeit_currency_agent"

    def _extract_signals(self, image_path: str) -> dict[str, float]:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image at {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]

        # Sharpness proxy: variance of the Laplacian. Blurry/low-effort
        # forgery photos (or bad scans) tend to score low here.
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        aspect_ratio = w / h if h else 0.0

        # Color variance proxy: genuine notes have deliberate, varied
        # security-ink coloration; a flat photocopy tends to have lower
        # channel variance.
        color_variance = float(np.mean([image[:, :, c].std() for c in range(3)]))

        return {"sharpness": sharpness, "aspect_ratio": aspect_ratio, "color_variance": color_variance}

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        image_path = payload.get("image_path", "")
        if not image_path:
            return self._response(Verdict.UNKNOWN, 0.0, [], "No image path provided.")

        try:
            signals = self._extract_signals(image_path)
        except Exception as exc:  # noqa: BLE001
            return self._response(Verdict.UNKNOWN, 0.0, [str(exc)], "Could not process the provided image.")

        evidence = []
        concerns = 0

        if signals["sharpness"] < 40:
            concerns += 1
            evidence.append(f"Image sharpness is low ({signals['sharpness']:.1f}) -- too blurry to assess security features reliably")

        ar = signals["aspect_ratio"]
        if not (EXPECTED_AR_RANGE[0] <= ar <= EXPECTED_AR_RANGE[1]):
            concerns += 1
            evidence.append(f"Aspect ratio ({ar:.2f}) falls outside the expected range for Indian currency notes -- check framing/cropping")

        if signals["color_variance"] < 15:
            concerns += 1
            evidence.append(f"Low color variance ({signals['color_variance']:.1f}) -- may indicate a flat photocopy/scan rather than a genuine printed note")

        if not evidence:
            evidence.append("Image passes basic quality triage checks (sharpness, framing, color variance)")

        # Deliberately capped: this heuristic can flag a bad PHOTO, it
        # cannot confirm a note is GENUINE. Real genuineness determination
        # needs the trained security-feature CNN pipeline from Section 11.
        verdict = Verdict.CAUTION if concerns > 0 else Verdict.UNKNOWN
        confidence = min(0.3 + 0.15 * concerns, 0.75)
        reasoning = (
            f"{concerns} image-quality concern(s) detected. This is an image-quality triage check only -- "
            "it is NOT a security-feature genuineness verification. Route to the full CV pipeline "
            "(Blueprint Section 11) or manual inspection for an actual genuine/counterfeit determination."
            if concerns > 0 else
            "Image passed basic quality triage. This scaffold does not include a trained security-feature "
            "classifier, so no genuineness verdict is given -- route to the full CV pipeline (Blueprint Section 11) "
            "or manual inspection for an actual determination."
        )

        return self._response(
            verdict, confidence, evidence, reasoning,
            visual_highlight={"signals": signals, "note": "quality triage only, not a genuineness determination"},
        )
