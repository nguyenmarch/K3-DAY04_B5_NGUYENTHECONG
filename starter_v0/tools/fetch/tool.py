from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err


def read_url(url: str = "") -> dict[str, Any]:
    try:
        key = os.getenv("FIRECRAWL_API_KEY")
        if not key:
            raise RuntimeError("Missing FIRECRAWL_API_KEY env var")
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            json={"url": url, "formats": ["markdown"]},
            headers={"Authorization": f"Bearer {key}"},
            timeout=60,
        )
        if response.status_code == 403:
            target_domain = domain(url)
            if target_domain in {"facebook.com", "m.facebook.com"}:
                raise RuntimeError(
                    "Facebook blocked the crawler or requires a logged-in session. "
                    "Use a publicly accessible article URL, or paste the post content "
                    "directly for analysis."
                )
            raise RuntimeError(
                f"The target site ({target_domain or 'unknown domain'}) denied crawler "
                "access. Use a public URL or paste the content directly."
            )
        if response.status_code in {401, 402}:
            raise RuntimeError(
                "Firecrawl authorization or quota failed. Check FIRECRAWL_API_KEY "
                "and the Firecrawl plan/quota."
            )
        response.raise_for_status()
        data = response.json().get("data", {})
        meta = data.get("metadata", {}) or {}
        return {"tool": "read_url", "url": url, "items": [{
            "title": meta.get("title") or url,
            "url": meta.get("sourceURL") or url,
            "source": domain(url),
            "summary": (data.get("markdown") or "")[:4000],
        }]}
    except Exception as exc:
        return err("read_url", exc)
