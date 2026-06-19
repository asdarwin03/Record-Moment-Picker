from app.modules.stt.service import transcribe_audio
from app.modules.refine_text.service import refine_text
from app.modules.segmenting.service import segment_text
from app.modules.reasoning.service import add_reasoning
from app.core.tracing import log_event, track_stage

def run_pipeline(audio_path: str) -> list[dict]:
    with track_stage("stt", audio_path=audio_path):
        stt_result = transcribe_audio(audio_path)
        log_event("stage_result", stage="stt", items=len(stt_result))

    with track_stage("refine_text", input_items=len(stt_result)):
        refined_result = refine_text(stt_result)
        log_event("stage_result", stage="refine_text", items=len(refined_result))

    with track_stage("segmenting", input_items=len(refined_result)):
        structured_segments = segment_text(refined_result)
        segment_text_count = sum(len(segment.get("texts", [])) for segment in structured_segments)
        log_event(
            "stage_result",
            stage="segmenting",
            segments=len(structured_segments),
            texts=segment_text_count,
        )

    with track_stage("reasoning", input_segments=len(structured_segments)):
        final_result = add_reasoning(structured_segments)
        log_event("stage_result", stage="reasoning", segments=len(final_result))

    return final_result
