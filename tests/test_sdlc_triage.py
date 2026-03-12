from scripts.sdlc_triage import run_triage, TriageResult


class TestTriageDryRun:
    def test_dry_run_output(self):
        result = run_triage(1, dry_run=True)
        assert isinstance(result, TriageResult)
        assert result.complexity in ("S", "M", "L")

    def test_dry_run_type(self):
        result = run_triage(1, dry_run=True)
        assert result.type in ("spec-update", "new-axiom", "implication-change", "documentation")

    def test_dry_run_no_rejection(self):
        result = run_triage(1, dry_run=True)
        assert result.reject_reason is None
