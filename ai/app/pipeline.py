from app.modules.stt.service import transcribe_audio
from app.modules.refine_text.service import refine_text
from app.modules.segmenting.service import segment_text
from app.modules.reasoning.service import add_reasoning

def run_pipeline(audio_path: str) -> list[dict]:
    stt_result = transcribe_audio(audio_path)
    refined_result = refine_text(stt_result)
    structured_segments = segment_text(refined_result)
    final_result = add_reasoning(structured_segments)

    return final_result