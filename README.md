# Record Moment Picker

Record Moment Picker(RMP)는 긴 녹음 파일에서 중요한 순간을 자동으로 찾고, 전체 요약과 구간별 요약, 원문 근거를 오디오 타임라인과 함께 확인할 수 있게 하는 AI 기반 녹음 분석 프로토타입입니다.

사용자는 녹음 파일을 업로드하고, 시스템은 음성을 텍스트로 변환한 뒤 텍스트를 정제하고, 의미 있는 구간으로 분할합니다. 각 구간에는 제목, 요약, 중요한 순간, 요약의 근거가 되는 원문 발화가 포함됩니다.

RMP는 `Frontend → Backend → AI Service` 구조로 동작합니다. Backend는 업로드 파일과 분석 결과를 로컬 파일 저장소에 보관하고, AI 분석은 background job으로 처리합니다.

---

## 1. 프로젝트 목표

이 프로젝트의 목표는 다음과 같습니다.

1. 긴 녹음 파일에서 중요한 순간을 자동으로 탐색한다.
2. STT 결과를 정제하여 읽기 좋은 텍스트로 변환한다.
3. 녹음 내용을 의미 단위의 segment로 나눈다.
4. 각 segment에 대해 제목, 요약, 중요 순간, 근거 문장을 생성한다.
5. 최종 JSON을 기반으로 사용자가 녹음 내용을 빠르게 탐색할 수 있는 GUI를 제공한다.
6. 파일 기반 저장소를 통해 업로드 기록과 분석 결과를 다시 확인할 수 있게 한다.

---

## 2. 시스템 구조

```txt
Frontend ──HTTP──> Backend ──HTTP──> AI Service
                     │
                     ├── backend/uploads/
                     └── backend/storage/data.json
```

로컬 프로토타입 저장소는 파일 기반으로 구성됩니다.

- 업로드 파일: `backend/uploads/`
- record/folder/result metadata: `backend/storage/data.json`
- `backend/storage/`는 로컬 실행 데이터이므로 git에 올리지 않습니다.

---

## 3. 처리 흐름

```txt
1. 사용자가 Frontend에서 녹음 파일을 업로드한다.
2. Frontend가 Backend의 POST /api/records를 호출한다.
3. Backend가 파일을 backend/uploads/에 저장한다.
4. Backend가 record를 processing 상태로 backend/storage/data.json에 저장한다.
5. Backend가 즉시 202 Accepted와 record_id를 반환한다.
6. Backend background job이 AI Service의 /process-audio를 호출한다.
7. AI Service가 demo 또는 full pipeline 결과를 반환한다.
8. Backend가 Final JSON과 상태를 저장한다.
9. Frontend가 /api/records/:id/status를 polling한다.
10. completed가 되면 /api/records/:id로 결과를 조회해 화면에 표시한다.
```

서버 재시작 시 Backend는 `processing` 상태의 record를 다시 queue에 올립니다. Queue는 Node.js 프로세스 내부 background 작업으로 관리됩니다.

---

## 4. 주요 데이터 계약

Transcript item은 `start_time`, `end_time`, `text`를 기준으로 합니다.

```json
{
  "t_id": "001",
  "start_time": 0.0,
  "end_time": 4.2,
  "text": "첫 번째 발화입니다."
}
```

Segment는 포함된 발화의 시작/종료를 기준으로 합니다.

```json
{
  "sid": "segment_01",
  "start_time": 0.0,
  "end_time": 15.4,
  "title": "프로젝트 킥오프",
  "summary": ["샘플 프로젝트의 목표와 진행 방식을 논의함"],
  "texts": [],
  "important": [
    {
      "time": 0.0,
      "title": "프로젝트 목표 설명"
    }
  ],
  "clues": []
}
```

주의할 점:

- STT/refined/segment `texts`는 `{ start_time, end_time, text }`가 전제입니다.
- Segment의 `end_time`은 마지막 발화의 `end_time` 기준입니다.
- 중요한 순간(`important`)은 특정 순간이므로 `time` 필드를 유지합니다.

