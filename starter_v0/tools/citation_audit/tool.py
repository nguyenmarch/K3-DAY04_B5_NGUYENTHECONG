from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def audit_citations(items: list[dict[str, Any]], require_https: bool = True) -> dict[str, Any]:
    """Audit citation metadata without fetching or mutating external state."""
    if not isinstance(items, list):
        raise TypeError("items must be a list")

    issues: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    valid_count = 0

    for index, raw_item in enumerate(items):
        item = raw_item if isinstance(raw_item, dict) else {}
        url = str(item.get("url") or "").strip()
        parsed = urlparse(url)
        item_issues: list[str] = []

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            item_issues.append("invalid_url")
        elif require_https and parsed.scheme != "https":
            item_issues.append("not_https")
        if not str(item.get("title") or "").strip():
            item_issues.append("missing_title")
        if not str(item.get("source") or "").strip():
            item_issues.append("missing_source")

        normalized_url = url.rstrip("/")
        if normalized_url:
            if normalized_url in seen:
                item_issues.append(f"duplicate_of_index_{seen[normalized_url]}")
            else:
                seen[normalized_url] = index

        if item_issues:
            issues.append({"index": index, "url": url, "issues": item_issues})
        else:
            valid_count += 1

    duplicate_urls = [
        issue["url"]
        for issue in issues
        if any(value.startswith("duplicate_of_index_") for value in issue["issues"])
    ]
    return {
        "status": "pass" if not issues else "needs_attention",
        "item_count": len(items),
        "valid_count": valid_count,
        "issues": issues,
        "duplicate_urls": duplicate_urls,
        "limitations": "Metadata audit only; content and factual accuracy were not verified.",
    }
