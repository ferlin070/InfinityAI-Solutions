"""Planner — produces a structured `Plan` from a user prompt.

The current `TaskExecutionFlow` (V1) has Claudia decide routing as
text — "I'll send this to HAKIM". Phase 1 of agentic-v3 splits that
into two LLM calls:

  1. Planner (THIS module): given the prompt + history + tool
     catalog, produce a `Plan` with `intent`, `subtasks[]`, dependencies,
     success criteria, fallback strategy.
  2. Coordinator: walk the plan, dispatch subtasks, build trace.

The Planner is intentionally simple: one LLM call that returns a
`Plan` Pydantic model. Phase 2 can add multi-step planning, but Phase
1 just needs the LLM to commit to a structured plan up-front so the
Coordinator (and the user) can see what's about to happen.

Why Pydantic + parse:
- The Planner LLM is asked for JSON. We use the same Pydantic model
  on both sides so the LLM knows the exact shape.
- A parsing failure is recoverable: the Planner falls back to a
  "simple" plan with one SubTask (route to NEXUS) so the user never
  gets an empty response.
"""

import json
import re
from typing import Optional

from src.ai.agentic.plan import Plan, SubTask, ToolHint
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
from src.core.config import logger


PLANNER_SYSTEM_PROMPT = """\
Anda adalah PLANNER untuk sistem multi-agent InfinityAI Solutions.
Tugas anda: analisis permintaan Bos, dan hasilkan SATU pelan berstruktur
(JSON) yang akan digunakan oleh Coordinator untuk diagihkan kepada ejen.

SKEMA OUTPUT (WAJIB ikut format ini):

{
  "intent": "<satu ayat: apa yang Bos sebenarnya mahu>",
  "complexity": "simple" | "moderate" | "complex",
  "success_criteria": "<kriteria kejayaan untuk SELURUH pelan>",
  "fallback_strategy": "<apa yang perlu dilakukan jika pelan gagal, atau null>",
  "subtasks": [
    {
      "id": "sub_1",
      "description": "<apa yang perlu dilakukan>",
      "agent_key": "<NAMA EJEN>",
      "success_criteria": "<kriteria kejayaan untuk subtask ini>",
      "required_capabilities": ["<capability1>", "<capability2>"],
      "tool_hints": [{"tool_name": "<Nama Tool>", "reason": "<kenapa>"}],
      "depends_on": ["sub_X"],
      "parallelizable": false,
      "approval_required": false,
      "max_tool_calls": 5
    }
  ]
}

PANDUAN MEMILIH EJEN:
- CLAUDIA — tidak pernah pilih sebagai agent_key. Claudia adalah router.
- MAYA — sales, CRM, sebut harga, prospek, customer history.
- HAKIM — teknikal, IT, sistem, dokumentasi, browser, status platform.
- AMELIA — latihan, modul, nota kelas, bahan pembelajaran.
- DANISH — copywriting, e-book, content, Image Generation.
- AIMAN — pemasaran, branding, strategi iklan, marketing plan.
- ZARA — kewangan, bajet, invois, sebut harga, kelulusan.
- ADILA — operasi, log harian, daily briefing, business profile.
- NEXUS — generalist fallback (cross-domain, kabur, atau tiada ejen khusus sesuai).

CONTOH:

User: "Adakah kita sudah bersambung dengan WhatsApp?"
Output:
{
  "intent": "Bos mahu tahu status sambungan WhatsApp InfinityAI.",
  "complexity": "simple",
  "success_criteria": "Balas dengan status WhatsApp (tersambung / menunggu / tidak) dalam 1-2 ayat.",
  "fallback_strategy": "Jika tiada data, beritahu Bos pergi ke Settings > WhatsApp Connection untuk setup.",
  "subtasks": [
    {
      "id": "sub_1",
      "description": "Semak status WhatsApp channel dalam sistem",
      "agent_key": "HAKIM",
      "success_criteria": "Kembalikan status WhatsApp (tersambung / menunggu / tidak) + bilangan channel",
      "required_capabilities": ["platform.status", "whatsapp.read"],
      "tool_hints": [
        {"tool_name": "DB Platform Status", "reason": "Aggregated status platform termasuk WhatsApp"},
        {"tool_name": "DB List Channels", "reason": "Senarai WhatsApp channel + status terperinci"}
      ],
      "depends_on": [],
      "parallelizable": false,
      "approval_required": false,
      "max_tool_calls": 3
    }
  ]
}

User: "Buat poster untuk produk baru dan hantar ke Instagram."
Output:
{
  "intent": "Bos mahu poster visual untuk produk baru, bersedia untuk Instagram.",
  "complexity": "moderate",
  "success_criteria": "Balas dengan imej banner yang dijana + caption Instagram + URL/handle Instagram (jika ada).",
  "fallback_strategy": "Jika Image Generation gagal, hantar text copy sahaja dengan nota 'imej belum dijana'.",
  "subtasks": [
    {
      "id": "sub_1",
      "description": "Cari produk baru dalam katalog",
      "agent_key": "DANISH",
      "success_criteria": "Kembalikan nama produk + harga untuk dipakai dalam poster",
      "required_capabilities": ["product.read"],
      "tool_hints": [{"tool_name": "DB Search Products", "reason": "Cari produk berdasarkan nama atau deskripsi"}],
      "depends_on": [],
      "parallelizable": false,
      "approval_required": false,
      "max_tool_calls": 2
    },
    {
      "id": "sub_2",
      "description": "Jana poster visual dengan Image Generation",
      "agent_key": "DANISH",
      "success_criteria": "Kembalikan imej base64 PNG yang dijana",
      "required_capabilities": ["image.generate"],
      "tool_hints": [{"tool_name": "Image Generation", "reason": "Tool Image Generation menjana banner / poster / grafik"}],
      "depends_on": ["sub_1"],
      "parallelizable": false,
      "approval_required": false,
      "max_tool_calls": 3
    }
  ]
}

PENTING:
- Untuk soalan "adakah X?" / "apa status X?" — guna `simple` complexity, 1 subtask.
- Untuk tugasan multi-langkah — guna `moderate` atau `complex`, pecahkan kepada subtasks.
- `depends_on` mesti kosong untuk subtask pertama.
- `parallelizable=true` hanya jika subtask benar-benar bebas (no shared state).
- `agent_key` mesti salah satu daripada senarai di atas (Bukan CLAUDIA).
- JANGAN cadang pelan kosong — sekurang-kurangnya SATU subtask.
- Output HANYA JSON. Tiada teks lain di luar JSON."""


