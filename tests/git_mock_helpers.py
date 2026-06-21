from __future__ import annotations

from types import SimpleNamespace


def patch_git_clean(monkeypatch, subprocess_module) -> None:
    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "diff", "HEAD"]:
            return SimpleNamespace(stdout="", returncode=0)
        if args[:2] == ["git", "status"]:
            return SimpleNamespace(stdout="", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(subprocess_module, "run", _fake_run)


def patch_git_with_changed_file(monkeypatch, subprocess_module, filename: str = "app/real.py") -> None:
    def _fake_run(args, **kwargs):
        if args[:3] == ["git", "diff", "HEAD"]:
            return SimpleNamespace(stdout="", returncode=0)
        if args[:2] == ["git", "status"]:
            return SimpleNamespace(stdout="", returncode=0)
        if args[:4] == ["git", "diff-tree", "--no-commit-id", "--name-only"]:
            return SimpleNamespace(stdout=f"{filename}\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)

    monkeypatch.setattr(subprocess_module, "run", _fake_run)
