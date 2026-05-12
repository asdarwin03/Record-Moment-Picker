# AI Service

이 디렉토리는 Record Moment Picker의 AI 처리 파이프라인을 담당합니다.

AI Service는 녹음 파일을 입력받아 다음 과정을 거쳐 최종 JSON을 생성합니다.

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
```

AI Service는 Python 기반 독립 서버로 동작하며, Backend는 이 내부 코드를 직접 import하지 않고 HTTP API를 통해 호출합니다.

---

## 1. AI Service의 책임

AI Service의 책임은 다음과 같습니다.

1. 녹음 파일을 텍스트로 변환한다.
2. STT 결과의 오타와 비문을 정제한다.
3. 정제된 텍스트를 의미 있는 구간으로 분할한다.
4. 각 구간의 제목, 요약, 중요 순간을 생성한다.
5. 각 요약이 어떤 원문 발화를 근거로 하는지 reasoning 결과를 생성한다.
6. Frontend와 Backend가 사용할 수 있는 Final JSON을 반환한다.

AI Service는 사용자 인증, DB 저장, 파일 목록 관리, 클라이언트 응답 관리를 직접 담당하지 않습니다.  
이 기능들은 Backend의 책임입니다.

---

## 2. 권장 디렉토리 구조

아래 구조는 AI Service가 최종적으로 갖추면 좋은 권장 구조입니다.  
현재 MVP 단계에서는 일부 파일이나 테스트 디렉토리가 비어 있거나 아직 생성되지 않았을 수 있습니다.

```txt
ai/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
│
├── app/
│   ├── main.py
│   ├── pipeline.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   │
│   ├── schemas/
│   │   ├── stt.py
│   │   ├── refined_text.py
│   │   ├── segment.py
│   │   └── final_result.py
│   │
│   ├── modules/
│   │   ├── stt/
│   │   │   ├── service.py
│   │   │   └── providers/
│   │   │       ├── whisper.py
│   │   │       ├── whisperx.py
│   │   │       └── faster_whisper.py
│   │   │
│   │   ├── refine_text/
│   │   │   ├── service.py
│   │   │   └── prompt.py
│   │   │
│   │   ├── segmenting/
│   │   │   ├── service.py
│   │   │   └── prompt.py
│   │   │
│   │   └── reasoning/
│   │       ├── service.py
│   │       └── prompt.py
│   │
│   ├── clients/
│   │   └── llm_client.py
│   │
│   └── tests/
│       ├── test_pipeline.py
│       ├── test_refine_text.py
│       ├── test_segmenting.py
│       └── test_reasoning.py
│
└── samples/
    ├── input_audio/
    ├── stt_output.json
    ├── refined_text.json
    ├── structured_segments.json
    └── final_result.json
