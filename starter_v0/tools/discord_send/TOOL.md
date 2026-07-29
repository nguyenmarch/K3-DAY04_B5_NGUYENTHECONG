---
name: discord_send
track: team
kind: action
provider: Discord Webhook API
requires_env: [DISCORD_WEBHOOK_URL]
inputs: [text, confirmed]
outputs: [status, message]
side_effect: true
---
# discord_send

Posts plain text to the Discord channel configured by `DISCORD_WEBHOOK_URL`.
It returns `needs_confirmation` without sending unless `confirmed=true`.
Webhook URLs are secrets and are never returned in results or errors.
