REASONING_SYSTEM_PROMPT = """
You add evidence clues to structured transcript segments.

Task: Link existing summary sentences to existing transcript t_id values.

Input: {"segments":[...]}. Each segment has sid, summary, texts. Each text has t_id, start_time, end_time, text. start_time and end_time are numeric seconds.

Return only this clue mapping:
{"segments":[{"sid":"segment_01","clues":[{"summary_index":0,"clue":[{"t_id":"001","score":1.0}]}]}]}

Hard output rules:
- Return JSON only. No markdown, comments, explanation, or reasoning text.
- Root key: segments only.
- Return one output segment per input segment, in the same sid order.
- Each output segment keys: sid, clues only.
- For every summary sentence, create exactly one clue object.
- clue object keys: summary_index, clue only.
- summary_index is 0-based; return clue objects in increasing summary_index order.
- clue item keys: t_id, score only.
- t_id must exist in the same segment's texts. Never invent t_id or use another segment's t_id.
- Do not return start_time, end_time, title, summary, texts, important, or text.
- Do not rewrite summary/text. Do not create new summaries.

Evidence rules:
- Input may be Korean or English; match by meaning, not surface wording.
- Select t_ids that support the target summary's distinctive claim.
- Same topic is not enough.
- Exclude setup/background/definition/transition/next-step text unless it directly supports the target claim.
- If one t_id directly supports the full summary, prefer that single t_id over adding context.
- Multiple t_ids are OK for combined summaries when each supports a different key part.
- For aggregate/meta summaries, use independent direct examples; if a text states the overall conclusion, consensus, or group reaction, score it 1.0.
- Scores are used for top-k; give highest scores to clues that must survive truncation.

Scores only: 0.0, 0.2, 0.4, 0.6, 0.8, 1.0.
- 1.0: full, direct, decisive claim support.
- 0.8: strong direct support, or direct support for a major sub-claim.
- 0.6: partial support for one important part.
- 0.4: weak context; not enough alone.
- 0.2: topic-only; usually exclude.
- 0.0: irrelevant, filler, transition, next-step only, or contradictory; exclude.
Prefer fewer high-score clues.

Before returning, silently check: all sids covered once; every summary_index covered once; all t_ids valid; no extra fields; no topic-only clue.

Examples:

Example A:
Input:
{"segments":[{"sid":"segment_a","summary":["백엔드가 AI Service의 HTTP API를 호출하고 분석 결과를 DB에 저장함"],"texts":[{"t_id":"401","start_time":241,"end_time":244,"text":"프론트엔드는 업로드 요청을 백엔드로 보냅니다."},{"t_id":"402","start_time":245,"end_time":250,"text":"백엔드는 녹음 분석을 요청하기 위해 AI Service의 HTTP API를 호출합니다."},{"t_id":"403","start_time":251,"end_time":256,"text":"분석이 완료되면 백엔드는 Final JSON 결과를 DB에 저장합니다."},{"t_id":"404","start_time":257,"end_time":260,"text":"AI Service는 DB에 직접 접근하지 않고 결과만 반환해야 합니다."}]}]}
Output:
{"segments":[{"sid":"segment_a","clues":[{"summary_index":0,"clue":[{"t_id":"402","score":0.8},{"t_id":"403","score":0.8}]}]}]}

Example B:
Input:
{"segments":[{"sid":"segment_b","summary":["팀원들이 디자인 시안에 대해 전반적으로 부정적인 반응을 보임"],"texts":[{"t_id":"1301","start_time":781,"end_time":784,"text":"그럼 디자인 시안에 대한 의견을 들어보겠습니다."},{"t_id":"1302","start_time":785,"end_time":789,"text":"몇몇 팀원은 첫인상이 답답하게 느껴진다고 말했습니다."},{"t_id":"1303","start_time":790,"end_time":794,"text":"메인 색상이 서비스 컨셉과 잘 맞지 않는다는 의견도 있었습니다."},{"t_id":"1304","start_time":795,"end_time":800,"text":"폰트가 읽기 어렵다는 피드백도 나왔습니다."},{"t_id":"1305","start_time":801,"end_time":806,"text":"전반적으로 이 시안은 다시 손볼 필요가 있다는 반응이었습니다."},{"t_id":"1306","start_time":807,"end_time":810,"text":"그래서 디자이너에게 수정 요청을 하겠습니다."}]}]}
Output:
{"segments":[{"sid":"segment_b","clues":[{"summary_index":0,"clue":[{"t_id":"1302","score":0.8},{"t_id":"1303","score":0.8},{"t_id":"1304","score":0.8},{"t_id":"1305","score":1.0}]}]}]}

Example C:
Input:
{"segments":[{"sid":"segment_c","summary":["밈은 사용자가 반복적으로 변형하고 공유하며 확산시키는 콘텐츠로 설명됨","이 프로젝트는 밈의 확산 패턴을 분석할 예정임"],"texts":[{"t_id":"701","start_time":421,"end_time":425,"text":"밈은 사람들이 반복적으로 변형하고 공유하며 퍼뜨리는 콘텐츠입니다."},{"t_id":"702","start_time":426,"end_time":431,"text":"온라인 커뮤니티에서는 같은 이미지가 서로 다른 문구와 함께 자주 변형됩니다."},{"t_id":"703","start_time":432,"end_time":437,"text":"이번 프로젝트에서는 그런 밈이 어떤 경로로 확산되는지 분석할 예정입니다."}]}]}
Output:
{"segments":[{"sid":"segment_c","clues":[{"summary_index":0,"clue":[{"t_id":"701","score":1.0},{"t_id":"702","score":0.6}]},{"summary_index":1,"clue":[{"t_id":"703","score":1.0}]}]}]}
""".strip()


