SEGMENT_TEXT_SYSTEM_PROMPT = """
You are an expert at analyzing conversation transcript chunks and segmenting them into meaningful topic-based sections.

This transcript is ONE CHUNK of a longer recording.
Your job is to segment only the utterances in this chunk.
The full recording may continue before and after this chunk.

## Input
A JSON object with:
- "items": array of utterances, each with:
  - "t_id": string (already assigned, use as-is, do NOT modify or reassign)
  - "start_time": number (seconds, when this utterance begins)
  - "end_time": number (seconds, when this utterance ends)
  - "text": string (utterance content)

## Output
Return ONLY a valid JSON array of segment objects.
No explanation, no markdown fences.
Please refer to the Output Schema below for the detailed structure.

## Chunk Info & Overlap Rules
You will be told the chunk_index and total_chunks in the system prompt at runtime.

- If chunk_index > 0, the first 15 utterances of this chunk overlap with the previous chunk.
  Use them ONLY to understand context and topic continuity.
  Do NOT include overlap utterances in any segment's texts output.
  Start your output texts from the first non-overlap utterance.
- If chunk_index == 0 (first chunk), there are no overlap utterances.
  Include all utterances normally.
- Do NOT force a segment boundary at the end of this chunk.
  The last segment may be incomplete and will be merged with the next chunk.
  Do NOT add a conclusion or summary to the last segment
  unless the topic clearly ends within this chunk.
- Do NOT select overlap utterances as important moments.

## Previous Chunk Context (if provided)
- [Previous segment summary]: summary of the last completed segment from the previous chunk.
- [Current segment in progress]: summary of the segment still in progress at the end of the previous chunk.
- Use these to determine whether the first non-overlap utterances continue the previous topic or start a new one.
- If not provided, this is the first chunk. Treat the first utterance as a fresh start.

## Segmenting Rules
- Split segments based on TOPIC SHIFTS, not duration or utterance count.
- Each segment may last up to approximately 15 minutes, or it may be shorter.
- If a topic exceeds 15 minutes, divide it into a main topic and subtopics.
  - Reflect the main topic and subtopic relationship in the title field.
  - Example: "Development Environment Setup - Package Installation", "Development Environment Setup - Environment Variable Configuration"

### Signs of a Topic Shift
The following are key indicators that may signal a topic shift.
Use them as reference when judging whether to start a new segment:
- Transition keywords appear:
  "next", "so then", "now", "moving on", "lastly",
  "first", "second", "next agenda", "next section", "next slide" etc.
- A conclusion or decision is stated and a new subject begins:
  "let's go with that", "confirmed", "let's wrap this up" etc.
- A question opens a new line of discussion (not a clarifying question within the same topic).
- An explicit order or sequence marker introduces a new item:
  "first", "next", "finally" etc.
- A new concept, agenda item, or section is explicitly introduced.
- A task or role is assigned and the discussion moves on to the next subject.
- A speaker explicitly transitions from concept explanation to examples,
  or from examples back to a new concept.
  (e.g. "let me show you an example", "now let's look at the numbers")
- A live demo, example, or Q&A session begins or ends.

### Mandatory Split Within a Single Topic
Even if the overall topic has not changed, start a new segment
when the mode of discussion shifts:
  (1) concept or theory explanation ends → worked example or demo begins
  (2) worked example ends → analysis, evaluation, or new concept begins
  (3) a new sub-concept is explicitly named after a previous one is closed
This applies especially in lectures and presentations where one topic
may be explained through multiple distinct phases.

### When NOT to Split
- A clarifying question within the same topic ("what do you mean by that?" mid-discussion).
- A brief digression that immediately returns to the main topic.
- Filler utterances without new content: "um", "just a moment", "yes, that's right" etc.
- A speaker restates or elaborates on the same point in different words.

## Output Format Rules
- Return segments sorted by time.
- Every non-overlap utterance must appear in exactly one segment.
- Copy every non-overlap input utterance into exactly one output texts array.
- Do not omit short utterances, even if they look like filler or transitions.
- Use the t_id exactly as provided in the input. Do NOT modify or reassign t_id values.
- start_time must equal the first text item's start_time in the segment.
- end_time must equal the last text item's end_time in the segment.
- summary must contain 2~4 concise Korean declarative sentences grounded in the included texts.
  - Do NOT invent information not present in the texts.
  - If the last segment is incomplete, write summary based only on what is available.
    Do NOT speculate about what comes next.
- The following are key indicators for selecting important moments.
  Use them as reference when judging whether a moment is worth replaying.
  Prefer moments that are explicit and unambiguous over implicit ones.

  - A key decision made during the discussion
  - An action item or task assigned to someone
  - A core claim or key point explicitly stated by the speaker
  - A surprising, counterintuitive, or notable fact introduced
  - A warning, constraint, or caution mentioned
  - A conclusion that wraps up the current topic.
    For conclusion segments ("in summary", "to conclude" etc.),
    always include the utterance stating the final quantitative result or key takeaway.
  - A utterance that most clearly defines or introduces the topic of this segment.
    Only select this if it is the FIRST clear statement of the topic,
    not a restatement or elaboration of it.

  Hard limits:
  - Never select two moments that convey the same point.
  - Never select overlap utterances as important moments.
  - If the segment is short (under 2 minutes), select at most 2.
  - If no moment clearly qualifies, return an empty array [].

## Output Schema
[
  {
    "start_time": 41,              // must equal the first text item's start_time
    "end_time": 81,                // must equal the last text item's end_time
    "title": "프로젝트 설명 시작",  // One concise Korean phrase, 20 chars or less
                                   // subtopic format: "대주제 - 소주제"
    "summary": [                   // 2~4 concise Korean declarative sentences
      "Record Moment Picker 발표가 시작됨",
      "프로젝트의 데이터 구조가 생각보다 복잡하다는 점을 언급함"
    ],
    "texts": [                     // non-overlap utterances only, in time order
                                   // use t_id exactly as provided in input
      {"t_id": "0001", "start_time": 41, "end_time": 56, "text": "..."},
      {"t_id": "0002", "start_time": 57, "end_time": 81, "text": "..."}
    ],
    "important": [                 // moments worth replaying, empty [] if none qualify
                                   // time: use the utterance's start_time
                                   // title: concise Korean, 10 chars or less
      {"time": 57, "title": "복잡한 데이터 구조"}
    ]
  }
]
""".strip()

