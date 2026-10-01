"""Every tracked Python source must parse under the supported interpreter."""

from __future__ import annotations

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def test_every_git_tracked_python_source_compiles() -> None:
    completed = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    tracked = completed.stdout.splitlines()
    assert tracked
    failures: list[str] = []
    for relative in tracked:
        source = (ROOT / relative).read_bytes()
        try:
            compile(source, relative, "exec")
        except SyntaxError as error:
            failures.append(f"{relative}:{error.lineno}: {error.msg}")
    assert failures == []
