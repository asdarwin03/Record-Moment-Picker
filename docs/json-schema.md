# JSON Schema Guide

이 문서는 Record Moment Picker에서 사용하는 JSON 데이터 구조를 정의합니다.

RMP의 핵심 계약은 발화 단위 텍스트가 `{ start_time, end_time, text }` 형태를 가진다는 점입니다. 중요한 순간(`important`)은 특정 시점을 가리키므로 `time` 필드를 사용합니다.

---

## 1. 전체 데이터 변환 흐름

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

---

## 2. 공통 규칙

### 2.1 시간 단위

모든 시간 값은 초 단위 number입니다.

```json
{
  "start_time": 41.2,
  "end_time": 46.8
}
```

### 2.2 Transcript Item

STT, 정제 텍스트, segment 내부 `texts`는 다음 필드를 기준으로 합니다.

```json
{
  "t_id": "001",
  "start_time": 41.2,
  "end_time": 46.8,
  "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
}
```

STT와 refined text 단계에서는 `t_id`가 없을 수 있습니다. Segmenting 이후부터는 `t_id`가 필요합니다.

### 2.3 ID 규칙

`sid`는 segment 고유 ID입니다.

```txt
segment_01
segment_02
segment_03
```

`t_id`는 transcript item 고유 ID이며 전체 녹음 기준으로 고유해야 합니다. Segment마다 다시 `001`부터 시작하지 않습니다.

### 2.4 빈 값 처리

AI가 특정 값을 생성하지 못한 경우 `null`보다 빈 배열 또는 빈 문자열을 사용합니다.

```json
{
  "important": [],
  "summary": []
}
```

---

## 3. STT Output

STT 모듈의 출력입니다. 각 발화는 시작/종료 시각과 텍스트를 가집니다.

Schema:

```txt
shared/schemas/stt-output.schema.json
```

Example:

```json
[
  {
    "start_time": 41.2,
    "end_time": 46.8,
    "text": "안냥하세요, RecordMomentPicker 발표를 시작하겠습니다."
  },
  {
    "start_time": 57.0,
    "end_time": 63.5,
    "text": "이 프로젝트는 생강보다 데이터 구조가 복잣합니다."
  }
]
```

| Field | Type | Required | Description |
|---|---:|---:|---|
| `start_time` | number | yes | 발화 시작 시간 |
| `end_time` | number | yes | 발화 종료 시간 |
| `text` | string | yes | STT 결과 텍스트 |

주의사항:

- STT 결과에는 오타가 포함될 수 있습니다.
- `end_time`은 플레이어 총 길이나 다음 발화 시작 시간이 아니라 해당 발화의 종료 시각이어야 합니다.
- timestamp는 이후 GUI 이동 기능에 사용되므로 최대한 보존해야 합니다.

---

## 4. Refined Text

Refine Text 모듈의 출력입니다. STT 결과에서 오타, 비문, 잘못 인식된 단어를 수정합니다.

Schema:

```txt
shared/schemas/refined-text.schema.json
```

Example:

```json
[
  {
    "start_time": 41.2,
    "end_time": 46.8,
    "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
  },
  {
    "start_time": 57.0,
    "end_time": 63.5,
    "text": "이 프로젝트는 생각보다 데이터 구조가 복잡합니다."
  }
]
```

| Field | Type | Required | Description |
|---|---:|---:|---|
| `start_time` | number | yes | 발화 시작 시간 |
| `end_time` | number | yes | 발화 종료 시간 |
| `text` | string | yes | 정제된 텍스트 |

주의사항:

- `start_time`, `end_time`은 STT Output의 값을 그대로 유지합니다.
- 발화 순서를 바꾸지 않습니다.
- 문장을 요약하지 않습니다.
- 의미를 임의로 추가하지 않습니다.

---

## 5. Structured Segments

Segmenting 모듈의 출력입니다. 정제된 transcript를 의미 있는 구간으로 나눈 결과입니다.

Schema:

```txt
shared/schemas/structured-segments.schema.json
```

Example:

