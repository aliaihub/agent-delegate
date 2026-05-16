from pathlib import Path

import pytest

from agent_delegate.commands import _corpus


def test_corpus_expands_directories_with_default_excludes(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "b.py").write_text("b", encoding="utf-8")
    (tmp_path / "src" / "a.py").write_text("a", encoding="utf-8")
    (tmp_path / "src" / "build").write_text("file named build", encoding="utf-8")
    (tmp_path / "src" / "node_modules").mkdir()
    (tmp_path / "src" / "node_modules" / "dep.py").write_text("dep", encoding="utf-8")
    (tmp_path / "src" / ".git").mkdir()
    (tmp_path / "src" / ".git" / "config").write_text("git", encoding="utf-8")

    rendered = _corpus.corpus(["src"])

    assert '<file path="src/a.py">' in rendered
    assert '<file path="src/b.py">' in rendered
    assert '<file path="src/build">' in rendered
    assert "node_modules" not in rendered
    assert ".git" not in rendered
    assert rendered.index("src/a.py") < rendered.index("src/b.py")


def test_corpus_expands_globs_dedupes_and_sorts(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "z.txt").write_text("z", encoding="utf-8")
    (tmp_path / "pkg" / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "pkg" / "dist").mkdir()
    (tmp_path / "pkg" / "dist" / "generated.txt").write_text("generated", encoding="utf-8")

    rendered = _corpus.corpus(["pkg/**/*.txt", "pkg/a.txt"])

    assert rendered.count("<file path=") == 2
    assert '<file path="pkg/a.txt">' in rendered
    assert '<file path="pkg/z.txt">' in rendered
    assert "generated" not in rendered
    assert rendered.index("pkg/a.txt") < rendered.index("pkg/z.txt")


def test_corpus_enforces_max_total_bytes(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("abcd", encoding="utf-8")
    (tmp_path / "b.txt").write_text("efgh", encoding="utf-8")
    monkeypatch.setattr(_corpus, "MAX_CORPUS_BYTES", 7)

    with pytest.raises(SystemExit, match="corpus too large"):
        _corpus.corpus(["*.txt"])
