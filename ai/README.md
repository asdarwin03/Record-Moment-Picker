# AI Service

이 디렉토리는 Record Moment Picker의 AI 처리 파이프라인을 담당합니다.

AI Service는 Python 기반 FastAPI 서버로 동작하며, Backend는 내부 코드를 직접 import하지 않고 HTTP API를 호출합니다.

---

## 1. 처리 파이프라인

```txt
Audio File
→ STT
→ Text with start_time/end_time
→ Refine Text
→ Refined text with start_time/end_time
→ Segmenting Important Parts
→ Structured JSON
→ Reasoning of Segmenting Results
→ Final JSON
```

`AI_PIPELINE_MODE`로 실행 방식을 선택합니다.

- `demo`: 실제 STT/LLM을 실행하지 않고 샘플 Final JSON을 반환합니다.
- `full`: STT, refine text, segmenting, reasoning 전체를 실행합니다.

---

## 2. AI Service의 책임

1. 녹음 파일을 텍스트로 변환한다.
2. STT 결과의 오타와 비문을 정제한다.
3. 정제된 텍스트를 의미 있는 구간으로 분할한다.
4. 각 구간의 제목, 요약, 중요 순간을 생성한다.
5. 각 요약이 어떤 원문 발화를 근거로 하는지 reasoning 결과를 생성한다.
6. Frontend와 Backend가 사용할 수 있는 Final JSON을 반환한다.

AI Service는 사용자 인증, 파일 목록 관리, 결과 저장을 담당하지 않습니다.

---

## 3. 데이터 계약

STT와 refined text의 기본 단위는 다음 구조입니다.

```json
{
  "start_time": 0.0,
  "end_time": 4.2,
  "text": "첫 번째 발화입니다."
}
```

Segmenting 이후 `texts`에는 `t_id`가 추가됩니다.

```json
{
  "t_id": "001",
  "start_time": 0.0,
  "end_time": 4.2,
  "text": "첫 번째 발화입니다."
}
```

중요한 순간은 특정 순간을 가리키므로 `time`을 사용합니다.

```json
{
  "time": 0.0,
  "title": "핵심 안내"
}
```

자세한 계약은 `../docs/json-schema.md`와 `../shared/schemas/`를 기준으로 합니다.

---

## 4. 주요 디렉토리

```txt
ai/
├── README.md
├── requirements.txt
├── app/
│   ├── main.py
│   ├── pipeline.py
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── schemas/
│   │   ├── stt.py
│   │   ├── refined_text.py
│   │   ├── segment.py
│   │   └── final_result.py
│   ├── modules/
│   │   ├── stt/
│   │   ├── refine_text/
│   │   ├── segmenting/
│   │   └── reasoning/
│   └── clients/
│       └── llm_client.py
└── samples/
```

---

## 5. API

### POST `/process-audio`

오디오 파일을 받아 전체 pipeline을 실행합니다.

```txt
Content-Type: multipart/form-data

file: audio file
```

`AI_PIPELINE_MODE=demo`에서는 샘플 결과를 반환합니다. `full`에서는 실제 STT와 LLM 호출을 수행합니다.

### POST `/process-stt`

STT만 단독 테스트합니다.

```json
{
  "status": "success",
  "data": [
    {
      "start_time": 0.0,
      "end_time": 4.2,
      "text": "첫 번째 발화입니다."
    }
  ],
  "message": null
}
```

### POST `/process-text`

STT를 건너뛰고 refine text부터 실행합니다.

```json
{
  "items": [
    {
      "start_time": 0.0,
      "end_time": 4.2,
      "text": "안냥하세요."
    }
  ]
}
```

### GET `/health`

```json
{
  "status": "ok"
}
```

---

## 6. 실행 방법

PowerShell에서는 실행 정책 때문에 activation이 막힐 수 있습니다. 그 경우 `.venv`의 Python을 직접 호출합니다.

```powershell
cd ai
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

긴 파일을 처리할 때는 `--reload`를 빼는 것을 권장합니다. reload process가 STT 작업과 충돌하거나 종료를 지연시킬 수 있습니다.

개발 중 코드 변경 감지가 필요할 때만 다음처럼 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

---

## 7. 환경 변수

루트 `.env` 파일을 읽습니다. `.env.example`을 복사해서 사용합니다.

```powershell
Copy-Item ..\.env.example ..\.env
```

주요 값:

```env
AI_PIPELINE_MODE=demo
AI_MAX_AUDIO_UPLOAD_BYTES=26214400

STT_PROVIDER=whisper
WHISPER_MODEL=tiny
WHISPER_DEVICE=cpu
WHISPER_CPU_THREADS=2

LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
LLM_TEMPERATURE=0.0
```

주의사항:

- `OPENAI_API_KEY`는 실제 ASCII API key여야 합니다. `your-key`, 한글, 따옴표가 섞인 placeholder는 실패합니다.
- `WHISPER_DEVICE`는 `cpu` 또는 `cuda`입니다.
- CPU 사용량이 부담되면 `WHISPER_MODEL=tiny`, `WHISPER_CPU_THREADS=1~2`로 낮춥니다.
- 긴 파일에서 LLM timeout이 반복되면 `LLM_TIMEOUT_SECONDS`와 Backend의 `AI_REQUEST_TIMEOUT_MS`를 함께 늘립니다.
- MP3/M4A 처리를 위해 `ffmpeg`가 필요합니다.

---

## 8. STT Provider

Provider 후보:

- `whisper`
- `whisperx`
- `openai`

로컬 CPU에서 가장 단순하게 확인하려면:

```env
STT_PROVIDER=whisper
WHISPER_MODEL=tiny
WHISPER_DEVICE=cpu
WHISPER_CPU_THREADS=2
```

Whisper 로컬 실행은 처음 모델을 받을 때 시간이 걸리고, 긴 파일에서는 CPU/메모리를 많이 사용할 수 있습니다.

---

## 9. 개발 원칙

1. 각 모듈은 입력 JSON과 출력 JSON을 명확히 유지합니다.
2. prompt는 `prompt.py`에 분리합니다.
3. LLM 호출 코드는 `clients/llm_client.py`에 모읍니다.
4. `service.py`는 외부에서 호출할 수 있는 명확한 함수만 제공합니다.
5. timestamp는 초 단위 number로 통일합니다.
6. transcript item은 `{ start_time, end_time, text }`를 유지합니다.
7. AI 내부 결과는 schema validation을 거친 뒤 반환합니다.
8. 예외 발생 시 Backend가 이해할 수 있는 에러 메시지를 반환합니다.
