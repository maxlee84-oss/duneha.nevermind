# No Gemini 운영 기준

## 변경 사항

Gemini API를 완전히 제거했습니다.

- `scripts/normalize_with_gemini.py` 삭제
- `api/cloudflare-worker-gemini-search.example.js` 삭제
- `assets/js/ai.js` 삭제
- HTML의 AI 검색 섹션 제거
- GitHub Actions에서 `GEMINI_API_KEY` 사용 제거

## daily workflow

```text
fetch_sources.py
→ update_without_gemini.py
→ validate_data.py
→ build_discord_message.py
→ commit if changed
→ deploy
```

## 동작 방식

매일 오전 8시 KST에 다음을 확인합니다.

- dune.gaming.tools
- Method.gg Deep Desert Companion
- Method.gg Overland Companion
- Method.gg Database
- 공식 뉴스

소스 페이지의 HTML hash가 바뀌면 `data/update_log.json`에 변경 감지를 기록합니다.

## 한계

Gemini를 제거했기 때문에 변경된 페이지 내용을 자동으로 해석하여 DD/던전 드랍 테이블을 갱신하지는 않습니다.  
대신 마지막 검증된 `weekly.json`을 유지하여 잘못된 자동 업데이트를 방지합니다.
