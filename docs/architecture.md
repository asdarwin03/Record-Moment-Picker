# Architecture

이 문서는 Record Moment Picker의 전체 시스템 구조와 각 컴포넌트의 책임을 정의합니다.

---

## 1. 시스템 개요

Record Moment Picker는 긴 녹음 파일을 분석하여 중요한 순간과 요약 정보를 추출하는 서비스입니다.

전체 시스템은 크게 세 부분으로 나뉩니다.

```txt
Frontend
Backend
AI Service
```

추가로 Backend는 Database와 연결됩니다.

```txt
Frontend ──HTTP──> Backend ──HTTP──> AI Service
                     │
                     └── Database
```

---

## 2. 전체 데이터 흐름

```txt
1. 사용자가 Frontend에서 녹음 파일을 업로드한다.
2. Frontend가 Backend에 파일을 전송한다.
3. Backend가 파일을 저장한다.
4. Backend가 AI Service에 녹음 파일 처리를 요청한다.
5. AI Service가 STT, Refine Text, Segmenting, Reasoning을 수행한다.
6. AI Service가 Final JSON을 Backend에 반환한다.
7. Backend가 Final JSON을 DB에 저장한다.
8. Frontend가 Backend에서 분석 결과를 조회한다.
9. Frontend가 Final JSON을 기반으로 GUI를 시각화한다.
```

---

## 3. 컴포넌트 책임

## 3.1 Frontend

Frontend는 사용자가 직접 상호작용하는 웹 애플리케이션입니다.

책임:

- 회원가입 및 로그인 화면 제공
- 녹음 파일 업로드 UI 제공
- 업로드된 녹음 목록 표시
- 분석 상태 표시
- 오디오 재생 기능 제공
- Final JSON 기반 시각화
- 전체 요약 표시
- 구간별 요약 표시
- 중요 순간 표시
- 요약 근거 문장 표시
- 특정 timestamp 클릭 시 오디오 위치 이동

Frontend는 AI Service를 직접 호출하지 않습니다.  
모든 요청은 Backend를 통해 처리합니다.

---

## 3.2 Backend

Backend는 클라이언트 요청 처리, 인증, 파일 저장, DB 관리, AI Service 호출을 담당합니다.

책임:

- 사용자 인증
- 세션 또는 토큰 관리
- 오디오 파일 업로드 처리
- 파일 저장 경로 관리
- AI Service 호출
- 처리 상태 관리
- Final JSON 저장
- 사용자별 과거 분석 결과 조회
- Frontend에 API 제공

Backend는 AI 내부 구현에 의존하지 않습니다.  
AI Service의 HTTP API만 호출합니다.

---

## 3.3 AI Service

AI Service는 Python 기반 독립 서비스입니다.

책임:

- 오디오 파일 STT 처리
- STT 결과 정제
- 의미 단위 segment 분할
- 각 segment 요약 생성
- 중요 순간 추출
- 요약 근거 추론
- Final JSON 생성

AI Service는 DB에 직접 접근하지 않는 것을 기본 원칙으로 합니다.  
Final JSON은 Backend에 반환하고, 저장은 Backend가 담당합니다.

---

## 3.4 Database

Database는 사용자 정보, 업로드 파일 정보, 분석 결과를 저장합니다.

저장 대상 예시:

- 사용자 정보
- 업로드된 녹음 파일 metadata
- 분석 상태
- Final JSON
- 업로드 시각
- 파일 경로
- 분석 완료 시각

---

## 4. AI Pipeline Architecture

AI 내부 파이프라인은 다음과 같습니다.

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

---

## 5. AI 모듈별 입출력

## 5.1 STT

입력:

```txt
audio file
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

---

## 5.2 Refine Text

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

---

## 5.3 Segmenting

입력:

```json
[
  {
    "time": 41,
    "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
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
    "important": []
  }
]
```

---

## 5.4 Reasoning

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

---

## 6. Backend 처리 흐름

```txt
POST /api/records
→ audio file 수신
→ 파일 저장
→ record row 생성
→ AI Service 호출
→ Final JSON 수신
→ DB에 Final JSON 저장
→ Frontend에 record_id와 처리 결과 반환
```

초기 개발 단계에서는 동기 처리로 구현할 수 있습니다.

```txt
Frontend 요청
→ Backend 대기
→ AI 처리 완료
→ 결과 반환
```

녹음 파일이 길어져 처리 시간이 길어질 경우, 비동기 job 방식으로 전환하는 것이 좋습니다.

```txt
Frontend 요청
→ Backend가 record_id 반환
→ AI 처리는 background job으로 수행
→ Frontend가 polling 또는 websocket으로 상태 확인
```

---

## 7. 권장 비동기 처리 구조

장기적으로는 다음 구조를 권장합니다.

```txt
Frontend
→ Backend
→ Job Queue
→ AI Worker
→ Backend DB
→ Frontend
```

초기 MVP에서는 Job Queue 없이 Backend가 AI Service를 직접 호출해도 됩니다.

---

## 8. Database 설계 초안

## 8.1 users

```txt
id
email
password_hash
name
created_at
updated_at
```

## 8.2 records

```txt
id
user_id
original_filename
stored_filename
file_path
duration
status
created_at
updated_at
completed_at
```

`status` 값 예시:

```txt
uploaded
processing
completed
failed
```

## 8.3 record_results

```txt
id
record_id
final_json
created_at
updated_at
```

초기에는 `final_json`을 JSON column으로 저장해도 충분합니다.  
검색, 필터링, 통계 기능이 필요해지면 segment 단위 테이블로 정규화할 수 있습니다.

---

## 9. Frontend 시각화 매핑

Final JSON의 주요 필드는 Frontend에서 다음과 같이 사용됩니다.

```txt
sid
→ segment 고유 식별자

start_time, end_time
→ timeline 구간 표시

title
→ 구간 제목

summary
→ 전체 요약 및 구간별 요약 표시

texts
→ 원문 transcript 표시

important
→ 중요한 순간 목록 및 timeline marker 표시

clues
→ 요약 문장과 근거 원문 연결
```

---

## 10. 설계 원칙

1. Frontend는 Backend만 호출한다.
2. Backend는 AI 내부 구현을 알지 않는다.
3. AI Service는 Final JSON만 안정적으로 반환한다.
4. JSON schema는 `shared/schemas`를 기준으로 한다.
5. mock Final JSON만으로 Frontend 개발이 가능해야 한다.
6. AI 단계별 출력은 항상 schema validation을 통과해야 한다.
7. DB 저장은 Backend가 담당한다.
8. AI 모듈은 실험적으로 바뀔 수 있으므로 Backend와 느슨하게 결합한다.
