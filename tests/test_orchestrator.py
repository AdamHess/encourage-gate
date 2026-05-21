"""Orchestrator tests using fakes for Gate and Rewriter."""

from encourage_gate.exceptions import RewriterError
from encourage_gate.gate import Classification
from encourage_gate.orchestrator import RewriteOrchestrator


class _StubGate:
    def __init__(self, verdict: Classification):
        self._verdict = verdict

    def classify(self, text: str) -> Classification:
        return self._verdict


class _StubRewriter:
    def __init__(self, *, output: str | None = None, error: Exception | None = None):
        self._output = output
        self._error = error
        self.calls: list[str] = []

    def rewrite(self, text: str) -> str:
        self.calls.append(text)
        if self._error is not None:
            raise self._error
        assert self._output is not None
        return self._output


def test_apply_when_classification_is_clean_should_skip_rewriter_and_return_original() -> None:
    rewriter = _StubRewriter(output="should not run")
    orch = RewriteOrchestrator(_StubGate(Classification(flagged=False, reason="clean", scores={})), rewriter)

    response = orch.apply("hello world")

    assert response.was_rewritten is False
    assert response.reason == "clean"
    assert response.text == "hello world"
    assert rewriter.calls == []


def test_apply_when_classification_is_flagged_should_rewrite_and_report_gate_reason() -> None:
    rewriter = _StubRewriter(output="kindly fix the build")
    orch = RewriteOrchestrator(
        _StubGate(Classification(flagged=True, reason="wordlist", scores={})),
        rewriter,
    )

    response = orch.apply("fix the damn build")

    assert response.was_rewritten is True
    assert response.reason == "wordlist"
    assert response.text == "kindly fix the build"
    assert rewriter.calls == ["fix the damn build"]


def test_apply_when_rewriter_raises_should_fall_back_to_original_with_failure_reason() -> None:
    rewriter = _StubRewriter(error=RewriterError("upstream timeout"))
    orch = RewriteOrchestrator(
        _StubGate(Classification(flagged=True, reason="toxicity", scores={"insult": 0.91})),
        rewriter,
    )

    response = orch.apply("you absolute fool")

    assert response.was_rewritten is False
    assert response.reason == "rewrite_failed"
    assert response.text == "you absolute fool"
    assert response.scores == {"insult": 0.91}