```json
[
  {
    "sid": "segment_01",
    "start_time": 41.2,
    "end_time": 63.5,
    "title": "프로젝트 설명 시작",
    "summary": [
      "Record Moment Picker 발표가 시작됨",
      "프로젝트의 데이터 구조가 생각보다 복잡하다는 점을 언급함"
    ],
    "texts": [
      {
        "t_id": "001",
        "start_time": 41.2,
        "end_time": 46.8,
        "text": "안녕하세요, RecordMomentPicker 발표를 시작하겠습니다."
      },
      {
        "t_id": "002",
        "start_time": 57.0,
        "end_time": 63.5,
        "text": "이 프로젝트는 생각보다 데이터 구조가 복잡합니다."
      }
    ],
    "important": [
      {
        "time": 57.0,
        "title": "복잡한 데이터 구조"
      }
    ]
  }
]
```

| Field | Type | Required | Description |
|---|---:|---:|---|
| `sid` | string | yes | segment 고유 ID |
| `start_time` | number | yes | segment 시작 시간 |
| `end_time` | number | yes | segment 종료 시간 |
| `title` | string | yes | segment 제목 |
| `summary` | string[] | yes | segment 핵심 요약 리스트 |
| `texts` | object[] | yes | segment에 포함된 transcript item |
| `important` | object[] | yes | 중요한 순간 리스트 |

`texts`의 `end_time`은 해당 발화의 종료 시각입니다. Segment의 `end_time`은 기본적으로 포함된 마지막 발화의 `end_time`을 기준으로 합니다.

`important`는 특정 순간을 가리키므로 다음 구조를 사용합니다.

```json
{
  "time": 57.0,
  "title": "복잡한 데이터 구조"
}
```

---

## 6. Final Result

Reasoning 모듈의 출력이자 Backend와 Frontend가 사용하는 최종 결과입니다. Structured Segments에 `clues` 필드가 추가됩니다.

Schema:

```txt
shared/schemas/final-result.schema.json
```

Example:

```json
[
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
```

### `clues`

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

## 7. Frontend 매핑 규칙

| JSON Field | GUI 역할 |
|---|---|
| `sid` | segment key |
| `start_time` | timeline segment 시작 위치 |
| `end_time` | timeline segment 종료 위치 |
| `title` | 구간 제목 |
| `summary` | 전체 요약 및 구간별 요약 |
| `texts` | transcript view |
| `texts[].start_time` | transcript 클릭 시 재생 이동 시각 |
| `texts[].end_time` | 발화/구간 종료 기준 계산 |
| `important` | 중요 순간 marker |
| `clues` | 요약 근거 표시 |

---

## 8. Validation 권장 방식

AI Service는 각 단계가 끝날 때 schema validation을 수행합니다.

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

---

## 9. 자주 발생할 수 있는 문제

### 9.1 transcript item에 `time`만 있는 경우

잘못된 예:

```json
{
  "time": 41,
  "text": "본문"
}
```

해결:

- transcript item은 `{ start_time, end_time, text }`를 사용합니다.
- legacy 데이터는 Frontend에서 임시 정규화할 수 있지만, AI/Backend의 기준 출력은 start/end 구조여야 합니다.

### 9.2 `clue`에 존재하지 않는 `t_id`가 들어가는 경우

해결:

- `clue`에는 같은 segment의 `texts` 안에 존재하는 `t_id`만 넣습니다.

### 9.3 segment 시간이 역전되는 경우

잘못된 예:

```json
{
  "start_time": 100,
  "end_time": 80
}
```

해결:

- `end_time`은 항상 `start_time`보다 크거나 같아야 합니다.

### 9.4 같은 발화가 segment 안에 중복 포함되는 경우

해결:

- 같은 `t_id` 또는 같은 `(start_time, text)` 조합이 중복되지 않도록 정규화합니다.

---

## 10. 최종 체크리스트

```txt
[ ] 전체 결과는 array인가?
[ ] 모든 segment에 sid가 있는가?
[ ] sid 형식은 segment_01 형태인가?
[ ] segment start_time, end_time은 number인가?
[ ] title은 빈 문자열이 아닌가?
[ ] summary는 array인가?
[ ] texts는 array인가?
[ ] 모든 text item에 t_id, start_time, end_time, text가 있는가?
[ ] important는 array인가?
[ ] important item은 time, title을 가지는가?
[ ] Final Result에는 clues가 있는가?
[ ] summary_index는 0부터 시작하는 유효한 index인가?
[ ] clue에 들어간 t_id가 실제 texts 안에 존재하는가?
```
