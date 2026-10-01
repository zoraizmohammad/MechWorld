#!/usr/bin/env python3
"""Dependency-free checks for the related-work bibliography and citations."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


class BibliographyParseError(ValueError):
    """Raised when a BibTeX file is structurally invalid."""


_FIELD_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_ENTRY_TYPE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_CITATION = re.compile(r"(?<![A-Za-z0-9_.])@([A-Za-z0-9][A-Za-z0-9_:./+-]*)")
_CITATION_GROUP = re.compile(r"\[([^\]]*@[^\]]*)\]")


def _skip_space_and_comments(text: str, position: int) -> int:
    while position < len(text):
        if text[position].isspace():
            position += 1
        elif text[position] == "%":
            newline = text.find("\n", position)
            position = len(text) if newline == -1 else newline + 1
        else:
            break
    return position


def _read_braced(text: str, position: int) -> tuple[str, int]:
    start = position
    depth = 0
    while position < len(text):
        character = text[position]
        if character == "\\":
            position += 2
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : position], position + 1
        position += 1
    raise BibliographyParseError("unterminated braced value")


def _read_quoted(text: str, position: int) -> tuple[str, int]:
    start = position + 1
    position += 1
    while position < len(text):
        if text[position] == "\\":
            position += 2
            continue
        if text[position] == '"':
            return text[start:position], position + 1
        position += 1
    raise BibliographyParseError("unterminated quoted value")


def _parse_fields(body: str, key: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    position = 0
    while True:
        position = _skip_space_and_comments(body, position)
        while position < len(body) and body[position] == ",":
            position = _skip_space_and_comments(body, position + 1)
        if position >= len(body):
            break

        match = _FIELD_NAME.match(body, position)
        if not match:
            raise BibliographyParseError(
                f"entry '{key}' has invalid field syntax near {body[position:position + 24]!r}"
            )
        field = match.group(0).lower()
        position = _skip_space_and_comments(body, match.end())
        if position >= len(body) or body[position] != "=":
            raise BibliographyParseError(f"entry '{key}' field '{field}' is missing '='")
        position = _skip_space_and_comments(body, position + 1)
        if position >= len(body):
            raise BibliographyParseError(f"entry '{key}' field '{field}' has no value")

        if body[position] == "{":
            value, position = _read_braced(body, position)
        elif body[position] == '"':
            value, position = _read_quoted(body, position)
        else:
            value_start = position
            while position < len(body) and body[position] != ",":
                position += 1
            value = body[value_start:position].strip()
        if not value.strip():
            raise BibliographyParseError(f"entry '{key}' field '{field}' is empty")
        if field in fields:
            raise BibliographyParseError(f"entry '{key}' repeats field '{field}'")
        fields[field] = value.strip()

        position = _skip_space_and_comments(body, position)
        if position < len(body) and body[position] != ",":
            raise BibliographyParseError(
                f"entry '{key}' field '{field}' is not followed by a comma"
            )

    return fields


def parse_bibliography(text: str) -> dict[str, dict[str, str]]:
    """Parse the BibTeX subset used by this repository and reject duplicate keys."""

    entries: dict[str, dict[str, str]] = {}
    position = 0
    while True:
        position = _skip_space_and_comments(text, position)
        if position >= len(text):
            break
        if text[position] != "@":
            raise BibliographyParseError(f"expected '@' at byte {position}")
        type_match = _ENTRY_TYPE.match(text, position + 1)
        if not type_match:
            raise BibliographyParseError(f"invalid entry type at byte {position}")
        entry_type = type_match.group(0).lower()
        position = _skip_space_and_comments(text, type_match.end())
        if position >= len(text) or text[position] not in "{(":
            raise BibliographyParseError(
                f"entry type '{entry_type}' is not followed by '{{' or '('")
        opening = text[position]
        closing = "}" if opening == "{" else ")"
        position += 1

        key_start = position
        while position < len(text) and text[position] not in "," + closing:
            position += 1
        if position >= len(text) or text[position] != ",":
            raise BibliographyParseError(f"entry '{entry_type}' has no citation key/body separator")
        key = text[key_start:position].strip()
        if not key:
            raise BibliographyParseError(f"entry '{entry_type}' has an empty citation key")
        if key in entries:
            raise BibliographyParseError(f"duplicate bibliography key '{key}'")
        position += 1

        body_start = position
        depth = 1
        in_quote = False
        while position < len(text):
            character = text[position]
            if character == "\\":
                position += 2
                continue
            if character == '"':
                in_quote = not in_quote
            elif not in_quote:
                if character == opening:
                    depth += 1
                elif character == closing:
                    depth -= 1
                    if depth == 0:
                        break
            position += 1
        if position >= len(text):
            raise BibliographyParseError(f"entry '{key}' is unterminated")

        fields = _parse_fields(text[body_start:position], key)
        fields["entrytype"] = entry_type
        entries[key] = fields
        position += 1

    return entries


def citation_keys(markdown: str) -> set[str]:
    """Return Pandoc-style citation keys from bracketed citation groups."""

    keys: set[str] = set()
    for group in _CITATION_GROUP.finditer(markdown):
        keys.update(_CITATION.findall(group.group(1)))
    return keys


def check_references(bibliography_path: Path, related_work_path: Path) -> list[str]:
    """Return all structural and cross-reference errors for the two documents."""

    errors: list[str] = []
    for path, label in (
        (bibliography_path, "bibliography"),
        (related_work_path, "related-work document"),
    ):
        if not path.is_file():
            errors.append(f"{label} does not exist: {path}")
    if errors:
        return errors

    try:
        entries = parse_bibliography(bibliography_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, BibliographyParseError) as error:
        return [f"bibliography parse error: {error}"]

    for key, fields in entries.items():
        for required in ("author", "title", "year"):
            if required not in fields:
                errors.append(f"entry '{key}' is missing required field '{required}'")
        year = fields.get("year")
        if year is not None and not re.fullmatch(r"\d{4}", year):
            errors.append(f"entry '{key}' has invalid four-digit year {year!r}")
        if "doi" not in fields and "url" not in fields:
            errors.append(f"entry '{key}' requires at least one of 'doi' or 'url'")
        doi = fields.get("doi")
        if doi is not None and not doi.lower().startswith("10."):
            errors.append(f"entry '{key}' has invalid DOI {doi!r}")
        url = fields.get("url")
        if url is not None and not re.match(r"https?://", url, re.IGNORECASE):
            errors.append(f"entry '{key}' has invalid URL {url!r}")

    try:
        markdown = related_work_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        return errors + [f"related-work read error: {error}"]
    citations = citation_keys(markdown)
    for key in sorted(citations - entries.keys()):
        errors.append(f"citation key '{key}' is not in the bibliography")
    for key in sorted(entries.keys() - citations):
        errors.append(f"bibliography key '{key}' is not cited in the related-work document")

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bibliography", required=True, type=Path)
    parser.add_argument("--related-work", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    errors = check_references(arguments.bibliography, arguments.related_work)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    entries = parse_bibliography(arguments.bibliography.read_text(encoding="utf-8"))
    citations = citation_keys(arguments.related_work.read_text(encoding="utf-8"))
    print(f"Reference check passed: {len(entries)} entries, {len(citations)} cited keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