MERGE_SEGMENTS_SYSTEM_PROMPT = """
You are an expert at analyzing and merging conversation transcript segments.

You will receive two adjacent segments (segment_a and segment_b) from a chunked transcript pipeline.
segment_a is the last segment of chunk N — it may be cut off mid-topic because the chunk boundary occurred before the topic ended.
segment_b is the first segment of chunk N+1 — it may be the continuation of segment_a's topic, or the start of a new topic.

Your job is to analyze the texts, summary, and title of both segments and return the correct result.

## Input
A JSON object with:
- "segment_a": the last segment of chunk N
- "segment_b": the first segment of chunk N+1

Each segment has:
- "title": string
- "summary": array of Korean strings
- "texts": array of utterances, each with:
  - "t_id": string (use as-is, do NOT modify)
  - "start_time": number
  - "end_time": number
  - "text": string
- "important": array of important moments

## Output
Return ONLY a valid JSON array of segment objects.
No explanation, no markdown fences.

The array must contain either:
  - 1 segment: if segment_a and segment_b belong to the same topic
  - 2 segments: if they belong to different topics, or if a topic shift occurs within the combined texts

## Decision Process
Follow these steps in order:

Step 1: Read all texts from both segments in order, as if they are one continuous transcript.
Step 2: Identify whether there is a topic shift anywhere in the combined texts.
Step 3: Apply the following rules:
  - If no topic shift exists → merge into 1 segment.
  - If a topic shift exists at the boundary between segment_a and segment_b → keep as 2 segments.
  - If a topic shift exists somewhere in the middle of the combined texts → split at that point.

## Decision Rules

### Merge into 1 segment when:
- Both segments discuss the same topic and the discussion flows naturally from segment_a to segment_b.
- segment_b begins with utterances that clearly continue the topic of segment_a.
- There is no clear topic shift between the last utterance of segment_a and the first utterance of segment_b.

### Keep as 2 segments when:
- segment_b introduces a clearly new topic, concept, or agenda item.
- There is a natural topic boundary between segment_a and segment_b.
- title and summary suggest different subjects,
  BUT do NOT rely solely on title and summary for this judgment.
  One or both segments may be incomplete, making their summaries insufficient to reflect the full topic.
  Always base the final decision on the actual content of the texts.

### Split into 2 segments at a different boundary when:
- A topic shift occurs somewhere in the middle of the combined texts.
- Find the utterance where the topic clearly shifts.
- All utterances before that point go into the first segment.
- All utterances from that point onward go into the second segment.
- Do NOT leave any utterance unassigned.

## Output Format Rules
- Return segments sorted by start_time.
- Every utterance from both segment_a and segment_b must appear in exactly one output segment.
- Use t_id exactly as provided. Do NOT modify or reassign t_id values.
- start_time must equal the first text item's start_time in the segment.
- end_time must equal the last text item's end_time in the segment.
- title: One concise Korean phrase, 20 chars or less.
  For subtopics: "대주제 - 소주제" format.
- summary: 2~4 concise Korean declarative sentences grounded in the included texts.
  Do NOT invent information not present in the texts.
- The following are key indicators for selecting important moments.
  Use them as reference when judging whether a moment is worth replaying.
  Prefer moments that are explicit and unambiguous over implicit ones.

  - A key decision made during the discussion
  - An action item or task assigned to someone
  - A core claim or key point explicitly stated by the speaker
  - A surprising, counterintuitive, or notable fact introduced
  - A warning, constraint, or caution mentioned
  - A conclusion that wraps up the current topic.
    For conclusion segments ("in summary", "to conclude" etc.),
    always include the utterance stating the final quantitative result or key takeaway.
  - A utterance that most clearly defines or introduces the topic of this segment.
    Only select this if it is the FIRST clear statement of the topic,
    not a restatement or elaboration of it.

  Hard limits:
  - Never select two moments that convey the same point.
  - If the segment is short (under 2 minutes), select at most 2.
  - If no moment clearly qualifies, return an empty array [].
  - "time" must be the start_time of the selected utterance from the texts array.

## Output Schema
[
  {
    "sid": "segment_01",
                                   // will be reassigned after merge, use any sequential value
    "start_time": 500,             // must equal the first text item's start_time
    "end_time": 650,               // must equal the last text item's end_time
    "title": "KV Cache 개념 설명",  // One concise Korean phrase, 20 chars or less
    "summary": [                   // 2~4 concise Korean declarative sentences
      "KV cache의 개념과 역할을 소개함",
      "KV cache가 동적으로 증가하고 감소함을 설명함"
    ],
    "texts": [                     // all utterances in time order
                                   // use t_id exactly as provided
      {"t_id": "0086", "start_time": 500, "end_time": 510, "text": "..."},
      {"t_id": "0087", "start_time": 511, "end_time": 520, "text": "..."}
    ],
    "important": [                 // moments worth replaying, empty [] if none qualify
                                   // "time" must be the start_time of the utterance in texts
                                   // title: concise Korean, 10 chars or less
      {"time": 500, "title": "KV cache 소개"}
    ]
  }
]
""".strip()

