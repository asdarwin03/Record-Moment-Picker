# JSON Schema Guide

이 문서는 Record Moment Picker에서 사용하는 JSON 데이터 구조를 정의합니다.

프로젝트의 핵심은 AI 단계별 입출력 JSON을 안정적으로 유지하는 것입니다.  
각 모듈은 내부 구현을 자유롭게 할 수 있지만, 모듈 밖으로 나가는 데이터는 반드시 이 문서의 포맷을 따라야 합니다.

---

## 1. 전체 데이터 변환 흐름

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

## 2. 공통 규칙

## 2.1 시간 단위

모든 시간 값은 초 단위 number로 저장합니다.

예시:

```json
{
  "time": 83
}
```

83초는 1분 23초를 의미합니다.

---

## 2.2 필드명 스타일

모든 JSON 필드명은 `snake_case`를 사용합니다.

올바른 예:

```json
{
  "start_time": 41,
  "end_time": 81
}
```

잘못된 예:

```json
{
  "startTime": 41,
  "endTime": 81
}
```

---

## 2.3 ID 규칙

### `sid`

segment ID입니다.

형식:

```txt
segment_01
segment_02
segment_03
```

### `t_id`

transcript item ID입니다.

형식:

```txt
001
002
003
```

`t_id`는 전체 녹음 기준으로 고유해야 합니다.  
segment마다 다시 001부터 시작하지 않습니다.

---

## 2.4 빈 값 처리

AI가 특정 값을 생성하지 못한 경우 `null`보다 빈 배열 또는 빈 문자열을 사용합니다.

권장:

```json
{
  "important": [],
  "summary": []
}
```

비권장:

```json
{
  "important": null,
  "summary": null
}
```

---

## 3. STT Output

STT 모듈의 출력입니다.

## 3.1 의미

녹음 파일을 음성 인식한 결과입니다.  
각 발화는 timestamp와 text를 가집니다.

## 3.2 Schema

파일 위치:

```txt
shared/schemas/stt-output.schema.json
```

## 3.3 Example

```json
[
  {
    "time": 41,
    "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
  },
  {
    "time": 57,
    "text": "이 프로젝트는 생강보다 데이터 구조가 복잣합니다."
  }
]
```

## 3.4 필드 설명

| Field | Type | Required | Description |
|---|---:|---:|---|
| `time` | number | yes | 발화 시작 시간, 초 단위 |
| `text` | string | yes | STT 결과 텍스트 |

## 3.5 주의사항

- STT 결과에는 오타가 포함될 수 있습니다.
- STT 단계에서는 텍스트를 과도하게 정제하지 않아도 됩니다.
- timestamp는 이후 GUI 이동 기능에 사용되므로 최대한 보존해야 합니다.

---

## 4. Refined Text

Refine Text 모듈의 출력입니다.

## 4.1 의미

STT 결과에서 오타, 비문, 잘못 인식된 단어를 수정한 결과입니다.

## 4.2 Schema

파일 위치:

```txt
shared/schemas/refined-text.schema.json
```

## 4.3 Example

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

## 4.4 필드 설명

| Field | Type | Required | Description |
|---|---:|---:|---|
| `time` | number | yes | 발화 시작 시간, 초 단위 |
| `text` | string | yes | 정제된 텍스트 |

## 4.5 주의사항

- `time`은 STT Output의 값을 그대로 유지합니다.
- 발화 순서를 바꾸지 않습니다.
- 문장을 요약하지 않습니다.
- 의미를 임의로 추가하지 않습니다.
- 오타와 인식 오류를 수정하는 데 집중합니다.

---

## 5. Structured Segments

Segmenting 모듈의 출력입니다.

## 5.1 의미

정제된 transcript를 의미 있는 구간으로 나눈 결과입니다.

## 5.2 Schema

파일 위치:

```txt
shared/schemas/structured-segments.schema.json
```

## 5.3 Example

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

## 5.4 필드 설명

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sid` | string | yes | segment 고유 ID |
| `start_time` | number | yes | segment 시작 시간 |
| `end_time` | number | yes | segment 종료 시간 |
| `title` | string | yes | segment 제목 |
| `summary` | string[] | yes | segment 핵심 요약 리스트 |
| `texts` | object[] | yes | segment에 포함된 transcript item |
| `important` | object[] | yes | 중요한 순간 리스트 |

---

## 5.5 `texts` 필드

```json
{
  "t_id": "001",
  "time": 41,
  "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
}
```

| Field | Type | Required | Description |
|---|---:|---:|---|
| `t_id` | string | yes | transcript item 고유 ID |
| `time` | number | yes | 발화 시작 시간 |
| `text` | string | yes | 발화 텍스트 |

---

## 5.6 `important` 필드

```json
{
  "time": 57,
  "title": "복잡한 데이터 구조"
}
```

| Field | Type | Required | Description |
|---|---:|---:|---|
| `time` | number | yes | 중요한 순간의 timestamp |
| `title` | string | yes | 중요한 순간의 짧은 제목 |

---

## 5.7 주의사항

- segment는 시간 순서대로 정렬합니다.
- segment 간 시간 범위가 불필요하게 겹치지 않게 합니다.
- 하나의 `t_id`가 여러 segment에 중복 포함되지 않는 것을 기본 원칙으로 합니다.
- `summary`는 너무 길지 않게 핵심 문장 위주로 작성합니다.
- `important`는 사용자가 다시 들어볼 가치가 있는 순간을 나타냅니다.

---

## 6. Final Result

Reasoning 모듈의 출력이자 Backend와 Frontend가 사용하는 최종 결과입니다.

## 6.1 의미

Structured Segments에 `clues` 필드가 추가된 최종 JSON입니다.  
`clues`는 각 요약 문장이 어떤 원문 발화를 근거로 생성되었는지 나타냅니다.

## 6.2 Schema

파일 위치:

```txt
shared/schemas/final-result.schema.json
```

## 6.3 Example

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
    ],
    "clues": [
      {
        "summary_index": 0,
        "clue": ["001"]
      },
      {
        "summary_index": 1,
        "clue": ["002"]
      }
    ]
  }
]
```

