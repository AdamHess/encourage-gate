"""Chain-of-responsibility gate: each stage decides flag-or-defer; first flag wins."""

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, runtime_checkable

from better_profanity import profanity
from detoxify import Detoxify
from pydantic import BaseModel, ConfigDict
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

type GateReason = Literal["clean", "wordlist", "toxicity", "sentiment"]

DEFAULT_DETOXIFY_MODEL = "original"
DEFAULT_TOXICITY_THRESHOLDS: Mapping[str, float] = {
    "toxicity": 0.7,
    "insult": 0.7,
    "threat": 0.5,
    "identity_attack": 0.5,
}
DEFAULT_SENTIMENT_THRESHOLD = -0.3


class Classification(BaseModel):
    model_config = ConfigDict(frozen=True)

    flagged: bool
    reason: GateReason
    scores: dict[str, float]


@runtime_checkable
class GateStage(Protocol):
    reason: GateReason

    def check(self, text: str) -> Classification | None:
        """Return Classification to terminate the chain, or None to defer."""
        ...


class WordlistStage:
    reason: GateReason = "wordlist"

    def __init__(self):
        profanity.load_censor_words()

    def check(self, text: str) -> Classification | None:
        if not profanity.contains_profanity(text):
            return None
        return Classification(flagged=True, reason=self.reason, scores={})


class ToxicityStage:
    reason: GateReason = "toxicity"

    def __init__(
        self,
        *,
        thresholds: Mapping[str, float] = DEFAULT_TOXICITY_THRESHOLDS,
        classifier_model: str = DEFAULT_DETOXIFY_MODEL,
    ):
        self._thresholds = dict(thresholds)
        self._classifier = Detoxify(classifier_model)

    def check(self, text: str) -> Classification | None:
        scores = self._score(text)
        if self._exceeds_any_threshold(scores):
            return Classification(flagged=True, reason=self.reason, scores=scores)
        return None

    def _score(self, text: str) -> dict[str, float]:
        raw = self._classifier.predict(text)
        return {key: float(raw[key]) for key in self._thresholds if key in raw}

    def _exceeds_any_threshold(self, scores: Mapping[str, float]) -> bool:
        return any(scores[key] >= threshold for key, threshold in self._thresholds.items() if key in scores)


class SentimentStage:
    reason: GateReason = "sentiment"

    def __init__(self, *, negative_threshold: float = DEFAULT_SENTIMENT_THRESHOLD):
        self._negative_threshold = negative_threshold
        self._analyzer = SentimentIntensityAnalyzer()

    def check(self, text: str) -> Classification | None:
        scores = self._analyzer.polarity_scores(text)
        compound = float(scores["compound"])
        if compound > self._negative_threshold:
            return None
        return Classification(flagged=True, reason=self.reason, scores={"compound": compound})


class Gate:
    def __init__(self, stages: Sequence[GateStage]):
        if not stages:
            raise ValueError("Gate requires at least one stage")
        self._stages = tuple(stages)

    def classify(self, text: str) -> Classification:
        for stage in self._stages:
            verdict = stage.check(text)
            if verdict is not None:
                return verdict
        return Classification(flagged=False, reason="clean", scores={})


def default_gate() -> Gate:
    return Gate([WordlistStage(), SentimentStage(), ToxicityStage()])
