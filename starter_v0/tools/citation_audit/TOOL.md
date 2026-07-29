---
name: citation_audit
track: team
kind: local_validator
requires_env: []
inputs: [items, require_https]
outputs: [status, item_count, valid_count, issues, duplicate_urls]
side_effect: false
---
# citation_audit

Audits source metadata supplied by the user. It checks URL shape, HTTPS,
missing titles/sources, and duplicate URLs. It does not access the network and
does not claim that a source or its content is true.
