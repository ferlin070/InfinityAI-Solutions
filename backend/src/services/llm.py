import time
from openai import OpenAI
from fastapi import HTTPException
from src.core.config import NVIDIA_API_KEY, logger


client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY or "missing_key",
    timeout=60.0
)


def call_nvidia(sys_prompt: str, user_prompt: str, model: str, temperature: float = 0.7) -> tuple[str, float]:
    """
    Call NVIDIA NIM API with system and user prompts.

    Returns:
        tuple: (response_text, duration_seconds)
    """
    start = time.time()
    try:
        # Model-specific configuration
        extra_args = {}
        max_tokens = 4096

        if "kimi" in model.lower():
            extra_args["extra_body"] = {"chat_template_kwargs": {"thinking": True}}
            max_tokens = 16384

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            **extra_args
        )
        return resp.choices[0].message.content, time.time() - start

    except Exception as e:
        logger.error(f"Ralat semasa memanggil API NVIDIA NIM: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Ralat dalaman semasa berhubung dengan API NVIDIA NIM."
        )
