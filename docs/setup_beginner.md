# 초보자용 GitHub 세팅 가이드

## 1. Repository 만들기

GitHub에서 새 repository를 만듭니다.

추천 이름:

```text
nevermind-dune-ops
```

## 2. 파일 업로드

ZIP 압축을 풀고, 폴더 안의 내용물을 repository root에 업로드합니다.

정상 구조:

```text
.github/
api/
assets/
data/
docs/
scripts/
index.html
README.md
requirements.txt
```

## 3. Pages 설정

```text
Settings → Pages → Source: GitHub Actions
```

## 4. Gemini API Key 등록 불필요

이 버전은 Gemini를 사용하지 않습니다.

## 5. 첫 수동 실행

```text
Actions → Daily Dune Ops Auto Update → Run workflow
```

## 6. 페이지 확인

```text
Settings → Pages → Your site is live at ...
```
