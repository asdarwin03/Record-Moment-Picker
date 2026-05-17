# Architecture

이 문서는 Record Moment Picker의 시스템 구조와 컴포넌트 책임을 정의합니다.

---

## 1. 시스템 개요

```txt
Frontend ──HTTP──> Backend ──HTTP──> AI Service
                     │
                     ├── backend/uploads/
                     └── backend/storage/data.json
```

Backend는 로컬 프로토타입 저장소로 `backend/storage/data.json`을 사용합니다. 운영 단계에서는 이 저장소를 DB로 확장하고, in-process background job을 별도 queue/worker로 분리할 수 있습니다.

---

## 2. 전체 데이터 흐름

```txt
1. 사용자가 Frontend에서 녹음 파일을 업로드한다.
2. Frontend가 Backend에 파일을 전송한다.
3. Backend가 파일을 저장하고 record를 processing 상태로 저장한다.
4. Backend가 202 Accepted와 record_id를 즉시 반환한다.
5. Backend background job이 AI Service에 녹음 파일 처리를 요청한다.
6. AI Service가 STT, Refine Text, Segmenting, Reasoning을 수행한다.
7. AI Service가 Final JSON을 Backend에 반환한다.
8. Backend가 Final JSON과 completed 상태를 파일 저장소에 저장한다.
9. Frontend가 status API를 polling한다.
10. Frontend가 Final JSON을 기반으로 GUI를 시각화한다.
```

---

## 3. 컴포넌트 책임

### 3.1 Frontend

- 녹음 파일 업로드 UI 제공
- 업로드된 녹음 목록 표시
- 분석 상태 polling
- 오디오 재생 기능 제공
- Final JSON 기반 시각화
- 전체 요약, 구간별 요약, 중요 순간, 근거 문장 표시
- 특정 timestamp 클릭 시 오디오 위치 이동

Frontend는 AI Service를 직접 호출하지 않습니다.

### 3.2 Backend

- 오디오 파일 업로드 처리
- 한국어 파일명 복원 및 안전한 저장 파일명 생성
- 업로드 파일 저장
- record/folder/result를 `backend/storage/data.json`에 저장
- AI Service 호출
- background processing queue 관리
- 서버 시작 시 processing record 재개
- Frontend에 API 제공

Backend는 AI 내부 구현에 의존하지 않고 HTTP API만 호출합니다.

### 3.3 AI Service

- 오디오 파일 STT 처리
- STT 결과 정제
- 의미 단위 segment 분할
- 각 segment 요약 생성
- 중요 순간 추출
- 요약 근거 추론
- Final JSON 생성

AI Service는 사용자 인증, 파일 목록 관리, 결과 저장을 담당하지 않습니다.

---

## 4. AI Pipeline

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

`AI_PIPELINE_MODE=demo`에서는 STT/LLM을 실행하지 않고 샘플 Final JSON을 반환합니다. `AI_PIPELINE_MODE=full`에서는 전체 pipeline을 실행합니다.

---

## 5. AI 모듈별 입출력

### 5.1 STT

입력:

```txt
audio file
```

출력:

