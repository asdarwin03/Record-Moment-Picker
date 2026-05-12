# API Specification

이 문서는 Record Moment Picker의 Backend API와 AI Service API를 정의합니다.

---

## 1. API 설계 원칙

1. Frontend는 Backend API만 호출합니다.
2. Backend는 AI Service API를 호출합니다.
3. Frontend는 AI Service를 직접 호출하지 않습니다.
4. AI Service는 사용자 인증과 DB 저장을 담당하지 않습니다.
5. Backend는 Final JSON을 DB에 저장하고 Frontend에 제공합니다.
6. 모든 응답은 가능한 한 일관된 JSON 구조를 사용합니다.

---

## 2. Backend 공통 응답 형식

이 형식은 Frontend가 호출하는 Backend API의 기본 응답 형식입니다.  
AI Service API는 Backend 내부 호출용이므로 `status`, `data`, `message` 형식을 사용합니다.

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

# 3. Backend API

Base URL 예시:

```txt
http://localhost:3000/api
```

---

## 3.1 Auth API

## POST `/auth/register`

회원가입 API입니다.

Request Body:

```json
{
  "email": "user@example.com",
  "password": "password1234",
  "name": "홍길동"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "email": "user@example.com",
    "name": "홍길동"
  },
  "message": null
}
```

---

## POST `/auth/login`

로그인 API입니다.

Request Body:

```json
{
  "email": "user@example.com",
  "password": "password1234"
}
```

Response:

```json
{
  "success": true,
  "data": {
    "access_token": "jwt-token",
    "user": {
      "user_id": 1,
      "email": "user@example.com",
      "name": "홍길동"
    }
  },
  "message": null
}
```

---

## GET `/auth/me`

현재 로그인한 사용자 정보를 조회합니다.

Headers:

```txt
Authorization: Bearer {access_token}
```

Response:

```json
{
  "success": true,
  "data": {
    "user_id": 1,
    "email": "user@example.com",
    "name": "홍길동"
  },
  "message": null
}
```

---

# 3.2 Record API

## POST `/records`

녹음 파일을 업로드하고 분석을 요청합니다.

초기 MVP에서는 이 API가 파일 업로드, AI 처리 요청, DB 저장까지 한 번에 수행할 수 있습니다.  
처리 시간이 길어질 경우 비동기 방식으로 분리하는 것을 권장합니다.

Headers:

```txt
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

Request:

```txt
file: audio file
```

Response:

```json
{
  "success": true,
  "data": {
    "record_id": 1,
    "status": "completed",
    "result": [
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
  },
  "message": null
}
```

---

## GET `/records`

현재 사용자의 녹음 분석 목록을 조회합니다.

Headers:

```txt
Authorization: Bearer {access_token}
```

Response:

```json
{
  "success": true,
  "data": [
    {
      "record_id": 1,
      "original_filename": "meeting.m4a",
      "status": "completed",
      "created_at": "2026-05-13T10:00:00Z",
      "completed_at": "2026-05-13T10:03:00Z"
    }
  ],
  "message": null
}
```

---

## GET `/records/{record_id}`

특정 녹음 분석 결과를 조회합니다.

Headers:

```txt
Authorization: Bearer {access_token}
```

Response:

```json
{
  "success": true,
  "data": {
    "record_id": 1,
    "original_filename": "meeting.m4a",
    "status": "completed",
    "result": [
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
  },
  "message": null
}
```

---

## DELETE `/records/{record_id}`

특정 녹음 기록을 삭제합니다.

Headers:

```txt
Authorization: Bearer {access_token}
```

Response:

```json
{
  "success": true,
  "data": {
    "record_id": 1
  },
  "message": "Record deleted"
}
```

---

# 3.3 Processing Status API

비동기 처리 방식으로 전환할 경우 사용하는 API입니다.

## GET `/records/{record_id}/status`

분석 상태를 조회합니다.

Headers:

```txt
Authorization: Bearer {access_token}
```

Response:

```json
{
  "success": true,
  "data": {
    "record_id": 1,
    "status": "processing",
    "progress": {
      "stage": "segmenting",
      "percentage": 60
    }
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

`stage` 값:

```txt
uploaded
stt
refine_text
segmenting
reasoning
completed
failed
```

---

# 4. AI Service API

Base URL 예시:

```txt
http://localhost:8000
```

AI Service API는 Backend에서만 호출합니다.

---

## POST `/process-audio`

오디오 파일을 받아 전체 AI 파이프라인을 실행합니다.

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

---

## POST `/process-text`

개발 및 테스트용 API입니다.  
STT를 건너뛰고 timestamp가 포함된 transcript를 입력받아 Refine Text부터 실행합니다.

Request Body:

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

Response:

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

---

## GET `/health`

AI Service 상태 확인 API입니다.

Response:

```json
{
  "status": "ok"
}
```

---

# 5. 에러 응답

## 5.1 Backend 에러 예시

인증 실패:

```json
{
  "success": false,
  "data": null,
  "message": "Unauthorized"
}
```

파일 누락:

```json
{
  "success": false,
  "data": null,
  "message": "Audio file is required"
}
```

분석 결과 없음:

```json
{
  "success": false,
  "data": null,
  "message": "Record not found"
}
```

---

## 5.2 AI Service 에러 예시

STT 실패:

```json
{
  "status": "failed",
  "data": null,
  "message": "STT processing failed"
}
```

schema validation 실패:

```json
{
  "status": "failed",
  "data": null,
  "message": "Final result schema validation failed"
}
```

---

# 6. MVP 단계 API 우선순위

MVP에서 먼저 구현할 API는 다음과 같습니다.

```txt
Backend
1. POST /api/records
2. GET /api/records
3. GET /api/records/{record_id}

AI Service
1. POST /process-audio
2. POST /process-text
3. GET /health
```

로그인 기능은 프로젝트 요구사항에 포함되지만, AI 및 GUI 프로토타입을 먼저 확인하려면 mock user 방식으로 시작할 수 있습니다.

---

# 7. Frontend 사용 기준

Frontend는 다음 순서로 API를 사용합니다.

```txt
1. 사용자가 로그인한다.
2. 사용자가 파일을 업로드한다.
3. POST /api/records 호출
4. record_id와 result를 받는다.
5. result를 기반으로 화면을 표시한다.
6. 이후 GET /api/records로 과거 분석 목록을 불러온다.
7. GET /api/records/{record_id}로 특정 결과를 다시 표시한다.
```
