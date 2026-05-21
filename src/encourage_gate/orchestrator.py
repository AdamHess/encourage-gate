"""Orchestrator: classify text via the gate, rewrite if flagged, package the response."""

import logging
from typing import Protocol

from encourage_gate.exceptions import RewriterError
from encourage_gate.gate import Classification
from encourage_gate.protocol import ResponseReason, RewriteResponse

log = logging.getLogger(__name__)


class GateClassifier(Protocol):
    def classify(self, text: str) -> Classification: ...


class TextRewriter(Protocol):
    def rewrite(self, text: str) -> str: ...


class RewriteOrchestrator:
    def __init__(self, gate: GateClassifier, rewriter: TextRewriter):
        self._gate = gate
        self._rewriter = rewriter

    def apply(self, text: str) -> RewriteResponse:
        classification = self._gate.classify(text)
        if not classification.flagged:
            return self._unchanged(text, classification)
        return self._rewrite_or_fallback(text, classification)

    def _rewrite_or_fallback(self, text: str, classification: Classification) -> RewriteResponse:
        try:
            rewritten = self._rewriter.rewrite(text)
        except RewriterError as err:
            log.warning("rewrite failed, passing through original: %s", err)
            return self._unchanged(text, classification, override_reason="rewrite_failed")
        return self._rewritten(rewritten, classification)

    @staticmethod
    def _rewritten(text: str, classification: Classification) -> RewriteResponse:
        return RewriteResponse(
            text=text,
            was_rewritten=True,
            reason=classification.reason,
            scores=classification.scores,
        )

    @staticmethod
    def _unchanged(
        text: str,
        classification: Classification,
        override_reason: ResponseReason | None = None,
    ) -> RewriteResponse:
        return RewriteResponse(
            text=text,
            was_rewritten=False,
            reason=override_reason or classification.reason,
            scores=classification.scores,
        )