```json
[
  {
    "start_time": 0.0,
    "end_time": 4.2,
    "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

### 5.2 Refine Text

입력과 출력은 같은 시간 구조를 유지합니다.

```json
[
  {
    "start_time": 0.0,
    "end_time": 4.2,
    "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

### 5.3 Segmenting

출력:

```json
[
  {
    "sid": "segment_01",
    "start_time": 0.0,
    "end_time": 15.4,
    "title": "프로젝트 설명 시작",
    "summary": [
      "Record Moment Picker 발표가 시작됨"
    ],
    "texts": [
      {
        "t_id": "001",
        "start_time": 0.0,
        "end_time": 4.2,
        "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
      }
    ],
    "important": []
  }
]
```

Segment의 `end_time`은 포함된 마지막 발화의 `end_time`을 기준으로 합니다.

### 5.4 Reasoning

Structured JSON에 `clues`를 추가합니다.

```json
[
  {
    "sid": "segment_01",
    "start_time": 0.0,
    "end_time": 15.4,
    "title": "프로젝트 설명 시작",
    "summary": [
      "Record Moment Picker 발표가 시작됨"
    ],
    "texts": [
      {
        "t_id": "001",
        "start_time": 0.0,
        "end_time": 4.2,
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

---

## 6. Backend 처리 흐름

```txt
POST /api/records
→ audio file 수신
→ 원본 파일명 복원
→ 안전한 stored filename 생성
→ backend/uploads/에 파일 저장
→ backend/storage/data.json에 record 생성
→ queueRecordProcessing(record_id)
→ Frontend에 202 Accepted 반환
```

Background job:

```txt
record 상태 processing
→ AI Service /process-audio 호출
→ Final JSON 수신
→ record.result 저장
→ record 상태 completed
```

실패 시:

```txt
record 상태 failed
→ error message 저장
→ Frontend status API에서 확인
```

---

## 7. 파일 기반 저장소

저장 파일은 다음 구조를 가집니다.

```txt
backend/storage/data.json
```

저장 대상:

- folders
- records
- record status
- original/stored filename
- upload path
- audio URL
- Final JSON
- error message
- created/completed timestamp

주의사항:

- 단일 로컬 개발 환경을 위한 저장 방식입니다.
- 여러 Backend 프로세스가 동시에 쓰는 구조에는 적합하지 않습니다.
- 운영 환경에서는 DB와 durable job queue가 필요합니다.

---

## 8. 향후 DB 전환 모델

파일 저장소는 운영 단계에서 다음 DB 모델로 확장할 수 있습니다.

### `users`

```txt
id
email
password_hash
name
created_at
updated_at
```

### `records`

```txt
id
user_id
original_filename
stored_filename
file_path
audio_url
duration
status
error_message
created_at
updated_at
completed_at
```

### `record_results`

```txt
id
record_id
final_json
created_at
updated_at
```

초기에는 `final_json`을 JSON column으로 저장해도 충분합니다. 검색, 필터링, 통계 기능이 필요해지면 segment, transcript, clue 단위 테이블로 정규화할 수 있습니다.

---

## 9. Job Queue 확장 모델

Background job은 Backend 프로세스 내부에서 실행됩니다.

긴 파일 처리와 여러 사용자 동시 업로드를 안정적으로 지원하려면 다음 구조로 확장하는 것이 좋습니다.

```txt
Frontend
→ Backend
→ Durable Job Queue
→ AI Worker
→ Database
→ Frontend polling 또는 websocket
```

이 구조로 바꾸면 Backend 재시작, AI worker 장애, 긴 STT 작업에 더 안정적으로 대응할 수 있습니다.

---

## 10. Frontend 시각화 매핑

```txt
sid
→ segment 고유 식별자

start_time, end_time
→ timeline 구간 표시

texts[].start_time
→ transcript 클릭 시 재생 이동

texts[].end_time
→ 발화 종료와 segment 종료 계산

title
→ 구간 제목

summary
→ 전체 요약 및 구간별 요약 표시

important
→ 중요한 순간 목록 및 timeline marker 표시

clues
→ 요약 문장과 근거 원문 연결
```

---

## 11. 설계 원칙

1. Frontend는 Backend만 호출한다.
2. Backend는 AI 내부 구현을 알지 않는다.
3. AI Service는 Final JSON 계약을 안정적으로 반환한다.
4. JSON schema는 `shared/schemas`를 기준으로 한다.
5. transcript item은 `{ start_time, end_time, text }`를 기준으로 한다.
6. AI 단계별 출력은 schema validation을 통과해야 한다.
7. 저장은 Backend가 담당한다.
8. 긴 파일 처리는 동기 HTTP 응답이 아니라 background job으로 처리한다.