자세한 내용은 [docs/json-schema.md](docs/json-schema.md)를 봅니다.

---

## 5. 디렉토리별 역할

### `frontend/`

사용자가 직접 보는 웹 클라이언트입니다.

- 녹음 파일 업로드
- 업로드된 녹음 목록 조회
- 오디오 플레이어
- 타임라인 시각화
- 전체 요약과 구간별 요약 표시
- 중요 순간 표시
- 요약 근거 문장 표시

Frontend는 Backend에서 받은 Final JSON을 기준으로 화면을 구성합니다.

### `backend/`

클라이언트와 AI 서버 사이에서 요청을 중계하고, 업로드 파일과 결과 데이터를 관리합니다.

- 녹음 파일 업로드 처리
- 한국어 파일명 복원
- 로컬 업로드 파일 저장
- 파일 기반 record/folder/result 저장
- AI Service 호출
- background job 상태 관리
- 분석 결과 조회 API 제공

Backend는 AI 내부 모듈을 직접 import하지 않고 AI Service의 HTTP API만 호출합니다.

### `ai/`

녹음 파일을 분석하여 최종 JSON을 생성하는 Python 기반 AI Service입니다.

```txt
STT
→ Refine Text
→ Segmenting Important Parts
→ Reasoning of Segmenting Results
→ Final JSON
```

각 단계는 정해진 JSON 포맷을 입력받고 정해진 JSON 포맷을 반환해야 합니다.

### `shared/`

Frontend, Backend, AI가 공통으로 참조하는 JSON 계약을 저장합니다.

```txt
shared/
├── examples/
└── schemas/
```

이 폴더의 목적은 각 요소를 만든 개발자들이 같은 데이터 포맷을 기준으로 독립적으로 개발할 수 있게 하는 것입니다.

### `docs/`

프로젝트 설계 문서를 저장합니다.

```txt
docs/
├── architecture.md
├── api-spec.md
└── json-schema.md
```

---

## 6. 개발 원칙

### 6.1 AI와 Backend는 분리한다

Backend에서 Python 파일을 직접 실행하지 않습니다.

```txt
Backend → HTTP Request → AI Service
```

이렇게 분리하면 Python 의존성과 Node.js 의존성이 충돌하지 않고, AI 파이프라인을 독립적으로 실험하고 교체할 수 있습니다.

### 6.2 JSON 포맷을 안정적으로 유지한다

이 프로젝트의 핵심은 각 AI 단계가 특정 JSON을 입력받고 특정 JSON을 반환하는 것입니다.

기준이 되는 포맷은 다음과 같습니다.

- STT Output
- Refined Text
- Structured Segments
- Final Result

### 6.3 Frontend는 mock Final JSON으로 먼저 개발할 수 있다

AI가 완성되기 전에도 Frontend는 `shared/examples/final-result.example.json`을 이용해 GUI를 개발할 수 있습니다.

Frontend는 AI 구현 세부사항을 몰라도 됩니다. Final JSON의 구조만 알면 화면 구현이 가능합니다.

### 6.4 `t_id`와 `sid`는 안정적으로 유지한다

- `sid`: segment 고유 ID
- `t_id`: transcript item 고유 ID

이 값들은 GUI의 근거 표시, 타임라인 이동, 요약과 원문 연결에 사용되므로 처리 중 임의로 바뀌면 안 됩니다.

---

## 7. 권장 개발 순서

```txt
1. shared/examples와 shared/schemas 작성
2. AI pipeline skeleton 작성
3. Frontend mock data 기반 GUI 개발
4. Backend 파일 업로드 및 저장 API 개발
5. Backend와 AI Service 연결
6. Frontend와 Backend 연결
7. background job/status polling 적용
8. 통합 테스트
9. 필요 시 DB와 durable job queue로 확장
```

