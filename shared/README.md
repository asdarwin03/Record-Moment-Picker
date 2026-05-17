# Shared JSON Contracts

이 폴더는 Record Moment Picker 프로젝트에서 frontend, backend, AI가 공통으로 사용하는 JSON 데이터 포맷을 정의합니다.

---

## 데이터 흐름

```txt
Audio File
→ STT
→ Text with start_time/end_time
→ Refine Text
→ Refined text with start_time/end_time
→ Segmenting important parts
→ Structured JSON
→ Reasoning of segmenting results
→ Final JSON
→ Backend 저장
→ Frontend GUI 시각화
```

---

## 폴더 설명

- `examples/`: 각 단계별 예시 JSON 데이터
- `schemas/`: 각 단계별 JSON Schema 정의

---

## 개발 원칙

1. AI 모듈은 내부 구현을 자유롭게 바꿀 수 있습니다.
2. 단, 각 단계의 입력과 출력은 이 폴더에 정의된 JSON 포맷을 따라야 합니다.
3. Frontend는 `final-result.example.json`을 mock data로 사용해 GUI를 먼저 개발할 수 있습니다.
4. Backend는 AI 서버에서 받은 Final JSON을 저장하고 Frontend에 전달합니다.
5. JSON 필드명은 `snake_case`를 기본으로 합니다.
6. transcript item은 `{ start_time, end_time, text }`를 기준으로 합니다.

---

## 주요 데이터 타입

### Text with start/end timestamp

STT 결과물입니다.

```json
[
  {
    "start_time": 0.0,
    "end_time": 4.2,
    "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

### Refined text with start/end timestamp

STT 결과의 오타, 비문, 인식 오류를 수정한 결과물입니다. 시간 값은 유지합니다.

```json
[
  {
    "start_time": 0.0,
    "end_time": 4.2,
    "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
  }
]
```

### Structured JSON

녹음 내용을 의미 있는 구간으로 나눈 결과물입니다.

```json
[
  {
    "sid": "segment_01",
    "start_time": 0.0,
    "end_time": 15.4,
    "title": "프로젝트 설명 시작",
    "summary": ["RMP 프로젝트의 데이터 구조가 생각보다 복잡함"],
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

### Final JSON

Structured JSON에 reasoning 결과인 `clues`가 추가된 최종 결과물입니다.

```json
[
  {
    "sid": "segment_01",
    "start_time": 0.0,
    "end_time": 15.4,
    "title": "프로젝트 설명 시작",
    "summary": ["RMP 프로젝트의 데이터 구조가 생각보다 복잡함"],
    "texts": [],
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

Frontend GUI는 Final JSON을 기준으로 전체 요약, 구간별 요약, 타임라인, 중요 순간, 근거 문장을 표시합니다.
