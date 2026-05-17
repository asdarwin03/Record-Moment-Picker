# Frontend

Record Moment Picker의 React + TypeScript + Vite 클라이언트입니다.

Frontend는 AI Service를 직접 호출하지 않고 Backend API만 호출합니다.

---

## 실행 방법

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Vite가 출력하는 주소로 접속합니다. 일반적으로 다음 주소입니다.

```txt
http://localhost:5173
```

Backend는 `http://localhost:3000`, AI Service는 `http://localhost:8000`에서 먼저 실행되어 있어야 합니다.

---

## 환경 변수

루트 `.env` 또는 Frontend 환경에서 Backend 주소를 지정합니다.

```env
VITE_BACKEND_API_URL=http://localhost:3000
```

---

## API 흐름

```txt
1. GET /api/bootstrap
   → 폴더와 녹음 목록 로드

2. POST /api/records
   → 파일 업로드
   → Backend가 record_id와 processing 상태를 즉시 반환

3. GET /api/records/:id/status
   → 업로드 후 주기적으로 polling

4. GET /api/records/:id
   → completed 이후 Final JSON 조회
```

---

## 데이터 기준

화면에 표시되는 분석 결과는 Final JSON을 기준으로 합니다.

Transcript item은 다음 구조를 사용합니다.

```json
{
  "t_id": "001",
  "start_time": 0.0,
  "end_time": 4.2,
  "text": "첫 번째 발화입니다."
}
```

Frontend의 표준 분석 입력은 `start_time/end_time`입니다.

사용 위치:

- `start_time`: transcript 클릭 시 오디오 이동, segment 시작 표시
- `end_time`: 발화 종료, segment 종료, 전체 분석 길이 계산
- `important[].time`: 중요한 순간 marker
