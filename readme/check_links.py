#!/usr/bin/env python3
"""Check every link and image of ../README.md.

- a link must answer 200 on its own site: a redirect to another domain means it moved (gemini.ai ended up
  on a crypto exchange); a redirect within the same site (language, trailing slash) is only reported;
- a badge with a logo must embed that logo: shields.io draws the badge without it, silently, when the name is unknown;
- a local image must exist.

A site that refuses bots (403, 429) cannot be checked: it gets a warning, not a failure.

Usage: python3 readme/check_links.py
"""

import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
CONTENT = ROOT / "readme" / "content.toml"

# LinkedIn answers bots with 999/405 whatever the URL: checking it only produces false alarms.
SKIPPED_HOSTS = ("www.linkedin.com",)

# "Not for bots" rather than "gone": Cloudflare sends these to GitHub's datacenter IPs
# (en.cppreference.com 403, docs.ansible.com 429) while the pages load fine in a browser.
BOT_REFUSALS = (403, 429)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,image/svg+xml,*/*",
}


def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.url, response.read()


def check(url, is_image):
    """Return (level, message): level is "ok", "warn" or "fail"; message is None when there is nothing to say."""
    if url.startswith("./"):
        return ("ok", None) if (ROOT / url).exists() else ("fail", "file not found")
    if url.startswith("mailto:") or urlsplit(url).hostname in SKIPPED_HOSTS:
        return "ok", "skipped"
    try:
        status, final_url, body = fetch(url)
    except urllib.error.HTTPError as error:
        if error.code in BOT_REFUSALS:
            return "warn", f"HTTP {error.code}, refused to a bot: check it in a browser"
        return "fail", f"HTTP {error.code}"
    except Exception as error:  # DNS, timeout, TLS...
        return "fail", str(error)
    if status != 200:
        return "fail", f"HTTP {status}"
    if is_image and "/badge/" in url and "logo=" in url and b"<image" not in body:
        return "fail", "badge has no logo (unknown logo name?)"
    if final_url != url:
        moved = urlsplit(final_url).hostname != urlsplit(url).hostname
        return ("fail" if moved else "ok"), f"redirects to {final_url}"
    return "ok", None


def locate(url):
    """Where to fix a URL: its line in content.toml, else in README.md (badge images are built by build.py)."""
    for path in (CONTENT, README):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if url in line:
                return path.relative_to(ROOT), number
    return README.relative_to(ROOT), 1


def annotate(level, url, message):
    """In GitHub Actions, pin warnings and failures to the source line in the run summary."""
    if os.environ.get("GITHUB_ACTIONS") == "true" and level != "ok":
        file, line = locate(url)
        print(f"::warning file={file},line={line},title=Link {level}::{url} {message}")


def main():
    text = README.read_text(encoding="utf-8")
    links = re.findall(r'href="([^"]+)"', text) + re.findall(r"\]\((https?://[^)]+)\)", text)
    images = re.findall(r'src="([^"]+)"', text)

    counts = {"ok": 0, "warn": 0, "fail": 0}
    for url, is_image in dict.fromkeys([(u, False) for u in links] + [(u, True) for u in images]):
        level, message = check(url, is_image)
        counts[level] += 1
        print(f"{level.upper():4} {url}" + (f"  ({message})" if message else ""))
        annotate(level, url, message)

    print(f"\n{counts['fail']} broken, {counts['warn']} not checkable, {counts['ok']} ok.")
    return 1 if counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
