# Pipeline Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 사용자가 업로드별로 네 파이프라인의 모델과 고급 설정을 선택하고 재시도에도 동일 설정을 사용하도록 구현한다.

**Architecture:** Backend가 env 기반 catalog/defaults를 제공하고 설정을 레코드에 저장한다. AI 서버는 multipart 설정을 검증해 요청별 client/options를 만들며 전역 env는 변경하지 않는다.

**Tech Stack:** React, TypeScript, Express, Multer, FastAPI, Pydantic

---

### Task 1: AI Runtime Settings

- [ ] 요청 설정 Pydantic schema와 options endpoint를 추가한다.
- [ ] 요청별 LLM client와 STT options를 pipeline에 전달한다.
- [ ] 모듈 서비스 진입점에 선택적 runtime 인자를 추가한다.
- [ ] schema와 pipeline 단위 테스트를 실행한다.

### Task 2: Backend Persistence And Transport

- [ ] env 기반 model catalog와 설정 validator를 추가한다.
- [ ] options endpoint와 multipart 설정 파싱을 추가한다.
- [ ] 레코드에 pipeline settings를 저장한다.
- [ ] 최초 처리와 재시도에서 동일 설정을 AI 서버로 전달한다.
- [ ] validator와 transport 테스트를 실행한다.

### Task 3: Frontend Upload Settings Modal

- [ ] pipeline settings 타입과 API 함수를 추가한다.
- [ ] 파일 선택, 단계별 모델, 고급 설정을 포함한 modal을 구현한다.
- [ ] 기존 추가 버튼을 modal open 동작으로 교체한다.
- [ ] 업로드 요청에 선택 설정을 포함한다.
- [ ] production build와 lint를 실행한다.

### Task 4: Verification

- [ ] 비용 없는 AI 테스트를 실행한다.
- [ ] Backend Node 테스트와 문법 검사를 실행한다.
- [ ] Frontend build와 lint를 실행한다.
- [ ] `git diff --check`와 비밀값 포함 여부를 확인한다.
