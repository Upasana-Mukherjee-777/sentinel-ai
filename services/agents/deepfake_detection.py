"""
services/agents/deepfake_detection.py

Deepfake Detection Agent (Blueprint Section 7.1, Agent #6) -- INTERFACE
STUB, not a functional detector.

WHY THIS IS A STUB: the blueprint specifies MTCNN face detection feeding
an EfficientNet-B4 classifier with a DCT frequency-domain branch, plus a
SpeechBrain voice-clone detector for audio and a temporal lip-sync
consistency check for video (Section 11). All of that requires trained
model weights on labeled real/fake face and voice datasets (FaceForensics++,
Celeb-DF, DFDC, ASVspoof), GPU inference, and — for the frequency-domain
branch specifically — architecture that is easy to specify and genuinely
hard to fake a working version of in a scaffold with no training data or
GPU budget. Shipping a heuristic here (the way the Counterfeit Currency
Agent does) would be actively misleading for deepfake detection
specifically, since a wrong "not manipulated" verdict on a deepfake
extortion video has real, serious harm potential. Better to be honest
that this needs the real pipeline before it's trustworthy.

WHAT TO DO TO MAKE THIS REAL: implement `analyze()` following the
pattern of every other agent in this folder (return an AgentResponse via
`self._response(...)`), with the actual inference call being:
  1. MTCNN face crop from each sampled frame
  2. EfficientNet-B4 + DCT branch forward pass -> per-frame manipulation
     probability
  3. Aggregate across frames + check audio/video lip-sync consistency
  4. For audio-only input, run the SpeechBrain anti-spoofing model
     (already wired for the Call Intelligence Agent's future audio
     upgrade -- reuse that model loader)
The AgentResponse contract (confidence, evidence, reasoning,
visual_highlight with per-frame bounding boxes) is unchanged from every
other agent, so the orchestrator and frontend do not need to change when
this is implemented for real.
"""

from __future__ import annotations

from typing import Any

from .base import AgentResponse, BaseAgent, Verdict


class DeepfakeDetectionAgent(BaseAgent):
    name = "deepfake_detection_agent"

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        return self._response(
            Verdict.UNKNOWN,
            0.0,
            evidence=[
                "Deepfake Detection Agent is not implemented in this scaffold — it requires trained "
                "model weights (EfficientNet-B4 + DCT branch, SpeechBrain voice-clone detector) that "
                "are not included here. See this module's docstring for the exact pipeline to implement."
            ],
            reasoning=(
                "This agent intentionally returns UNKNOWN rather than a fabricated verdict. "
                "Do not treat the absence of a flag from this agent as evidence that media is genuine."
            ),
        )