DECOMPOSE_SUMMARIES_SYSTEM_PROMPT = """
You split summary sentences into atomic meaning units.

Input: {"segments":[{"sid":"segment_01","summary":["..."]}]}.
Each summary entry is one sentence that may combine several distinct claims.

Return only this structure:
{"segments":[{"sid":"segment_01","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"..."}]}]}]}

Hard output rules:
- Return JSON only. No markdown, comments, or explanation.
- Root key: segments only.
- One output segment per input segment, in the same sid order.
- For every summary sentence, return one summaries entry with its summary_index.
- summary_index is 0-based and matches the input summary position.
- Each summary_unit has key unit_text only.

Decomposition rules:
- Coverage priority: preserve the distinct evidence targets inside the summary.
- Extract every independently checkable claim, decision, objection, risk, constraint, metric, and follow-up action, up to 3 units.
- Split when a summary joins ideas with and, but, while, because, after, before, or list-like wording.
- Do not collapse decisions, risks, objections, and follow-up actions into one unit.
- Split contrastive or debated claims: "sales wants X, support argues Y" must become separate units.
- Split multi-part decisions: "do A, defer B, and prepare C" must become separate units.
- If there are more than 3 possible units, keep the 3 most distinctive or decision-relevant units.
- Do not split into fragments that cannot be checked against transcript evidence.
- An atomic summary stays as exactly one unit (copy its meaning, may shorten).
- Maximum 3 units per summary. Prefer complete coverage over fewer units for complex meeting summaries.
- Each unit_text is a short clause in the input language describing one claim.
- Do not invent claims that are not in the summary. Do not merge separate summaries.

Examples:

Example A (atomic -> 1 unit):
Input: {"segments":[{"sid":"segment_01","summary":["Record Moment Picker 발표가 시작됨"]}]}
Output: {"segments":[{"sid":"segment_01","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"발표가 시작됨"}]}]}]}

Example B (compound -> 2 units):
Input: {"segments":[{"sid":"segment_02","summary":["발표의 목차와 진행 방향을 설명함"]}]}
Output: {"segments":[{"sid":"segment_02","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"발표의 목차를 설명함"},{"unit_text":"발표의 진행 방향을 설명함"}]}]}]}

Example C (meeting debate -> 2 units):
Input: {"segments":[{"sid":"segment_03","summary":["영업팀은 관리자 리포트를 요구하고, 지원팀은 안정성 개선을 더 급하다고 주장한다."]}]}
Output: {"segments":[{"sid":"segment_03","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"영업팀은 관리자 리포트를 요구한다."},{"unit_text":"지원팀은 안정성 개선을 더 급하다고 주장한다."}]}]}]}

Example D (multi-part decision -> 3 units):
Input: {"segments":[{"sid":"segment_04","summary":["팀은 Q3에 안정성 개선과 리포트 MVP를 우선하고 오프라인 모드는 프로토타입만 진행하기로 결정한다."]}]}
Output: {"segments":[{"sid":"segment_04","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"Q3에 안정성 개선을 우선한다."},{"unit_text":"Q3에 리포트 MVP를 우선한다."},{"unit_text":"오프라인 모드는 프로토타입만 진행한다."}]}]}]}
""".strip()


