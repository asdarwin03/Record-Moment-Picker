# Record Moment Picker

Record Moment Picker(RMP)는 긴 녹음 파일에서 중요한 순간을 자동으로 찾아내고, 사용자가 다시 들어야 할 구간과 요약 정보를 시각적으로 확인할 수 있도록 돕는 AI 기반 녹음 분석 서비스입니다.

사용자는 녹음 파일을 업로드하고, 시스템은 음성을 텍스트로 변환한 뒤 텍스트를 정제하고, 의미 있는 구간으로 분할하며, 각 구간의 핵심 요약과 근거 문장을 포함한 최종 JSON을 생성합니다. 이후 서버는 최종 JSON을 DB에 저장하고, 클라이언트는 이 데이터를 기반으로 타임라인, 전체 요약, 구간별 요약, 중요 순간, 근거 문장을 GUI에 표시합니다.

---

## 1. 프로젝트 목표

이 프로젝트의 목표는 다음과 같습니다.

1. 긴 녹음 파일에서 중요한 순간을 자동으로 탐색한다.
2. STT 결과를 정제하여 읽기 좋은 텍스트로 변환한다.
3. 녹음 내용을 의미 단위의 segment로 나눈다.
4. 각 segment에 대해 제목, 요약, 중요 순간, 근거 문장을 생성한다.
5. 최종 JSON을 기반으로 사용자가 녹음 내용을 빠르게 탐색할 수 있는 GUI를 제공한다.
6. 로그인 및 DB 저장 기능을 통해 사용자가 과거 업로드 결과를 다시 확인할 수 있도록 한다.

---

## 2. 전체 시스템 구조

```txt
Frontend ──HTTP──> Backend ──HTTP──> AI Service
                     │
                     └── Database
```

전체 데이터 흐름은 다음과 같습니다.

```txt
Audio File
→ STT
→ Text with timestamp
→ Refine Text
→ Refined text with timestamp
→ Segmenting Important Parts
→ Structured JSON
→ Reasoning of Segmenting Results
→ Final JSON
→ Save JSON to DB
→ Visualize in Client
```

---

## 3. 주요 디렉토리 구조

```txt
record-moment-picker/
│
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── frontend/
│   └── 클라이언트 웹 애플리케이션
│
├── backend/
│   └── 서버, 인증, 파일 업로드, DB 저장, AI 서버 호출
│
├── ai/
│   └── STT, 텍스트 정제, 구간 분할, reasoning 파이프라인
│
├── shared/
│   ├── examples/
│   └── schemas/
│
└── docs/
    ├── architecture.md
    ├── api-spec.md
    └── json-schema.md
```

---

## 4. 디렉토리별 역할

### `frontend/`

사용자가 직접 보는 웹 클라이언트입니다.

주요 기능은 다음과 같습니다.

- 로그인 및 사용자 화면
- 녹음 파일 업로드
- 업로드된 녹음 목록 조회
- 오디오 플레이어
- 타임라인 시각화
- 전체 요약 표시
- 구간별 요약 표시
- 중요 순간 표시
- 요약 근거 문장 표시

Frontend는 최종적으로 Backend에서 전달받은 `Final JSON`을 기반으로 화면을 구성합니다.

---

### `backend/`

클라이언트와 AI 서버 사이에서 요청을 중계하고, 사용자 및 결과 데이터를 관리하는 서버입니다.

주요 기능은 다음과 같습니다.

- 사용자 인증
- 녹음 파일 업로드 처리
- 업로드 파일 저장
- AI Service 호출
- AI 처리 상태 관리
- Final JSON 저장
- 과거 분석 결과 조회
- Frontend에 분석 결과 제공

Backend는 AI 내부 모듈을 직접 import하지 않습니다. AI Service의 HTTP API를 호출합니다.

---

### `ai/`

녹음 파일을 분석하여 최종 JSON을 생성하는 Python 기반 AI 서비스입니다.

AI 내부 파이프라인은 다음 순서로 실행됩니다.

```txt
STT
→ Refine Text
→ Segmenting Important Parts
→ Reasoning of Segmenting Results
→ Final JSON
```

각 단계는 정해진 JSON 포맷을 입력받고, 정해진 JSON 포맷을 반환해야 합니다.

---

### `shared/`

Frontend, Backend, AI가 공통으로 참조하는 JSON 계약을 저장합니다.

```txt
shared/
├── examples/
│   ├── stt-output.example.json
│   ├── refined-text.example.json
│   ├── structured-segments.example.json
│   └── final-result.example.json
│
└── schemas/
    ├── stt-output.schema.json
    ├── refined-text.schema.json
    ├── structured-segments.schema.json
    └── final-result.schema.json
```

