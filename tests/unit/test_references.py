from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT / "tools"))

from check_references import check_references, parse_bibliography


VALID_BIBLIOGRAPHY = r"""
@article{example2025,
  author = {Ada Lovelace and Grace Hopper},
  title = {A {Graph} Reference},
  year = {2025},
  doi = {10.0000/example},
  url = {https://doi.org/10.0000/example}
}
"""


def _write_inputs(tmp_path: Path, bibliography: str, related_work: str) -> tuple[Path, Path]:
    bibliography_path = tmp_path / "references.bib"
    related_work_path = tmp_path / "related_work.md"
    bibliography_path.write_text(bibliography, encoding="utf-8")
    related_work_path.write_text(related_work, encoding="utf-8")
    return bibliography_path, related_work_path


def test_parse_bibliography_handles_nested_braces() -> None:
    entries = parse_bibliography(VALID_BIBLIOGRAPHY)

    assert list(entries) == ["example2025"]
    assert entries["example2025"]["title"] == "A {Graph} Reference"


def test_check_references_accepts_valid_cited_entry(tmp_path: Path) -> None:
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        VALID_BIBLIOGRAPHY,
        "Supported claim [@example2025].\n",
    )

    assert check_references(bibliography_path, related_work_path) == []


def test_check_references_rejects_duplicate_keys(tmp_path: Path) -> None:
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        VALID_BIBLIOGRAPHY + VALID_BIBLIOGRAPHY,
        "Supported claim [@example2025].\n",
    )

    errors = check_references(bibliography_path, related_work_path)

    assert any("duplicate bibliography key 'example2025'" in error for error in errors)


def test_check_references_rejects_unterminated_bibliography(tmp_path: Path) -> None:
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        VALID_BIBLIOGRAPHY.rstrip()[:-1],
        "Supported claim [@example2025].\n",
    )

    errors = check_references(bibliography_path, related_work_path)

    assert any("bibliography parse error" in error for error in errors)


@pytest.mark.parametrize("missing_field", ["author", "title", "year"])
def test_check_references_rejects_missing_required_fields(
    tmp_path: Path, missing_field: str
) -> None:
    bibliography = "\n".join(
        line
        for line in VALID_BIBLIOGRAPHY.splitlines()
        if not line.strip().startswith(f"{missing_field} =")
    )
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        bibliography,
        "Supported claim [@example2025].\n",
    )

    errors = check_references(bibliography_path, related_work_path)

    assert any(f"missing required field '{missing_field}'" in error for error in errors)


def test_check_references_requires_doi_or_url(tmp_path: Path) -> None:
    bibliography = "\n".join(
        line
        for line in VALID_BIBLIOGRAPHY.splitlines()
        if not line.strip().startswith(("doi =", "url ="))
    )
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        bibliography,
        "Supported claim [@example2025].\n",
    )

    errors = check_references(bibliography_path, related_work_path)

    assert any("requires at least one of 'doi' or 'url'" in error for error in errors)


def test_check_references_rejects_unknown_citation_key(tmp_path: Path) -> None:
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        VALID_BIBLIOGRAPHY,
        "Unsupported claim [@missing2025].\n",
    )

    errors = check_references(bibliography_path, related_work_path)

    assert any("citation key 'missing2025' is not in the bibliography" in error for error in errors)


def test_check_references_rejects_uncited_bibliography_entry(tmp_path: Path) -> None:
    bibliography_path, related_work_path = _write_inputs(
        tmp_path,
        VALID_BIBLIOGRAPHY,
        "A claim with no citation.\n",
    )

    errors = check_references(bibliography_path, related_work_path)

    assert any("bibliography key 'example2025' is not cited" in error for error in errors)


def test_cli_reports_repository_documents_as_valid() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPOSITORY_ROOT / "tools" / "check_references.py"),
            "--bibliography",
            str(REPOSITORY_ROOT / "paper" / "references.bib"),
            "--related-work",
            str(REPOSITORY_ROOT / "docs" / "related_work.md"),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Reference check passed" in result.stdout
