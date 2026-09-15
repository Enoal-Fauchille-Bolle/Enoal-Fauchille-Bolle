#!/usr/bin/env python3
"""Render ../README.md from content.toml and the Jinja2 templates next to this file.

Usage:
  python3 readme/build.py           write README.md
  python3 readme/build.py --check   write nothing; exit 1 and print a diff if README.md is out of date
"""

import argparse
import difflib
import sys
import tomllib
from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, StrictUndefined

HERE = Path(__file__).resolve().parent
README = HERE.parent / "README.md"


def translate(value, lang):
    """Pick the `lang` version of a translated table; return a language-neutral string as is."""
    if not isinstance(value, dict):
        return value
    if lang not in value:
        sys.exit(f"content.toml: missing '{lang}' translation in {value}")
    return value[lang]


def render():
    env = Environment(
        loader=FileSystemLoader(HERE),
        undefined=StrictUndefined,  # a missing key or translation fails the build
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["tr"] = translate
    env.filters["urlquote"] = lambda s: quote(s, safe="")  # "C/C++" -> "C%2FC%2B%2B"
    content = tomllib.loads((HERE / "content.toml").read_text(encoding="utf-8"))
    return env.get_template("readme.md.j2").render(content)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if README.md is out of date")
    args = parser.parse_args()

    output = render()
    current = README.read_text(encoding="utf-8") if README.exists() else ""

    if args.check:
        if output == current:
            print("README.md is up to date.")
            return 0
        sys.stdout.writelines(difflib.unified_diff(
            current.splitlines(keepends=True), output.splitlines(keepends=True),
            "README.md (committed)", "README.md (generated)",
        ))
        print("\nREADME.md is out of date: run `python3 readme/build.py` and commit the result.")
        return 1

    README.write_text(output, encoding="utf-8")
    print("README.md written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
