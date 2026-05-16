from pathlib import Path
import io
import json
import tomllib

import pytest

import agent_delegate
from agent_delegate.backends import Backend, Message, get_backend
from agent_delegate.backends.base import BackendError, ChatResult
from agent_delegate.commands import ask, summarize, write
from agent_delegate.ledger import read_entries, summarize_entries
from agent_delegate.install import Action, inject_block, strip_block
from agent_delegate.profiles import Profile


class FakeBackend:
    name = "fake"

    def __init__(self, result: ChatResult | None = None, error: BackendError | None = None):
        self.result = result or ChatResult(
            content="fake content",
            model="fake-model",
            backend=self.name,
            prompt_tokens=3,
            completion_tokens=5,
            cached_tokens=1,
            reasoning_tokens=2,
            total_duration_ms=123,
        )
        self.error = error
        self.messages: list[Message] = []

    def chat(self, messages, model, *, temperature=0.2, max_tokens=None, timeout=120.0):
        self.messages = list(messages)
        if self.error:
            raise self.error
        return self.result


def fake_profile() -> Profile:
    return Profile(
        name="test-profile",
        backend="fake",
        base_url="http://example.test",
        default_model="fake-model",
    )


def test_package_imports():
    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        pyproject_data = tomllib.load(f)
    expected_version = pyproject_data["project"]["version"]
    assert agent_delegate.__version__ == expected_version


def test_backends_protocol():
    b = get_backend("openai-compat", base_url="http://x")
    assert isinstance(b, Backend)
    assert b.name == "openai-compat"

    a = get_backend("anthropic", api_key="k")
    assert isinstance(a, Backend)
    assert a.name == "anthropic"

    with pytest.raises(ValueError):
        get_backend("unknown")


def test_installer_idempotent(tmp_path: Path):
    path = tmp_path / "config.txt"
    user_content = "line1\nline2\n"
    path.write_text(user_content)

    rule_text = "<!-- agent-delegate:begin v0.1.0 -->\ntest body\n<!-- agent-delegate:end -->"

    res1 = inject_block(path, rule_text)
    assert res1.action == Action.APPENDED_BLOCK
    content1 = path.read_text()
    assert "line1" in content1
    assert "test body" in content1

    res2 = inject_block(path, rule_text)
    assert res2.action == Action.UNCHANGED

    res3 = strip_block(path)
    assert res3.action == Action.REMOVED_BLOCK
    content3 = path.read_text()
    assert "<!-- agent-delegate:begin" not in content3
    assert "<!-- agent-delegate:end" not in content3

    res4 = strip_block(path)
    assert res4.action == Action.REMOVED_NOTHING


def test_bundled_rules_use_current_marker():
    rules_dir = Path(__file__).parent.parent / "src" / "agent_delegate" / "rules"
    for rule in ("claude_code.md", "codex_cli.md", "claude_desktop.md", "codex_app.md"):
        content = (rules_dir / rule).read_text(encoding="utf-8")
        assert "<!-- agent-delegate:begin v0.2.0 -->" in content


def test_ask_json_success(capsys, tmp_path: Path):
    context = tmp_path / "context.txt"
    context.write_text("hello", encoding="utf-8")

    rc = ask.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        paths=[str(context)],
        question="What is this?",
        json_output=True,
    )

    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {
        "ok": True,
        "command": "ask",
        "profile": "test-profile",
        "model": "fake-model",
        "content": "fake content",
        "usage": {
            "prompt_tokens": 3,
            "completion_tokens": 5,
            "cached_tokens": 1,
            "reasoning_tokens": 2,
            "total_duration_ms": 123,
        },
    }


def test_write_json_target_exists(capsys, tmp_path: Path):
    context = tmp_path / "context.txt"
    context.write_text("hello", encoding="utf-8")
    target = tmp_path / "out.txt"
    target.write_text("existing", encoding="utf-8")

    rc = write.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        context=[str(context)],
        spec="write it",
        target=str(target),
        json_output=True,
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    out = json.loads(captured.out)
    assert out["ok"] is False
    assert out["command"] == "write"
    assert out["profile"] == "test-profile"
    assert out["model"] == "fake-model"
    assert out["target"] == str(target)
    assert out["error"]["type"] == "target_exists"
    assert "pass --force" in out["error"]["message"]


def test_write_strips_markdown_fences_by_default(tmp_path: Path):
    target = tmp_path / "draft.py"
    backend = FakeBackend(ChatResult(
        content="```python\nprint('hello')\n```\n",
        model="fake-model",
        backend="fake",
    ))

    rc = write.run(
        backend,
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target=str(target),
    )

    assert rc == 0
    assert target.read_text(encoding="utf-8") == "print('hello')\n"


def test_write_can_preserve_markdown_fences(tmp_path: Path):
    target = tmp_path / "draft.py"
    backend = FakeBackend(ChatResult(
        content="```python\nprint('hello')\n```\n",
        model="fake-model",
        backend="fake",
    ))

    rc = write.run(
        backend,
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target=str(target),
        strip_fences=False,
    )

    assert rc == 0
    assert target.read_text(encoding="utf-8") == "```python\nprint('hello')\n```\n"