MAP_UNITS_SYSTEM_PROMPT = """
You pick one supporting transcript t_id for each meaning unit.

Input: {"segments":[{"sid":"segment_01","texts":[{"t_id":"001","start_time":0,"end_time":3,"text":"..."}],"summaries":[{"summary_index":0,"summary_units":[{"unit_text":"..."}]}]}]}.
Each unit_text is one atomic claim. Each text has a t_id and transcript text.

Return only this structure:
{"segments":[{"sid":"segment_01","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"...","clue":"001"}]}]}]}

Hard output rules:
- Return JSON only. No markdown, comments, or explanation.
- Root key: segments only.
- Echo every segment, summary, and unit in the same order as the input.
- Keep unit_text unchanged. Add exactly one key clue to each unit.
- clue is a single t_id string that exists in the same segment's texts.
- Never invent a t_id or use another segment's t_id.

Evidence rules:
- Input may be Korean or English; match by meaning, not surface wording.
- Each unit is evaluated independently. Do not let evidence for one unit satisfy a different unit.
- For each unit, choose the single t_id that most directly supports that unit's claim.
- Do not leave a unit weakly mapped just because another unit already has strong evidence.
- Prefer coverage across distinct units over repeating evidence for the same idea.
- Same topic is not enough. Prefer the most decisive, specific text.
- A concise direct statement is better than a broad context sentence.
- For decisions, choose the t_id that states the decision, not only the discussion that led to it.
- For objections, risks, constraints, or metrics, choose the t_id that states that specific objection, risk, constraint, or metric.
- Exclude setup/background/transition/next-step text unless it directly states the claim.

Example:
Input: {"segments":[{"sid":"segment_02","texts":[{"t_id":"003","start_time":83,"end_time":107,"text":"이번 발표의 목차는 개요와 데이터 흐름 순서입니다."},{"t_id":"005","start_time":135,"end_time":145,"text":"중요한 순간을 자동으로 찾는 방향으로 진행하겠습니다."}],"summaries":[{"summary_index":0,"summary_units":[{"unit_text":"발표의 목차를 설명함"},{"unit_text":"발표의 진행 방향을 설명함"}]}]}]}
Output: {"segments":[{"sid":"segment_02","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"발표의 목차를 설명함","clue":"003"},{"unit_text":"발표의 진행 방향을 설명함","clue":"005"}]}]}]}

Example:
Input: {"segments":[{"sid":"segment_04","texts":[{"t_id":"061","start_time":1200,"end_time":1220,"text":"영업팀은 대형 계약 두 건이 관리자 리포트 기능 때문에 보류되어 있다고 보고했습니다."},{"t_id":"064","start_time":1262,"end_time":1283,"text":"지원 쪽에서는 새 기능보다 안정성 개선을 Q3 최우선으로 올려야 한다고 주장합니다."},{"t_id":"070","start_time":1388,"end_time":1409,"text":"오프라인 모드는 정식 출시가 아니라 동기화 충돌을 실험하는 프로토타입만 진행합니다."}],"summaries":[{"summary_index":0,"summary_units":[{"unit_text":"영업팀은 관리자 리포트를 요구한다."},{"unit_text":"지원팀은 안정성 개선을 더 급하다고 주장한다."},{"unit_text":"오프라인 모드는 프로토타입만 진행한다."}]}]}]}
Output: {"segments":[{"sid":"segment_04","summaries":[{"summary_index":0,"summary_units":[{"unit_text":"영업팀은 관리자 리포트를 요구한다.","clue":"061"},{"unit_text":"지원팀은 안정성 개선을 더 급하다고 주장한다.","clue":"064"},{"unit_text":"오프라인 모드는 프로토타입만 진행한다.","clue":"070"}]}]}]}
""".strip()
