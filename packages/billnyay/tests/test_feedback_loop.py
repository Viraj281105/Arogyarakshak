from billnyay.agents.feedback_loop import draft_with_self_correction
from billnyay.agents.judge import Issue, JudgeScorecard, SubScores


class SequenceClient:
    """Returns each of `letters` in order (repeating the last one), regardless of
    prompt content — the loop mechanics being tested don't depend on prompt text."""

    def __init__(self, letters):
        self.letters = list(letters)
        self.calls = 0

    def generate(self, *args, **kwargs) -> str:
        letter = self.letters[min(self.calls, len(self.letters) - 1)]
        self.calls += 1
        return letter


def _scorecard(status: str, overall_score: int, issues=None) -> JudgeScorecard:
    subs = SubScores(
        factual_accuracy=70, citation_consistency=70, logical_adequacy=70,
        tone_professionalism=70, hallucination_risk=10,
    )
    # Passing overall_score explicitly short-circuits JudgeScorecard's validator, so
    # this constructs an exact scorecard rather than one derived from sub_scores.
    return JudgeScorecard(
        overall_score=overall_score, status=status, sub_scores=subs, issues=issues or [], confidence_estimate=0.5
    )


def test_language_reaches_the_barrister_on_every_call_including_revisions(monkeypatch):
    """#39: a language selected once at the endpoint must survive every re-draft in
    the self-correction loop, not just the first attempt."""
    monkeypatch.setattr(
        "billnyay.agents.feedback_loop.run_judge_agent",
        lambda *a, **kw: _scorecard("needs_revision", 40, issues=[]),
    )
    captured_languages = []

    class CapturingClient:
        def generate(self, *args, **kwargs):
            captured_languages.append(kwargs.get("language"))
            return "L" * 400

    draft_with_self_correction(CapturingClient(), max_attempts=1, language="mr")

    assert captured_languages == ["mr", "mr"]  # initial draft + 1 revision


def test_language_defaults_to_english(monkeypatch):
    monkeypatch.setattr(
        "billnyay.agents.feedback_loop.run_judge_agent",
        lambda *a, **kw: _scorecard("approve", 85),
    )
    captured_languages = []

    class CapturingClient:
        def generate(self, *args, **kwargs):
            captured_languages.append(kwargs.get("language"))
            return "M" * 400

    draft_with_self_correction(CapturingClient())
    assert captured_languages == ["en"]


def test_no_revision_needed_when_judge_approves_first_draft(monkeypatch):
    monkeypatch.setattr(
        "billnyay.agents.feedback_loop.run_judge_agent",
        lambda *a, **kw: _scorecard("approve", 85),
    )
    client = SequenceClient(["A" * 400])
    result = draft_with_self_correction(client)

    assert result is not None
    assert result.revision_count == 0
    assert result.revision_history == []
    assert result.appeal_letter == "A" * 400


def test_revises_once_then_stops_on_approval(monkeypatch):
    sequence = [
        _scorecard(
            "needs_revision", 60,
            issues=[Issue(id="I1", severity="high", description="Missing citation", suggested_fix="Add IRDAI circular reference")],
        ),
        _scorecard("approve", 85),
    ]
    calls = {"n": 0}

    def fake_judge(*args, **kwargs):
        result = sequence[min(calls["n"], len(sequence) - 1)]
        calls["n"] += 1
        return result

    monkeypatch.setattr("billnyay.agents.feedback_loop.run_judge_agent", fake_judge)

    client = SequenceClient(["A" * 400, "B" * 400])
    result = draft_with_self_correction(client)

    assert result.revision_count == 1
    assert result.scorecard.status == "approve"
    assert result.appeal_letter == "B" * 400
    assert len(result.revision_history) == 1
    assert result.revision_history[0].prior_score == 60
    assert "Missing citation" in result.revision_history[0].critique


def test_stops_at_max_attempts_when_never_approved(monkeypatch):
    monkeypatch.setattr(
        "billnyay.agents.feedback_loop.run_judge_agent",
        lambda *a, **kw: _scorecard("needs_revision", 40),
    )
    client = SequenceClient(["A" * 400])
    result = draft_with_self_correction(client, max_attempts=2)

    assert result.revision_count == 2
    assert len(result.revision_history) == 2
    assert result.scorecard.status == "needs_revision"


def test_returns_none_when_no_initial_draft():
    client = SequenceClient(["too short"])
    result = draft_with_self_correction(client)
    assert result is None


def test_keeps_prior_draft_when_a_revision_attempt_fails(monkeypatch):
    monkeypatch.setattr(
        "billnyay.agents.feedback_loop.run_judge_agent",
        lambda *a, **kw: _scorecard("needs_revision", 40, issues=[Issue(id="I1", severity="high", description="Too short")]),
    )

    class FirstGoodThenFailsClient:
        def __init__(self):
            self.calls = 0

        def generate(self, *args, **kwargs):
            self.calls += 1
            return ("A" * 400) if self.calls == 1 else "short"

    result = draft_with_self_correction(FirstGoodThenFailsClient())
    assert result is not None
    assert result.appeal_letter == "A" * 400
    assert result.revision_count == 1
