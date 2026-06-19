# Daily Automation Policy

## Schedule

```text
매일 오전 8시 KST
cron: 0 23 * * *
```

## Flow

```text
fetch_sources.py
→ update_without_gemini.py
→ validate_data.py
→ build_discord_message.py
→ auto commit if changed
→ GitHub Pages deploy
```

## Failure Handling

- Source fetch failure: error is logged.
- Gemini는 사용하지 않습니다. 소스 변경 감지만 기록합니다.
- Validation failure: candidate data is not promoted.
- Page remains on last stable version.
