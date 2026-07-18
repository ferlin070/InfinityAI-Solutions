import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── Regression: bug is fixed ───────────────────────────────────────────────

def test_claudia_story_no_longer_says_chat_is_default():
    """The original bug: 'chat is default' made the agent just chat when
    the user asked 'adakah X?'. Verify the rewrite flipped the default
    to tool-first."""
    from src.ai.prompts.loader import resolve_role_goal_backstory
    _, _, backstory = resolve_role_goal_backstory("CLAUDIA")
    upper = backstory.upper()
    # The old "chat is default" guidance is gone.
    assert "CHAT STATUS" not in upper or "HANYA UNTUK" in upper, (
        "Expected 'chat' to be qualified as 'only for sapaan/ucapan/soalan闲聊', not default"
    )
    # New tool-first guidance is present.
    assert "DB PLATFORM STATUS" in upper, "Should explicitly mention DB Platform Status as the tool to use for status questions"
    assert "JANGAN JAWAB" in upper or "JANGAN JAWAB" in backstory, "Should forbid empty 'saya tak pasti' responses"


def test_claudia_has_quick_check_tools():
    """The fix: Claudia has a small 'quick-check' toolset so she can
    answer status/config/discovery questions directly with a real call."""
    from src.ai.agents.tool_mappings import STATIC_TOOL_MAPPINGS
    tools = STATIC_TOOL_MAPPINGS["CLAUDIA"]
    names = {t.name for t in tools}
    assert "DB Platform Status" in names
    assert "DB Get Configuration Status" in names
    assert "DB Discover Platform" in names
    assert "DB Get Recent Activity" in names
    assert "DB Get Business Profile" in names


def test_claudia_backstory_lists_concrete_routing_examples():
    """The rewrite should include the exact failure case 'adakah kita
    sudah bersambung dengan WhatsApp?' as a worked routing example."""
    from src.ai.prompts.loader import resolve_role_goal_backstory
    _, _, backstory = resolve_role_goal_backstory("CLAUDIA")
    assert "adakah kita sudah bersambung dengan WhatsApp" in backstory.lower() or \
           "whatsapp" in backstory.lower()
    # The new example should map to a tool, not a chat reply
    lower = backstory.lower()
    assert "platform status" in lower


# ─── Other agents also got "investigate thoroughly" guidance ───────────────

def test_all_specialists_have_investigate_thoroughly_guidance():
    """Each specialist should be told to use multiple tools and not
    answer in one line."""
    from src.ai.prompts.loader import resolve_role_goal_backstory
    for key in ("MAYA", "HAKIM", "ZARA", "DANISH", "AIMAN", "AMELIA", "ADILA", "NEXUS"):
        _, _, backstory = resolve_role_goal_backstory(key)
        upper = backstory.upper()
        # At least one of the SELIDIKI / AMALAN phrases should be present.
        assert "SELIDIKI" in upper or "AMALAN TERBAIK" in upper, (
            f"{key} backstory should encourage thorough investigation, not one-line answers"
        )


def test_claudia_backstory_examples_cover_whatsapp_question():
    """The exact failure case from the user — verify the rewrite added
    it as a concrete example routed to DB Platform Status."""
    from src.ai.prompts.loader import resolve_role_goal_backstory
    _, _, backstory = resolve_role_goal_backstory("CLAUDIA")
    # Look for either the literal phrase or a paraphrase
    has_wa_question = (
        "sambung dengan whatsapp" in backstory.lower() or
        "tersambung dengan whatsapp" in backstory.lower() or
        "sambungan whatsapp" in backstory.lower()
    )
    assert has_wa_question, "Should include the WhatsApp-status question as a worked example"
