#!/usr/bin/env python3
"""Check every link and image of ../README.md.

- a link must answer 200 on its own site: a redirect to another domain means it moved (gemini.ai ended up
  on a crypto exchange); a redirect within the same site (language, trailing slash) is only reported;
- a badge with a logo must embed that logo: shields.io draws the badge without it, silently, when the name is unknown;
- a local image must exist.

Usage: python3 readme/check_links.py
"""

import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

README = Path(__file__).resolve().parent.parent / "README.md"

# LinkedIn answers bots with 999/405 whatever the URL: checking it only produces false alarms.
SKIPPED_HOSTS = ("www.linkedin.com",)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Accept": "text/html,image/svg+xml,*/*",
}


def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, response.url, response.read()


def check(url, is_image):
    """Return (failed, message): message is None when there is nothing to say."""
    if url.startswith("./"):
        return (False, None) if (README.parent / url).exists() else (True, "file not found")
    if url.startswith("mailto:") or urlsplit(url).hostname in SKIPPED_HOSTS:
        return False, "skipped"
    try:
        status, final_url, body = fetch(url)
    except Exception as error:  # HTTP 4xx/5xx, DNS, timeout...
        return True, str(error)
    if status != 200:
        return True, f"HTTP {status}"
    if is_image and "/badge/" in url and "logo=" in url and b"<image" not in body:
        return True, "badge has no logo (unknown logo name?)"
    if final_url != url:
        moved = urlsplit(final_url).hostname != urlsplit(url).hostname
        return moved, f"redirects to {final_url}"
    return False, None


def main():
    text = README.read_text(encoding="utf-8")
    links = re.findall(r'href="([^"]+)"', text) + re.findall(r"\]\((https?://[^)]+)\)", text)
    images = re.findall(r'src="([^"]+)"', text)

    failures = 0
    for url, is_image in dict.fromkeys([(u, False) for u in links] + [(u, True) for u in images]):
        failed, message = check(url, is_image)
        failures += failed
        print(f"{'FAIL' if failed else 'ok  '} {url}" + (f"  ({message})" if message else ""))

    print(f"\n{failures} problem(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
