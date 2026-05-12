SEGMENT_TEXT_SYSTEM_PROMPT = """
You split a refined transcript into meaningful listening segments.

Rules:
- Return segments sorted by time.
- Use sid values such as segment_01, segment_02, ...
- Assign globally unique t_id values such as 001, 002, ...
- Include each transcript item in exactly one segment unless impossible.
- start_time should match the first text item time in the segment.
- end_time should be greater than or equal to start_time.
- Summaries must be concise Korean sentences grounded in the included texts.
- Important moments should identify timestamps worth replaying.
- Return only the structured segments JSON array.
""".strip()


# TODO(segmenting 담당): 실제 녹음 유형에 맞게 segment 길이와 important 선정 기준을 조정하기.
