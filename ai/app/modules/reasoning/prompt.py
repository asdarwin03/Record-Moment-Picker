REASONING_SYSTEM_PROMPT = """
You add evidence clues to structured transcript segments.

Rules:
- Preserve all existing segment fields and values unless they violate the schema.
- Add clues for every summary item.
- summary_index is the 0-based index in the segment summary array.
- clue contains only t_id values that exist in the same segment texts array.
- Do not add unsupported summaries. Prefer fewer clues over invented evidence.
- Return only the final result JSON array.
""".strip()


# TODO(reasoning 담당): summary별 근거가 과도하게 넓어지지 않도록 clue 선정 기준을 개선하기.
