from crewai.tools import tool
from openai import OpenAI

from src.core.config import OPENAI_API_KEY, logger


def build_image_generation_tool(collector: list[dict]):
    """Tool factory (not a shared instance) — each call/specialist run gets its
    own closure-bound `collector`, mirroring the `captured: list[LLMResult]`
    pattern already used in task_execution_flow.py's `_run_specialist`.

    The tool returns only a short confirmation string to the LLM — the actual
    image bytes never re-enter the model's context (a base64 PNG would blow up
    token usage) — and are appended to `collector` instead, for the caller to
    attach directly to the AgentResult.
    """

    @tool("Image Generation")
    def image_generation_tool(prompt: str) -> str:
        """Jana imej (banner, poster, grafik promosi, ilustrasi) daripada
        penerangan teks. Guna bila diminta 'gambar', 'banner', 'poster',
        'grafik', atau sebarang visual lain dijana."""
        try:
            client = OpenAI(api_key=OPENAI_API_KEY or "missing_key")
            resp = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json",
            )
            b64 = resp.data[0].b64_json
            collector.append({
                "type": "image",
                "mime_type": "image/png",
                "data_base64": b64,
                "caption": prompt,
            })
            return f"Imej berjaya dijana untuk: '{prompt}'. Ia akan dipaparkan terus kepada Bos."
        except Exception as e:
            logger.error(f"Ralat menjana imej: {e}", exc_info=True)
            return f"Gagal menjana imej: {e}"

    return image_generation_tool
