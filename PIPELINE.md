# 🩳 Bicycle Outer Cycle Pipeline 구축 기록

> 노션 원문: https://miraeasset-design.notion.site/Bicycle-Outer-Cycle-Pipline-328244fb0a68803fad58fc97a922cfe4

---

## 목표

간단한 데모 프로젝트의 dev/build 파이프라인을 **멀티 에이전트**로 구축 및 입증

### 에이전트 구성
| 에이전트 | 역할 |
|---|---|
| 디자이너 에이전트 | 피그마 시안 작업, 디자인 토큰 관리 |
| 프론트엔드 에이전트 | React 구현, 피그마 토큰 → 코드 반영 |
| 백엔드 에이전트 | FastAPI 구현, 노션 요건 변경 감지 → 코드 변경 |

---

## 인프라

| 항목 | 상태 | URL |
|---|---|---|
| DB | ✅ 배포완료 | Railway PostgreSQL (autorack.proxy.rlwy.net:57803) |
| 앱 서버 (FastAPI) | ✅ 배포완료 | https://backend-production-c2b7.up.railway.app |
| 웹 서버 (React) | ✅ 배포완료 | https://frontend-production-78d4.up.railway.app |

---

## Claude 플로우

```
[노션 요건 변경 감지]
        ↓
[백엔드 에이전트] → FastAPI 기능 변경 → GitHub 커밋 → Railway 자동 배포

[피그마 시안 작업]
        ↓
[디자이너 에이전트] → 사람에게 확인 요청 (사람이 수정 가능)
        ↓
[프론트엔드 에이전트] → 디자인 토큰 read → GitHub FE 코드 업데이트 → Railway 자동 배포
```

---

## POC 요건

- [x] DB의 인사 메시지를 읽어 React로 인사 페이지 생성
- [x] 세션/브라우저 고유값 기반으로 `{유저고유값}님 {인사메시지}!` 문구 표시
- [x] 버튼 클릭 시 DB에 반응값 업데이트

---

## 웹훅 플로우

```
노션 페이지 변경
      ↓
Notion Webhook (베타) → POST /notion-webhook
      ↓
백엔드가 Notion API로 페이지 재조회
      ↓
greetings 테이블 업데이트
      ↓
프론트엔드 다음 요청 시 새 메시지 반영
```

### 웹훅 등록 방법 (Notion 대시보드)
1. Notion → Settings → Integrations → Webhooks (beta)
2. URL: `https://backend-production-c2b7.up.railway.app/notion-webhook`
3. 이벤트: `page.updated`
4. Secret: Railway 백엔드 환경변수 `NOTION_WEBHOOK_SECRET` 값으로 검증

---

## 작업 로그

### 2026-03-19
- 노션 페이지 요건 확인 완료
- 프로젝트 디렉토리 초기화
- DB 스키마 생성 (greetings, user_reactions)
- FastAPI 백엔드 + React 프론트엔드 구현
- Railway 3개 서비스 배포 완료 (DB, backend, frontend)
- GitHub 연결 및 push

### 2026-03-20
- 프론트엔드 VITE_API_URL 환경변수 설정 및 재배포
- Notion 웹훅 엔드포인트 추가 (`POST /notion-webhook`)
- 웹훅 서명 검증 + 페이지 변경 시 DB 자동 업데이트 로직 구현

---

## 디렉토리 구조 (예정)

```
investment-agent-poc/
├── PIPELINE.md           # 이 파일 - 전체 기록
├── backend/              # FastAPI 앱
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/             # React 앱
    ├── src/
    ├── package.json
    └── Dockerfile
```

## 환경변수

| 변수 | 서비스 | 설명 |
|---|---|---|
| `DATABASE_URL` | backend | Railway PostgreSQL 연결 문자열 |
| `NOTION_WEBHOOK_SECRET` | backend | 웹훅 서명 검증 시크릿 |
| `NOTION_TOKEN` | backend | Notion API 토큰 (페이지 재조회용) |
| `NOTION_PAGE_ID` | backend | 모니터링할 Notion 페이지 ID |
| `VITE_API_URL` | frontend | 백엔드 API 베이스 URL |

> 민감한 값은 `.env.local`로 관리 (git 제외)