# API Specification

이 문서는 Record Moment Picker의 Backend API와 AI Service API를 정의합니다.

Backend는 파일과 record metadata를 저장한 뒤 `202 Accepted`를 반환하고, AI 분석을 background job으로 실행합니다. Frontend는 상태 API를 polling해서 완료 여부를 확인합니다.

---

## 1. API 설계 원칙

1. Frontend는 Backend API만 호출합니다.
2. Backend는 AI Service API를 호출합니다.
3. Frontend는 AI Service를 직접 호출하지 않습니다.
4. AI Service는 사용자 인증과 저장소 관리를 담당하지 않습니다.
5. Backend는 파일과 Final JSON을 저장하고 Frontend에 제공합니다.
6. 로컬 프로토타입 저장소는 `backend/storage/data.json`입니다.

---

## 2. Backend 공통 응답 형식

성공 응답:

```json
{
  "success": true,
  "data": {},
  "message": null
}
```

실패 응답:

```json
{
  "success": false,
  "data": null,
  "message": "Error message"
}
```

---

## 3. Backend API

Base URL:

```txt
http://localhost:3000/api
```

로컬 프로토타입은 mock user 기반으로 동작합니다. 인증 API는 설계상 포함되어 있지만 핵심 분석 흐름에는 사용하지 않습니다.

---

## 3.1 Bootstrap

### GET `/bootstrap`

Frontend 초기 화면에 필요한 폴더와 녹음 목록을 조회합니다.

Response:

```json
{
  "success": true,
  "data": {
    "folders": [
      {
        "id": "all",
        "name": "전체",
        "count": 4
      }
    ],
    "recordings": [
      {
        "id": "rec_001",
        "name": "sample-kickoff.mp3",
        "date": "2026-05-16",
        "folderId": "uncategorized",
        "status": "completed"
      }
    ]
  },
  "message": null
}
```

---

## 3.2 Record API

### POST `/records`

녹음 파일을 업로드하고 분석 job을 생성합니다.

Request:

```txt
Content-Type: multipart/form-data

file: audio file
```

Response:

```json
{
  "success": true,
  "data": {
    "record_id": "rec_20260517_001",
    "status": "processing",
    "recording": {
      "id": "rec_20260517_001",
      "name": "sample-kickoff.mp3",
      "date": "2026-05-17",
      "folderId": "uncategorized",
      "status": "processing"
    }
  },
  "message": "Record uploaded. Processing has started."
}
```

HTTP status는 `202 Accepted`입니다. 분석 결과는 이 응답에 포함되지 않습니다.

한국어 파일명은 Backend에서 multipart filename을 복원한 뒤 저장합니다.

---

### GET `/records`

녹음 분석 목록을 조회합니다.

Response:

```json
{
  "success": true,
  "data": [
    {
      "id": "rec_20260517_001",
      "name": "sample-kickoff.mp3",
      "date": "2026-05-17",
      "folderId": "uncategorized",
      "status": "completed"
    }
  ],
  "message": null
}
```

---

### GET `/records/{record_id}`

특정 녹음 분석 결과를 조회합니다.

Response:

```json
{
  "success": true,
  "data": {
    "id": "rec_20260517_001",
    "name": "sample-kickoff.mp3",
    "status": "completed",
    "audioUrl": "/uploads/1700000000000-sample-kickoff.mp3",
    "result": [
      {
        "sid": "segment_01",
        "start_time": 41.2,
        "end_time": 63.5,
        "title": "프로젝트 설명 시작",
        "summary": [
          "Record Moment Picker 발표가 시작됨"
        ],
        "texts": [
          {
            "t_id": "001",
            "start_time": 41.2,
            "end_time": 46.8,
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
  },
  "message": null
}
```

---

### GET `/records/{record_id}/status`

분석 상태를 조회합니다. Frontend는 업로드 후 이 API를 주기적으로 호출합니다.

Response:

```json
{
  "success": true,
  "data": {
    "record_id": "rec_20260517_001",
    "status": "processing",
    "stage": "ai_processing",
    "error": null
  },
  "message": null
}
```

`status` 값:

```txt
uploaded
processing
completed
failed
```

---

### DELETE `/records/{record_id}`

특정 녹음 기록을 숨김/삭제 처리합니다.

Response:

```json
{
  "success": true,
  "data": {
    "record_id": "rec_20260517_001"
  },
  "message": "Record deleted"
}
```

---

## 3.3 Folder API

폴더 정보도 파일 기반 저장소에 함께 저장됩니다.

```txt
GET /folders
POST /folders
PATCH /folders/{folder_id}
DELETE /folders/{folder_id}
PATCH /records/{record_id}/folder
```

---

## 4. AI Service API

Base URL:

```txt
http://localhost:8000
```

AI Service API는 Backend에서만 호출합니다.

---

### POST `/process-audio`

오디오 파일을 받아 전체 AI 파이프라인을 실행합니다.

`AI_PIPELINE_MODE=demo`이면 샘플 Final JSON을 반환합니다. `AI_PIPELINE_MODE=full`이면 STT, 정제, segmenting, reasoning을 모두 실행합니다.

Request:

```txt
Content-Type: multipart/form-data

file: audio file
```

Response:

```json
{
  "status": "success",
  "data": [
    {
      "sid": "segment_01",
      "start_time": 41.2,
      "end_time": 63.5,
      "title": "프로젝트 설명 시작",
      "summary": [
        "Record Moment Picker 발표가 시작됨"
      ],
      "texts": [
        {
          "t_id": "001",
          "start_time": 41.2,
          "end_time": 46.8,
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

---

### POST `/process-stt`

STT만 단독으로 테스트하는 개발용 API입니다.

Request:

```txt
Content-Type: multipart/form-data

file: audio file
```

Response:

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

---

### POST `/process-text`

STT를 건너뛰고 `{ start_time, end_time, text }` transcript를 입력받아 Refine Text부터 실행하는 개발용 API입니다.

Request Body:

```json
{
  "items": [
    {
      "start_time": 41.2,
      "end_time": 46.8,
      "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
    }
  ]
}
```

---

### GET `/health`

AI Service 상태 확인 API입니다.

Response:

```json
{
  "status": "ok"
}
```

---

## 5. 에러 응답

Backend 에러:

```json
{
  "success": false,
  "data": null,
  "message": "AI service request failed"
}
```

AI Service 에러:

```json
{
  "status": "failed",
  "data": null,
  "message": "Final result schema validation failed"
}
```

---

## 6. Frontend 사용 기준

```txt
1. Frontend가 GET /api/bootstrap으로 초기 목록을 불러온다.
2. 사용자가 파일을 업로드한다.
3. Frontend가 POST /api/records를 호출한다.
4. Backend가 record_id와 processing 상태를 즉시 반환한다.
5. Frontend가 GET /api/records/{record_id}/status를 polling한다.
6. completed가 되면 GET /api/records/{record_id}로 Final JSON을 가져온다.
7. Final JSON을 기반으로 화면을 표시한다.
```
