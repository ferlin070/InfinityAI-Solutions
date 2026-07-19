from crewai import Agent, Crew, Process, Task
from crewai.flow.flow import Flow, listen, start

from src.ai.agents.factory import build_crewai_agent
from src.ai.agents.registry import load_agent
from src.core.config import logger


class InboundConversationFlow(Flow):
    def __init__(self, conversation_id: str, last_messages: list[dict],
                 lead_profile: dict | None, products: list[dict],
                 phone_number: str = "",
                 org_id: str = "00000000-0000-0000-0000-000000000001"):
        super().__init__()
        self.conversation_id = conversation_id
        self.last_messages = last_messages
        self.lead_profile = lead_profile
        self.products = products
        self.phone_number = phone_number
        self.org_id = org_id

    @start()
    def maya_reply(self):
        maya_config = load_agent("MAYA", org_id=self.org_id)
        maya = build_crewai_agent(maya_config)

        conversation_history = "\n".join(
            f"[{m.get('sender', 'customer')}]: {m.get('body', '')}"
            for m in self.last_messages[-10:]
        )

        lead_info = ""
        if self.lead_profile:
            lead_info = (
                f"Nama: {self.lead_profile.get('name', 'Unknown')}\n"
                f"Skor: {self.lead_profile.get('score', 'cold')}\n"
                f"Minat: {self.lead_profile.get('interest_summary', 'N/A')}"
            )

        product_catalog = ""
        if self.products:
            product_catalog = "\n".join(
                f"- {p['name']}: RM{p['unit_price']:.2f}"
                for p in self.products
            )

        system_prompt = (
            "Anda adalah Maya, pakar jualan dan CRM InfinityAI Solutions. "
            "Balas mesej WhatsApp pelanggan dengan nada mesra, profesional, "
            "dan helpful.\n\n"
            "Gunakan alat Product Pricing untuk semak harga produk sebenar.\n"
            "Gunakan alat Contact Info untuk lihat profil pelanggan.\n"
            "Gunakan alat Conversation History untuk semak perbualan lepas.\n\n"
            "Balas dalam format JSON seperti ini — bolehlah bercakap secara natural "
            "dahulu, kemudian akhir sekali sertakan JSON ini:\n"
            '{\n'
            '  "reply": "balasan WhatsApp dalam Bahasa Melayu",\n'
            '  "intent": "buying|inquiry|complaint|unclear",\n'
            '  "lead_score": "hot|warm|cold",\n'
            '  "score_reason": "sebab kenapa skor ini",\n'
            '  "needs_quotation": true|false,\n'
            '  "items": [{"name": "nama produk", "qty": 1}] | null\n'
            '}'
        )

        user_context = f"""
Nombor Telefon Pelanggan: {self.phone_number}

Perbualan terkini:
{conversation_history}

Profil lead:
{lead_info}

Katalog produk:
{product_catalog}

Balas dengan JSON seperti format yang ditetapkan.
"""

        task = Task(
            description=f"{system_prompt}\n\n{user_context}",
            expected_output=(
                "JSON tepat mengikut format yang dinyatakan. Tiada teks lain di luar JSON."
            ),
            agent=maya,
        )

        crew_output = Crew(
            agents=[maya],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        ).kickoff()

        result = str(crew_output)
        self._state["maya_result"] = result
        return result

    @listen(maya_reply)
    def handle_quotation(self):
        import json
        from src.services.logging import extract_json

        result = self._state.get("maya_result", "")
        json_str = extract_json(result)
        if not json_str:
            logger.warning("Maya did not return valid JSON")
            self._state["quotation_needed"] = False
            self._state["reply"] = "Maaf, saya tidak dapat memproses permintaan anda buat masa ini."
            return

        try:
            decision = json.loads(json_str)
        except json.JSONDecodeError:
            self._state["quotation_needed"] = False
            self._state["reply"] = "Maaf, saya tidak dapat memproses permintaan anda buat masa ini."
            return

        self._state["reply"] = decision.get("reply", "")
        self._state["intent"] = decision.get("intent", "unclear")
        self._state["lead_score"] = decision.get("lead_score", "cold")
        self._state["score_reason"] = decision.get("score_reason", "")
        needs_q = decision.get("needs_quotation", False)
        self._state["quotation_needed"] = needs_q

        if needs_q and decision.get("items"):
            self._state["quotation_items"] = decision["items"]