---

## 8. 실행 준비

루트에 `.env` 파일을 둡니다. `.env.example`을 복사해서 시작하면 됩니다.

```powershell
Copy-Item .env.example .env
```

프로토타입 확인만 할 때는 다음 설정이 안전합니다.

```env
AI_PIPELINE_MODE=demo
AI_SERVER_URL=http://localhost:8000
BACKEND_PORT=3000
VITE_BACKEND_API_URL=http://localhost:3000
```

`DATABASE_URL`은 DB 저장소로 확장할 때 사용하는 값입니다. 로컬 파일 기반 실행에서는 별도 DB 실행이 필요하지 않습니다.

실제 STT/LLM까지 돌릴 때는 다음처럼 바꿉니다.

```env
AI_PIPELINE_MODE=full
OPENAI_API_KEY=your_openai_api_key_here
STT_PROVIDER=whisper
WHISPER_MODEL=tiny
WHISPER_DEVICE=cpu
WHISPER_CPU_THREADS=2
```

`WHISPER_DEVICE`는 `cpu` 또는 `cuda`를 사용합니다. `gpu`는 올바른 값이 아닙니다.

MP3/M4A 처리를 위해 `ffmpeg`가 필요합니다.

```powershell
ffmpeg -version
```

설치가 안 되어 있으면 Windows에서 다음 명령을 사용할 수 있습니다.

```powershell
winget install Gyan.FFmpeg
```

---

## 9. 실행 방법

터미널을 3개 열고 각각 실행합니다.

### 9.1 AI Service

PowerShell 실행 정책 때문에 가상환경 activation이 막힐 수 있으므로, activation 없이 `.venv`의 Python을 직접 호출하는 방식을 권장합니다.

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

긴 파일을 처리할 때는 `--reload`를 붙이지 않는 편이 안정적입니다.

### 9.2 Backend

```powershell
cd backend
npm.cmd install
npm.cmd start
```

정상 실행 시:

```txt
Backend server listening on http://localhost:3000
```

### 9.3 Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Vite가 표시하는 주소로 접속합니다. 기본 주소는 보통 다음과 같습니다.

```txt
http://localhost:5173
```

---

## 10. 모드별 동작

### `AI_PIPELINE_MODE=demo`

- 업로드는 실제로 수행합니다.
- AI Service는 샘플 Final JSON을 반환합니다.
- STT/LLM/API key 문제 없이 화면 연결을 확인할 수 있습니다.

### `AI_PIPELINE_MODE=full`

- STT → refine text → segmenting → reasoning 전체 파이프라인을 실행합니다.
- `OPENAI_API_KEY`, `ffmpeg`, Whisper 의존성이 필요합니다.
- 긴 파일은 CPU 사용량과 처리 시간이 큽니다.
- 비동기 업로드 구조이므로 Backend HTTP timeout은 피할 수 있지만, AI 작업 자체는 오래 걸릴 수 있습니다.

---

## 11. 주요 디렉토리

```txt
frontend/                 React + Vite 클라이언트
backend/                  Express API, 업로드, 파일 기반 저장소, AI 호출
backend/uploads/          업로드된 오디오 파일
backend/storage/data.json record/folder/result 저장 파일
ai/                       FastAPI AI Service
shared/schemas/           공통 JSON Schema
shared/examples/          공통 예시 JSON
docs/                     설계/API/스키마 문서
```

---

## 12. 확장 고려사항

- 저장소는 로컬 파일 기반이라 여러 Backend 인스턴스에서 동시에 쓰기에 적합하지 않습니다.
- background job queue는 프로세스 내부 구현입니다. 운영 환경에서는 DB/job queue/worker 분리가 필요합니다.
- 20분~1시간 파일은 chunking, 진행률 저장, 외부 STT 또는 faster-whisper 기반 최적화가 필요할 수 있습니다.
- 파일명 복원은 새 업로드 요청에 적용됩니다.