## 6.4 추가 필드 설명

| Field | Type | Required | Description |
|---|---:|---:|---|
| `clues` | object[] | yes | 요약 문장과 근거 원문 간의 연결 정보 |

---

## 6.5 `clues` 필드

```json
{
  "summary_index": 0,
  "clue": ["001", "002"]
}
```

| Field | Type | Required | Description |
|---|---:|---:|---|
| `summary_index` | integer | yes | `summary` 배열에서 해당 요약 문장의 index |
| `clue` | string[] | yes | 해당 요약의 근거가 되는 `t_id` 목록 |

---

## 6.6 `summary_index` 규칙

`summary_index`는 0부터 시작합니다.

예시:

```json
{
  "summary": [
    "첫 번째 요약",
    "두 번째 요약"
  ],
  "clues": [
    {
      "summary_index": 0,
      "clue": ["001"]
    },
    {
      "summary_index": 1,
      "clue": ["002"]
    }
  ]
}
```

---

## 7. Frontend 매핑 규칙

Frontend는 Final Result를 다음과 같이 사용합니다.

| JSON Field | GUI 역할 |
|---|---|
| `sid` | segment key |
| `start_time` | timeline segment 시작 위치 |
| `end_time` | timeline segment 종료 위치 |
| `title` | 구간 제목 |
| `summary` | 전체 요약 및 구간별 요약 |
| `texts` | transcript view |
| `important` | 중요 순간 marker |
| `clues` | 요약 근거 표시 |

---

## 8. Validation 권장 방식

AI Service는 각 단계가 끝날 때 schema validation을 수행하는 것을 권장합니다.

예시 흐름:

```txt
STT output 생성
→ stt-output.schema.json으로 validation

Refined text 생성
→ refined-text.schema.json으로 validation

Structured segments 생성
→ structured-segments.schema.json으로 validation

Final result 생성
→ final-result.schema.json으로 validation
```

Python에서는 `jsonschema` 또는 Pydantic을 사용할 수 있습니다.  
Node.js에서는 `ajv`를 사용할 수 있습니다.

---

## 9. 자주 발생할 수 있는 문제

## 9.1 `summary_index`가 summary 배열 범위를 벗어나는 경우

잘못된 예:

```json
{
  "summary": ["요약 1"],
  "clues": [
    {
      "summary_index": 2,
      "clue": ["001"]
    }
  ]
}
```

해결:

- `summary_index`는 반드시 `0 <= summary_index < summary.length`를 만족해야 합니다.

---

## 9.2 `clue`에 존재하지 않는 `t_id`가 들어가는 경우

잘못된 예:

```json
{
  "texts": [
    {
      "t_id": "001",
      "time": 41,
      "text": "본문"
    }
  ],
  "clues": [
    {
      "summary_index": 0,
      "clue": ["999"]
    }
  ]
}
```

해결:

- `clue`에는 같은 segment의 `texts` 안에 존재하는 `t_id`만 넣습니다.

---

## 9.3 segment 시간이 역전되는 경우

잘못된 예:

```json
{
  "start_time": 100,
  "end_time": 80
}
```

해결:

- `end_time`은 항상 `start_time`보다 크거나 같아야 합니다.

---

## 10. 최종 체크리스트

AI 결과를 반환하기 전에 다음을 확인합니다.

```txt
[ ] 전체 결과는 array인가?
[ ] 모든 segment에 sid가 있는가?
[ ] sid 형식은 segment_01 형태인가?
[ ] start_time, end_time은 number인가?
[ ] title은 빈 문자열이 아닌가?
[ ] summary는 array인가?
[ ] texts는 array인가?
[ ] 모든 text item에 t_id, time, text가 있는가?
[ ] important는 array인가?
[ ] Final Result에는 clues가 있는가?
[ ] summary_index는 0부터 시작하는 유효한 index인가?
[ ] clue에 들어간 t_id가 실제 texts 안에 존재하는가?
```
