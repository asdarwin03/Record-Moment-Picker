REASONING_SYSTEM_PROMPT = """
You add evidence clues to structured transcript segments.

Task: Link existing summary sentences to existing transcript t_id values.

Input: {"segments":[...]}. Each segment has sid, summary, texts. Each text has t_id, time, text. time is numeric seconds.

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
- Do not return start_time, end_time, title, summary, texts, important, time, or text.
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
{"segments":[{"sid":"segment_a","summary":["Backend calls AI Service via HTTP API and stores the analysis result in DB"],"texts":[{"t_id":"401","time":241,"text":"Frontend sends the upload request to Backend."},{"t_id":"402","time":245,"text":"Backend calls AI Service's HTTP API to request recording analysis."},{"t_id":"403","time":251,"text":"After analysis is complete, Backend stores the Final JSON result in DB."},{"t_id":"404","time":257,"text":"AI Service should not access DB directly; it only returns the result."}]}]}
Output:
{"segments":[{"sid":"segment_a","clues":[{"summary_index":0,"clue":[{"t_id":"402","score":0.8},{"t_id":"403","score":0.8}]}]}]}

Example B:
Input:
{"segments":[{"sid":"segment_b","summary":["Team members showed an overall negative reaction to the design draft"],"texts":[{"t_id":"1301","time":781,"text":"Let's hear opinions about the design draft."},{"t_id":"1302","time":785,"text":"Some said the first impression felt cramped."},{"t_id":"1303","time":790,"text":"Some said the main color does not match the service concept."},{"t_id":"1304","time":795,"text":"There was also feedback that the font is hard to read."},{"t_id":"1305","time":801,"text":"Overall, the reaction was that the draft needs to be reworked."},{"t_id":"1306","time":807,"text":"So we will ask the designer for revisions."}]}]}
Output:
{"segments":[{"sid":"segment_b","clues":[{"summary_index":0,"clue":[{"t_id":"1302","score":0.8},{"t_id":"1303","score":0.8},{"t_id":"1304","score":0.8},{"t_id":"1305","score":1.0}]}]}]}

Example C:
Input:
{"segments":[{"sid":"segment_c","summary":["A meme is explained as content that users repeatedly modify and spread","This project will analyze meme diffusion patterns"],"texts":[{"t_id":"701","time":421,"text":"A meme is content that people repeatedly modify, share, and spread."},{"t_id":"702","time":426,"text":"In online communities, the same image is often changed with different captions."},{"t_id":"703","time":432,"text":"In this project, we will analyze how such memes spread through different paths."}]}]}
Output:
{"segments":[{"sid":"segment_c","clues":[{"summary_index":0,"clue":[{"t_id":"701","score":1.0},{"t_id":"702","score":0.6}]},{"summary_index":1,"clue":[{"t_id":"703","score":1.0}]}]}]}
""".strip()