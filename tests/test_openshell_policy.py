from pathlib import Path
import re


_CHROME = {
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome",
}


def test_openshell_policy_has_no_public_model_apis() -> None:
    raw = Path("openshell/policy.yaml").read_text(encoding="utf-8")
    blocked = (
        "api.anthropic.com",
        "api.openai.com",
        "api.x.ai",
        "chatgpt.com",
        "claude.ai",
        "platform.claude.com",
        "openrouter.ai",
        "run.app",
        "9876",
    )
    for host in blocked:
        assert host not in raw, host
    assert "127.0.0.1" in raw
    assert "8766" in raw
    assert "inference.local" in raw
    paths = re.findall(r"path:\s*([^}\s]+)", raw)
    assert paths
    assert set(paths) <= _CHROME
    assert "/opt/google/chrome/chrome" in paths
    joined = " ".join(paths)
    for banned in ("claude", "codex", "grok", "curl", "python", "node"):
        assert banned not in joined


def test_openshell_skill_is_browser_only() -> None:
    skill = Path("openshell/skills/rubiks-eval/SKILL.md").read_text(encoding="utf-8")
    assert "127.0.0.1:9876" not in skill
    assert "/api/task" in skill
    assert "Do not" in skill
    assert "/eval" in skill
    assert "inference.local" in skill
