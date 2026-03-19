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

| 항목 | 상태 | 내용 |
|---|---|---|
| DB | ✅ 완료 | PostgreSQL on Railway |
| 앱 서버 | ⏳ 미구축 | FastAPI, Railway Docker |
| 웹 서버 | ⏳ 미구축 | React, Railway Docker |

### DB 연결 정보
```
postgresql://postgres:blcNIypSPOJJlnCujwqqjOgOMOjnmaqq@autorack.proxy.rlwy.net:57803/railway
```

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

- [ ] DB의 인사 메시지를 읽어 React로 인사 페이지 생성
- [ ] 세션/브라우저 고유값 기반으로 `{유저고유값}님 {인사메시지}!` 문구 표시
- [ ] 버튼 클릭 시 DB에 반응값 업데이트

---

## 작업 로그

### 2026-03-19
- 노션 페이지 요건 확인 완료
- 프로젝트 디렉토리 초기화 및 PIPELINE.md 생성
- 다음 단계: DB 연결 확인 및 스키마 설계

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
