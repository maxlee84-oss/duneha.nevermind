# v7.5.4 Pretendard Typography Pass

## 적용 방식

Pretendard Variable 웹폰트를 CDN으로 로드합니다.

```html
@import url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css");
```

## 반영 영역

- body
- navigation
- buttons
- form controls
- gear cards
- crafting lookup
- route cards
- badges / chips

## 배포 정책

폰트 파일은 ZIP 내부에 포함하지 않습니다.  
GitHub Pages에서 CDN을 통해 로드하고, 실패 시 Noto Sans KR / Apple SD Gothic Neo / Malgun Gothic 순서로 fallback 됩니다.