```

---

## 3. 모듈별 역할

### 3.1 `stt/`

음성 파일을 timestamp가 포함된 텍스트 배열로 변환합니다.

입력:

```txt
.m4a, .mp3, .wav 등의 audio file
```

출력:

```json
[
  {
    "time": 41,
    "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

STT는 기본적으로 Whisper 기반으로 처리합니다.

사용 가능한 Whisper 구현 후보는 다음과 같습니다.

- whisper
- WhisperX
- faster-whisper

STT 모듈의 출력은 반드시 `shared/schemas/stt-output.schema.json`을 만족해야 합니다.

---

### 3.2 `refine_text/`

STT 결과의 오타, 비문, 잘못 인식된 단어를 정제합니다.

입력:

```json
[
  {
    "time": 41,
    "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

출력:

```json
[
  {
    "time": 41,
    "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

주의사항:

- `time` 값은 변경하지 않습니다.
- 발화 순서는 변경하지 않습니다.
- 의미를 과도하게 요약하지 않습니다.
- STT 오류를 수정하되, 원문의 정보량은 유지합니다.

---

### 3.3 `segmenting/`

정제된 텍스트를 의미 있는 구간으로 나눕니다.

입력:

```json
[
  {
    "time": 41,
    "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
  },
  {
    "time": 57,
    "text": "이 프로젝트는 생각보다 데이터 구조가 복잡합니다."
  }
]
```

출력:

```json
[
  {
    "sid": "segment_01",
    "start_time": 41,
    "end_time": 81,
    "title": "프로젝트 설명 시작",
    "summary": [
      "Record Moment Picker 발표가 시작됨",
      "프로젝트의 데이터 구조가 생각보다 복잡하다는 점을 언급함"
    ],
    "texts": [
      {
        "t_id": "001",
        "time": 41,
        "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
      },
      {
        "t_id": "002",
        "time": 57,
        "text": "이 프로젝트는 생각보다 데이터 구조가 복잡합니다."
      }
    ],
    "important": [
      {
        "time": 57,
        "title": "복잡한 데이터 구조"
      }
    ]
  }
]
```

주의사항:

- `sid`는 `segment_01`, `segment_02` 형식을 사용합니다.
- `t_id`는 전체 녹음 기준으로 고유해야 합니다.
- `start_time`은 segment에 포함된 첫 번째 발화의 시간과 일치하는 것이 좋습니다.
- `end_time`은 다음 segment 시작 직전 또는 해당 segment 종료 추정 시간으로 설정합니다.
- `summary`는 해당 segment의 핵심 내용을 리스트 형태로 작성합니다.
- `important`는 사용자가 다시 확인할 만한 중요한 시점을 나타냅니다.

---

### 3.4 `reasoning/`

Structured JSON에 요약 근거 정보를 추가합니다.

입력:

```json
[
  {
    "sid": "segment_01",
    "summary": [
      "Record Moment Picker 발표가 시작됨"
    ],
    "texts": [
      {
        "t_id": "001",
        "time": 41,
        "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
      }
    ]
  }
]
```

출력:

```json
[
  {
    "sid": "segment_01",
    "start_time": 41,
    "end_time": 81,
    "title": "프로젝트 설명 시작",
    "summary": [
      "Record Moment Picker 발표가 시작됨"
    ],
    "texts": [
      {
        "t_id": "001",
        "time": 41,
        "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
      }
    ],
    "important": [],
    "clues": [
      {
        "summary_index": 0,
        "clue": ["001"]
      }
    ]
  }
]
```

주의사항:

- `summary_index`는 0부터 시작합니다.
- `clue`에는 해당 요약의 근거가 되는 `t_id` 목록을 넣습니다.
- 근거가 불분명한 요약은 생성하지 않는 것이 좋습니다.
- `clues`는 Frontend에서 요약과 원문을 연결하는 데 사용됩니다.

---

## 4. Pipeline 구조

`pipeline.py`는 각 모듈을 순서대로 실행하는 orchestrator 역할을 합니다.

예시:

```python
from app.modules.stt.service import transcribe_audio
from app.modules.refine_text.service import refine_text
from app.modules.segmenting.service import segment_text
from app.modules.reasoning.service import add_reasoning

def run_pipeline(audio_path: str):
    stt_result = transcribe_audio(audio_path)
    refined_result = refine_text(stt_result)
    structured_segments = segment_text(refined_result)
    final_result = add_reasoning(structured_segments)

    return final_result
```

`pipeline.py`는 복잡한 AI 로직을 직접 포함하지 않는 것이 좋습니다.  
각 단계의 실제 처리는 `modules/` 내부의 `service.py`가 담당합니다.

---

## 5. FastAPI 엔드포인트 예시

AI Service는 다음 API를 제공하는 것을 권장합니다.

### POST `/process-audio`

```txt
POST /process-audio
```

입력:

```txt
multipart/form-data
file: audio file
```

출력:

```json
{
  "status": "success",
  "data": [
    {
      "sid": "segment_01",
      "start_time": 41,
      "end_time": 81,
      "title": "프로젝트 설명 시작",
      "summary": [
        "Record Moment Picker 발표가 시작됨"
      ],
      "texts": [
        {
          "t_id": "001",
          "time": 41,
          "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
        }
      ],
      "important": [],
      "clues": [
        {
          "summary_index": 0,
          "clue": ["001"]
        }
      ]
    }
  ],
  "message": null
}
```

### POST `/process-text`

개발 및 테스트용 API입니다. STT를 건너뛰고 timestamp가 포함된 transcript를 입력받아 Refine Text부터 실행합니다.

입력:

```json
{
  "items": [
    {
      "time": 41,
      "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
    }
  ]
}
```

출력:

```json
{
  "status": "success",
  "data": [
    {
      "sid": "segment_01",
      "start_time": 41,
      "end_time": 81,
      "title": "프로젝트 설명 시작",
      "summary": [
        "Record Moment Picker 발표가 시작됨"
      ],
      "texts": [
        {
          "t_id": "001",
          "time": 41,
          "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
        }
      ],
      "important": [],
      "clues": [
        {
          "summary_index": 0,
          "clue": ["001"]
        }
      ]
    }
  ],
  "message": null
}
```

### GET `/health`

출력:

```json
{
  "status": "ok"
}
```

---

## 6. 실행 방법

```bash
cd ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell:

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 7. 환경 변수

`.env.example`

```env
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
```

루트의 `.env.example`은 전체 프로젝트용 템플릿입니다. 현재 AI Service 코드는 `.env` 파일을 자동으로 읽지 않고, 실행 환경에 이미 주입된 환경 변수를 `app/core/config.py`에서 읽습니다.

`config.py`는 환경 변수를 한 번 읽어 `settings` 객체를 만들고, 이후 AI 내부 코드는 `os.getenv()`를 직접 호출하기보다 이 `settings` 값을 사용하는 구조입니다.

PowerShell 예시:

```powershell
$env:OPENAI_API_KEY="your_openai_api_key_here"
$env:STT_PROVIDER="whisper"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`.env` 파일 자동 로딩이 필요하다면 `python-dotenv`를 의존성에 추가하고 `config.py`에서 `Settings.from_env()`가 호출되기 전에 dotenv를 로드해야 합니다.

---

## 8. 테스트 전략

AI는 각 단계별로 독립 테스트가 가능해야 합니다.

```txt
test_refine_text.py
- STT output을 입력했을 때 refined text schema를 만족하는지 검사

test_segmenting.py
- refined text를 입력했을 때 structured segments schema를 만족하는지 검사

test_reasoning.py
- structured segments를 입력했을 때 final result schema를 만족하는지 검사

test_pipeline.py
- 전체 pipeline이 final result schema를 만족하는지 검사
```

---

## 9. 개발 원칙

1. 각 모듈은 입력 JSON과 출력 JSON을 명확히 유지합니다.
2. prompt는 `prompt.py`에 분리합니다.
3. LLM 호출 코드는 `clients/llm_client.py`에 모읍니다.
4. `service.py`는 외부에서 호출할 수 있는 명확한 함수만 제공합니다.
5. timestamp는 초 단위 number로 통일합니다.
6. AI 내부에서 생성한 결과는 항상 schema validation을 거친 뒤 반환합니다.
7. 예외 발생 시 Backend가 이해할 수 있는 에러 메시지를 반환합니다.

---

## 10. AI Service가 하지 않는 일

AI Service는 다음 기능을 담당하지 않습니다.

- 사용자 로그인
- 사용자 권한 관리
- DB에 최종 결과 저장
- 과거 업로드 목록 관리
- Frontend 화면 구성
- 결제 또는 배포 인증 처리

이 기능들은 Backend와 Frontend의 책임입니다.
