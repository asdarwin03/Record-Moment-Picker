# Pipeline Settings Design

## Goal

녹음 업로드 전에 STT, Refine, Segmenting, Reasoning 모델과 고급 설정을 사용자가 선택하고, 선택값을 레코드에 저장해 최초 처리와 재시도에 동일하게 적용한다.

## Architecture

- `.env`는 기본값과 드롭다운 허용 목록을 제공한다.
- Frontend는 Backend의 `GET /api/records/processing-options`에서 선택지와 기본값을 조회한다.
- 업로드 multipart에는 `file`과 `pipelineSettings` JSON을 함께 전송한다.
- Backend는 설정을 검증하고 `pipeline_settings`로 레코드에 저장한다.
- Backend는 AI 서버의 `/process-audio`에 같은 설정을 전달한다.
- AI 서버는 설정을 독립적으로 재검증하고 요청별 client/options를 생성한다.
- 전역 환경변수나 전역 settings 객체는 요청 중 변경하지 않는다.

## UI

- 기존 추가 버튼은 `녹음 추가` modal을 연다.
- Modal 상단에서 오디오 파일을 선택한다.
- STT, Refine, Segmenting, Reasoning 네 단계가 가로 패널로 표시된다.
- 각 패널은 모델 드롭다운과 고급 설정 토글을 제공한다.
- 모바일에서는 단계 패널이 세로로 배치된다.
- 추가 버튼은 파일과 모든 설정이 유효할 때만 활성화한다.

## Runtime Settings

- STT: provider, model, device, compute type, chunking enabled, chunk seconds, overlap seconds, minimum duration
- Refine: model, temperature, max output tokens
- Segmenting: model, temperature, chunk seconds, max output tokens, merge max output tokens
- Reasoning: model, temperature, max output tokens

## AI Module Changes

핵심 알고리즘과 prompt/schema는 유지한다. 다음 서비스 진입점에만 선택적 인자를 추가한다.

- `transcribe_audio`: STT runtime options
- `refine_text`: 요청별 LLM client
- `segment_text`: 요청별 LLM client와 chunk/token options
- `add_reasoning`: 요청별 LLM client와 token options

## Validation

- 모델과 provider는 서버 allowlist에 포함된 값만 허용한다.
- 숫자 설정은 서버에서 최소/최대 범위를 검증한다.
- Backend와 AI 서버가 각각 검증한다.
- 기존 레코드에 설정이 없으면 현재 env 기본값을 적용한다.