이 폴더의 목적은 팀원들이 같은 데이터 포맷을 기준으로 독립적으로 개발할 수 있게 하는 것입니다.

---

### `docs/`

프로젝트 설계 문서를 저장합니다.

```txt
docs/
├── architecture.md
├── api-spec.md
└── json-schema.md
```

---

## 5. 개발 원칙

### 5.1 AI와 Backend는 분리한다

Backend에서 Python 파일을 직접 실행하지 않습니다.

권장 구조는 다음과 같습니다.

```txt
Backend → HTTP Request → AI Service
```

이렇게 분리하면 Python 의존성과 Node.js 의존성이 충돌하지 않고, AI 파이프라인을 독립적으로 실험하고 교체할 수 있습니다.

---

### 5.2 JSON 포맷을 먼저 고정한다

이 프로젝트의 핵심은 각 AI 단계가 특정 JSON을 입력받고 특정 JSON을 반환하는 것입니다.

따라서 기능 구현 전에 다음 포맷을 먼저 확정해야 합니다.

- STT Output
- Refined Text
- Structured Segments
- Final Result

---

### 5.3 Frontend는 mock Final JSON으로 먼저 개발한다

AI가 완성되기 전에도 Frontend는 `shared/examples/final-result.example.json`을 이용해 GUI를 개발할 수 있습니다.

Frontend는 AI 구현 세부사항을 몰라도 됩니다.  
Final JSON의 구조만 알면 화면 구현이 가능합니다.

---

### 5.4 t_id와 sid는 안정적으로 유지한다

- `sid`: segment 고유 ID
- `t_id`: transcript item 고유 ID

이 값들은 GUI의 근거 표시, 타임라인 이동, 요약과 원문 연결에 사용되므로 처리 중 임의로 바뀌면 안 됩니다.

---

## 6. 권장 개발 순서

```txt
1. shared/examples와 shared/schemas 작성
2. AI pipeline skeleton 작성
3. Frontend mock data 기반 GUI 개발
4. Backend 파일 업로드 및 결과 저장 API 개발
5. Backend와 AI Service 연결
6. Frontend와 Backend 연결
7. 로그인 및 과거 결과 조회 기능 추가
8. 통합 테스트
```

---

## 7. 실행 방식 예시

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
npm install
npm run dev
```

### AI Service

```bash
cd ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Windows PowerShell에서는 다음과 같이 가상환경을 활성화합니다.

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

---

## 8. 환경 변수 예시

`.env.example`

```env
# Backend
BACKEND_PORT=3000
DATABASE_URL=postgresql://user:password@localhost:5432/rmp
AI_SERVER_URL=http://localhost:8000
JWT_SECRET=change_me

# AI Service
AI_HOST=0.0.0.0
AI_PORT=8000
AI_TEMP_DIR=

# STT
STT_PROVIDER=whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_TEMPERATURE=0.0

# Frontend
VITE_BACKEND_API_URL=http://localhost:3000
```

`.env.example`은 실제 실행에 직접 사용되는 파일이 아니라 필요한 환경 변수 목록을 보여주는 템플릿입니다.

현재 AI Service 코드는 `.env` 파일을 자동으로 읽지 않습니다. 실행 시점에 OS/터미널/배포 환경에 주입된 환경 변수를 `ai/app/core/config.py`가 `os.getenv()`로 한 번 읽고, 이후 내부 코드는 `settings` 객체의 값으로 사용합니다.

예를 들어 PowerShell에서는 다음처럼 필요한 값을 주입한 뒤 실행합니다.

```powershell
$env:OPENAI_API_KEY="your_openai_api_key_here"
$env:STT_PROVIDER="whisper"
cd ai
uvicorn app.main:app --reload --port 8000
```

나중에 `.env` 파일을 자동으로 읽고 싶다면 `python-dotenv`를 추가하고 `config.py`에서 환경 변수를 읽기 전에 dotenv 로드를 수행해야 합니다.

---

## 9. 최종 결과물

AI Service가 반환하고 Backend가 DB에 저장하는 최종 결과물은 `Final JSON`입니다.

Final JSON은 다음 정보를 포함합니다.

- segment ID
- segment 시작/종료 시간
- segment 제목
- segment 요약
- segment에 포함된 원문 텍스트
- 중요한 순간
- 요약의 근거가 되는 원문 ID

Frontend는 이 Final JSON을 기준으로 전체 GUI를 구성합니다.