def test_write_stdout_does_not_touch_target(tmp_path: Path, capsys):
    target = tmp_path / "draft.py"

    rc = write.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target=str(target),
        stdout=True,
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "fake content\n"
    assert not target.exists()


def test_write_stdout_ignores_target_root(tmp_path: Path, capsys):
    outside_root = tmp_path / "outside-root"
    outside_root.mkdir()

    rc = write.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target="-",
        stdout=True,
        target_root=str(outside_root),
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "fake content\n"
    assert captured.err == ""


def test_write_target_root_rejects_escape(tmp_path: Path, capsys):
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "outside.py"

    rc = write.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target=str(target),
        target_root=str(root),
    )

    captured = capsys.readouterr()
    assert rc == 2
    assert "target escapes --target-root" in captured.err
    assert not target.exists()


def test_write_diff_prints_unified_diff_and_writes(tmp_path: Path, capsys):
    target = tmp_path / "draft.py"
    target.write_text("old\n", encoding="utf-8")
    backend = FakeBackend(ChatResult(
        content="new",
        model="fake-model",
        backend="fake",
    ))

    rc = write.run(
        backend,
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target=str(target),
        force=True,
        diff=True,
    )

    captured = capsys.readouterr()
    assert rc == 0
    assert "---" in captured.out
    assert "-old\n" in captured.out
    assert "+new\n" in captured.out
    assert target.read_text(encoding="utf-8") == "new\n"


def test_summarize_json_backend_error(capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("summarize this"))
    backend = FakeBackend(error=BackendError("boom", backend="fake", status=503, body="nope"))

    rc = summarize.run(
        backend,
        fake_profile(),
        "fake-model",
        json_output=True,
    )

    assert rc == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    out = json.loads(captured.out)
    assert out["ok"] is False
    assert out["command"] == "summarize"
    assert out["error"] == {
        "type": "backend_error",
        "message": "boom",
        "backend": "fake",
        "status": 503,
        "body": "nope",
    }


def test_ask_text_output_is_default(capsys, tmp_path: Path):
    context = tmp_path / "context.txt"
    context.write_text("hello", encoding="utf-8")

    rc = ask.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        paths=[str(context)],
        question="What is this?",
    )

    assert rc == 0
    captured = capsys.readouterr()
    assert captured.out == "fake content\n"
    assert captured.err == ""


def test_ask_json_corpus_error(capsys, tmp_path: Path):
    missing = tmp_path / "missing.txt"

    rc = ask.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        paths=[str(missing)],
        question="What is this?",
        json_output=True,
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    out = json.loads(captured.out)
    assert out["ok"] is False
    assert out["command"] == "ask"
    assert out["error"]["type"] == "corpus_error"
    assert "missing file" in out["error"]["message"]


def test_write_json_corpus_error(capsys, tmp_path: Path):
    missing = tmp_path / "missing.txt"
    target = tmp_path / "out.py"

    rc = write.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        context=[str(missing)],
        spec="write it",
        target=str(target),
        json_output=True,
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    out = json.loads(captured.out)
    assert out["ok"] is False
    assert out["command"] == "write"
    assert out["target"] == str(target)
    assert out["error"]["type"] == "corpus_error"
    assert "missing file" in out["error"]["message"]


def test_usage_log_records_write_target(tmp_path: Path, monkeypatch):
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("AGENT_DELEGATE_LOG_DIR", str(log_dir))
    target = tmp_path / "draft.py"

    rc = write.run(
        FakeBackend(),
        fake_profile(),
        "fake-model",
        context=[],
        spec="write a file",
        target=str(target),
    )

    assert rc == 0
    entries = read_entries(log_dir / "agent-delegate.log")
    assert len(entries) == 1
    assert entries[0]["command"] == "write"
    assert entries[0]["profile"] == "test-profile"
    assert entries[0]["backend"] == "fake"
    assert entries[0]["model"] == "fake-model"
    assert entries[0]["target"] == str(target)


def test_ledger_summary_counts_models_and_commands():
    summary = summarize_entries([
        {
            "command": "ask",
            "profile": "ollama",
            "backend": "openai-compat",
            "model": "qwen3-coder:480b-cloud",
            "prompt_eval_count": 10,
            "eval_count": 3,
            "total_duration_ms": 100,
        },
        {
            "command": "write",
            "profile": "ollama",
            "backend": "openai-compat",
            "model": "qwen3-coder:480b-cloud",
            "prompt_eval_count": 20,
            "eval_count": 7,
            "total_duration_ms": 200,
        },
    ])

    assert summary["total_calls"] == 2
    assert summary["total_tokens"] == 40
    assert summary["total_duration_ms"] == 300
    assert summary["by_command"] == {"ask": 1, "write": 1}
    assert summary["by_profile"] == {"ollama": 2}
    assert summary["by_model"] == {"qwen3-coder:480b-cloud": 2}
