from pathlib import Path


def test_openshell_policy_has_no_public_model_apis() -> None:
    raw = Path("openshell/policy.yaml").read_text(encoding="utf-8")
    blocked = (
        "api.anthropic.com",
        "api.openai.com",
        "api.x.ai",
        "chatgpt.com",
        "openrouter.ai",
        "run.app",
        "9876",
    )
    for host in blocked:
        assert host not in raw, host
    assert "127.0.0.1" in raw
    assert "8766" in raw
    assert "/usr/bin/chromium" in raw
    # Agent CLIs must not be listed as allowed binaries for the eval port.
    binaries = [
        line.strip()
        for line in raw.splitlines()
        if "path:" in line and "/usr" in line
    ]
    joined = " ".join(binaries)
    assert "claude" not in joined
    assert "codex" not in joined
    assert "grok" not in joined
    assert "curl" not in joined
    assert "python" not in joined


def test_openshell_skill_is_browser_only() -> None:
    skill = Path("openshell/skills/rubiks-eval/SKILL.md").read_text(encoding="utf-8")
    assert "127.0.0.1:9876" not in skill
    assert "/api/task" in skill
    assert "must not" in skill.lower() or "Do not" in skill
    assert "/eval" in skill
    assert "inference.local" in skill
