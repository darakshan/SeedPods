"""
Shared error and warning reporting for build and check.
Messages are collected and printed at the end. Use nugget number + shortname
when available; otherwise path relative to content/ (e.g. about/goals.md).
Warnings do not fail the build; errors do.
"""

import sys
from pathlib import Path

from nugget_parser import CONTENT_DIR

_errors = []
_warnings = []


def _location(path=None, nugget_num=None, shortname=None):
    if nugget_num is not None and shortname:
        return f"{nugget_num}-{shortname}"
    if path is not None:
        path = Path(path).resolve()
        try:
            rel = path.relative_to(Path(CONTENT_DIR).resolve())
        except ValueError:
            return str(path)
        parts = rel.parts
        if len(parts) == 2 and parts[0] == "nuggets" and rel.suffix == ".txt" and "-" in rel.stem:
            return rel.stem
        return str(rel).replace("\\", "/")
    return None


def _format(loc, msg):
    if loc:
        return f"{loc}: {msg}"
    return msg


def reset():
    global _errors, _warnings
    _errors = []
    _warnings = []


def error(msg, path=None, nugget_num=None, shortname=None):
    loc = _location(path=path, nugget_num=nugget_num, shortname=shortname)
    _errors.append(_format(loc, msg))


def warning(msg, path=None, nugget_num=None, shortname=None):
    loc = _location(path=path, nugget_num=nugget_num, shortname=shortname)
    _warnings.append(_format(loc, msg))


def has_errors():
    return len(_errors) > 0


def has_warnings():
    return len(_warnings) > 0


def print_all():
    for line in _errors:
        print(f"Error: {line}", file=sys.stderr)
    for line in _warnings:
        print(f"Warning: {line}", file=sys.stderr)
