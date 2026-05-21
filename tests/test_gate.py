"""Gate tests. Unit tests cover chain ordering with fakes; integration tests load Detoxify."""

from collections.abc import Sequence

import pytest

from encourage_gate.gate import (
    Classification,
    Gate,
    GateReason,
    GateStage,
    WordlistStage,
    default_gate,
)


class _FakeStage:
    def __init__(self, reason: GateReason, verdict: Classification | None):
        self.reason: GateReason = reason
        self._verdict = verdict
        self.calls = 0

    def check(self, text: str) -> Classification | None:
        self.calls += 1
        return self._verdict


def _gate_with(stages: Sequence[GateStage]) -> Gate:
    return Gate(list(stages))


def test_classify_when_first_stage_flags_should_short_circuit_and_skip_later_stages() -> None:
    flagger = _FakeStage("wordlist", Classification(flagged=True, reason="wordlist", scores={}))
    later = _FakeStage(
        "toxicity",
        Classification(flagged=True, reason="toxicity", scores={"toxicity": 0.99}),
    )

    result = _gate_with([flagger, later]).classify("anything")

    assert result.flagged is True
    assert result.reason == "wordlist"
    assert flagger.calls == 1
    assert later.calls == 0


def test_classify_when_earlier_stage_defers_should_fall_through_to_next_stage():
    deferring = _FakeStage("wordlist", None)
    flagger = _FakeStage(
        "toxicity",
        Classification(flagged=True, reason="toxicity", scores={"insult": 0.9}),
    )

    result = _gate_with([deferring, flagger]).classify("anything")

    assert result.flagged is True
    assert result.reason == "toxicity"
    assert deferring.calls == 1
    assert flagger.calls == 1


def test_classify_when_chain_has_many_stages_should_traverse_until_one_flags():
    a = _FakeStage("wordlist", None)
    b = _FakeStage("wordlist", None)
    c = _FakeStage(
        "toxicity",
        Classification(flagged=True, reason="toxicity", scores={"toxicity": 0.95}),
    )
    d = _FakeStage("toxicity", None)

    result = _gate_with([a, b, c, d]).classify("anything")

    assert result.flagged is True
    assert result.reason == "toxicity"
    assert a.calls == 1
    assert b.calls == 1
    assert c.calls == 1
    assert d.calls == 0


def test_classify_when_all_stages_defer_should_return_clean_with_no_scores():
    a = _FakeStage("wordlist", None)
    b = _FakeStage("toxicity", None)

    result = _gate_with([a, b]).classify("polite text")

    assert result.flagged is False
    assert result.reason == "clean"
    assert result.scores == {}


def test_init_when_stage_list_is_empty_should_raise_value_error():
    with pytest.raises(ValueError):
        Gate([])


def test_check_when_text_contains_profanity_should_return_flagged_classification() -> None:
    result = WordlistStage().check("this fucking thing")
    assert result is not None and result.flagged is True


def test_check_when_text_is_clean_should_return_none():
    assert WordlistStage().check("please help me") is None


@pytest.mark.integration
def test_classify_when_text_is_overt_insult_should_flag_via_toxicity_stage():
    result = default_gate().classify("you are a worthless idiot and your code is garbage")
    assert result.flagged is True
    assert result.reason == "toxicity"


@pytest.mark.integration
def test_classify_when_prompt_is_polite_should_return_clean():
    result = default_gate().classify("Please help me refactor this function.")
    assert result.flagged is False
    assert result.reason == "clean"