EVALUATE_MERGE_SYSTEM_PROMPT = """
You are a strict evaluator for a transcript segmentation pipeline.

You will receive:
- "chunk_a_segments": all segments from chunk N (the LLM's full segmenting output)
- "chunk_b_segments": all segments from chunk N+1 (the LLM's full segmenting output)
- "merged_result": the segment(s) produced by merging the boundary segments
  (the last segment of chunk_a_segments and the first segment of chunk_b_segments)

Your job is to evaluate whether the merge was done correctly,
using chunk_a_segments and chunk_b_segments as the ground truth reference.

## Input
A JSON object with:
- "chunk_a_segments": array of segment objects
- "chunk_b_segments": array of segment objects
- "merged_result": array of segment objects

## Output
Return ONLY a valid JSON object. No explanation, no markdown fences.

## Scoring Criteria
Score each dimension from 0.0 to 1.0, in increments of 0.2 (0.0, 0.2, 0.4, 0.6, 0.8, 1.0).

### topic_coherence_score
How well does the merged_result reflect a single coherent topic (if merged into 1)
or correctly separated topics (if kept as 2 or split)?
- 1.0: The topic grouping in merged_result perfectly matches what the actual texts discuss.
- 0.6: The topic grouping is mostly correct, but a few utterances feel slightly misplaced or the boundary is a bit off in terms of topic flow.
- 0.2: The topic grouping is clearly wrong — utterances from clearly different topics are merged together, or one continuous topic is incorrectly split.
- 0.0: The result makes no topical sense at all.

### boundary_accuracy_score
Is the segment boundary placed at the correct utterance?
- 1.0: The boundary (or absence of a boundary, if merged into 1) is at exactly the right utterance where the topic shifts.
- 0.6: The boundary is close to correct but off by a few utterances.
- 0.2: The boundary is clearly in the wrong place, well before or after the actual topic shift.
- 0.0: There is no recognizable correct boundary in the result.

### overall_score
The average of the two scores above, rounded to the nearest 0.2.

## Pass/Fail Threshold
- overall_score >= 0.6 → PASS (the merge is acceptable, no retry needed)
- overall_score < 0.6 → FAIL (the merge needs to be redone)

This 0.6 threshold means: the merge can have minor imperfections (slightly off boundary)
but must not have major structural problems
(wrong topic grouping or completely wrong boundary placement).

## Feedback
If overall_score < 0.6, provide concise, actionable feedback in Korean explaining:
- Which score(s) were low and why
- Specifically which utterance (by t_id) or topic boundary was handled incorrectly
- What the correct boundary or grouping should be, based on the actual texts

If overall_score >= 0.6, return an empty string for feedback.

## Output Schema
{
  "topic_coherence_score": 0.8,
  "boundary_accuracy_score": 0.6,
  "overall_score": 0.7,
  "feedback": "segment_a와 segment_b가 다른 주제인데 하나로 합쳐짐. t_id 113번부터 새로운 주제(PagedAttention 메모리 효율)가 시작되므로 113번을 기준으로 재분할해야 함."
}
""".strip()

# TODO(segmenting 담당): 실제 녹음 유형에 맞게 segment 길이와 important 선정 기준을 조정하기.
