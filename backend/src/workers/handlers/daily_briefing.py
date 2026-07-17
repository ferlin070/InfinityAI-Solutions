from datetime import datetime, timezone, timedelta
from src.core.config import logger
from src.db.repositories.leads import LeadRepo
from src.db.repositories.conversations import ConversationRepo
from src.db.repositories.quotations import QuotationRepo
from src.db.repositories.reports import ReportRepo
from src.channels.wa_webjs import WAWebJSProvider
from src.ai.agents.registry import load_agents
from src.ai.agents.factory import build_crewai_agent
from src.ai.crewai_adapter.llm_adapter import InfinityLLMAdapter
from src.ai.providers.registry import resolve_provider

ORG_ID = "00000000-0000-0000-0000-000000000001"


def daily_briefing(job: dict) -> None:
    lead_repo = LeadRepo()
    conv_repo = ConversationRepo()
    q_repo = QuotationRepo()
    report_repo = ReportRepo()

    today = datetime.now(timezone.utc).date()
    leads = lead_repo.list_by_org(ORG_ID)
    open_convs = conv_repo.list_open(ORG_ID)
    pending_q = q_repo.list_pending_approval(ORG_ID)

    new_leads = [l for l in leads if l.get("created_at") and datetime.fromisoformat(l["created_at"]).date() == today]
    hot_leads = [l for l in leads if l.get("score") == "hot"]

    summary_data = (
        f"Ringkasan harian ({today.isoformat()}):\n"
        f"- Lead baru hari ini: {len(new_leads)}\n"
        f"- Lead hot aktif: {len(hot_leads)}\n"
        f"- Perbualan open: {len(open_convs)}\n"
        f"- Quotation pending approval: {len(pending_q)}\n\n"
        f"Butiran lead baru:\n" + "\n".join(
            f"  - {l.get('contacts', {}).get('name', 'Unknown')} ({l.get('score', 'cold')})"
            for l in new_leads[:5]
        ) if new_leads else "  Tiada lead baru hari ini.\n"
    )

    agents_cfg = load_agents(ORG_ID)
    claudia_cfg = next(a for a in agents_cfg.values() if a.key.upper() == "CLAUDIA")
    provider = resolve_provider(claudia_cfg)
    adapter = InfinityLLMAdapter(provider=provider)

    system_prompt = (
        "Anda adalah Claudia, Ketua Staf AI. Berdasarkan data ringkasan harian di bawah, "
        "hasilkan briefing harian yang ringkas dalam Bahasa Melayu untuk pemilik perniagaan. "
        "Sertakan cadangan tindakan untuk hari ini. Format dalam teks biasa."
    )

    briefing = adapter.call([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": summary_data},
    ])

    report_repo.create(ORG_ID, "daily_briefing", today, today, briefing)

    channel = WAWebJSProvider()
    channel.send_text(
        "default",  # will be resolved to actual owner channel
        "",  # will be resolved to owner's number
        f"*Selamat Pagi Bos!* ☕\n\n{briefing}",
    )

    logger.info(f"Daily briefing generated and sent for {today}")
