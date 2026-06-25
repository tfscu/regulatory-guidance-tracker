from pathlib import Path


SCRIPT = Path("scripts/update_guidance_database.ps1")


def test_update_script_is_portable_and_runs_core_steps():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "C:\\Users\\ET" not in text
    assert "$RepoRoot = Resolve-Path" in text
    assert "regulatory_guidance_${Timestamp}.db" in text
    assert '"crawl"' in text
    assert '"export-csv"' in text
    assert '"generate-report"' in text
    assert "Start-Transcript" in text