class Planner:
    """Produces a `Plan` from a user prompt via one LLM call.

    The Planner LLM is bound to gpt-4o-mini by default (cheap, fast,
    good enough for routing decisions). Override via `model` in the
    constructor if you want a smarter planner.
    """

    def __init__(self, llm: Optional[InfinityLLMAdapter] = None,
                 model: str = "gpt-4o-mini"):
        self._llm = llm
        self._model = model

    def _ensure_llm(self) -> InfinityLLMAdapter:
        if self._llm is None:
            from src.ai.providers.registry import resolve_provider
            from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
            provider = resolve_provider("openai", None)
            self._llm = InfinityLLMAdapter(
                provider=provider,
                model=self._model,
                agent_key="PLANNER",
                org_id=None,
            )
        return self._llm

    def plan(self, user_prompt: str, history: Optional[list[dict]] = None,
             max_retries: int = 1) -> Plan:
        """Return a `Plan` for `user_prompt`. Falls back to a minimal
        'send to NEXUS' plan if the LLM output can't be parsed, so the
        user always gets an executable plan."""
        history = history or []
        llm = self._ensure_llm()

        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        ]
        # Conversation history (turn-limited) — gives the planner context
        # for follow-up questions like "yes, do that" or "what about X?"
        for m in history[-6:]:
            role = m.get("role", "user")
            content = m.get("content", "")
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": user_prompt})

        # One retry if the first parse fails (sometimes the LLM
        # adds a stray code fence).
        for attempt in range(max_retries + 1):
            try:
                text = llm.call(messages)
            except Exception as e:
                logger.warning(f"Planner LLM call failed (attempt {attempt+1}): {e}")
                text = ""

            plan = self._parse_plan(text)
            if plan is not None and plan.subtasks:
                return plan
            logger.warning(
                f"Planner returned unparseable plan (attempt {attempt+1}); "
                f"first 200 chars: {text[:200]!r}"
            )

        # All attempts failed — return a safe fallback so the user
        # still gets an answer (NEXUS is the generalist).
        return self._fallback_plan(user_prompt)

    def _parse_plan(self, text: str) -> Optional[Plan]:
        if not text:
            return None
        # Try a few extraction strategies: raw, then ```json fence.
        candidates = [text]
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            candidates.append(m.group(1))
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            candidates.append(m.group(0))

        for c in candidates:
            try:
                data = json.loads(c)
            except (json.JSONDecodeError, ValueError):
                continue
            try:
                return Plan.model_validate(data)
            except Exception as e:
                logger.debug(f"Plan validation failed: {e}")
                continue
        return None

    def _fallback_plan(self, user_prompt: str) -> Plan:
        """Used when the LLM output can't be parsed. Always returns a
        valid Plan so the Coordinator has something to execute."""
        return Plan(
            intent=user_prompt[:200],
            complexity="simple",
            success_criteria="Balas dengan jawapan terbaik untuk permintaan Bos (generalist fallback).",
            fallback_strategy="Jika NEXUS juga gagal, jawab dengan chat terus.",
            subtasks=[
                SubTask(
                    id="sub_1",
                    description=user_prompt,
                    agent_key="NEXUS",
                    success_criteria="Berikan jawapan yang membantu untuk permintaan Bos.",
                    required_capabilities=[],
                    tool_hints=[
                        ToolHint(tool_name="DB Discover Tools", reason="Lihat senarai tool tersedia untuk pilih yang sesuai"),
                    ],
                    depends_on=[],
                    parallelizable=False,
                    approval_required=False,
                    max_tool_calls=5,
                ),
            ],
        )
