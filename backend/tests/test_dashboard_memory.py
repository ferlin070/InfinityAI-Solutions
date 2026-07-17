import sys
import os
import importlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def memory(tmp_path, monkeypatch):
    import src.services.dashboard_memory as dashboard_memory
    monkeypatch.chdir(tmp_path)
    importlib.reload(dashboard_memory)
    yield dashboard_memory


def test_append_and_get_recent_roundtrip(memory):
    memory.append_message("user", "hai")
    memory.append_message("assistant", "hai jugak Bos!")

    recent = memory.get_recent()

    assert recent == [
        {"role": "user", "content": "hai"},
        {"role": "assistant", "content": "hai jugak Bos!"},
    ]


def test_get_recent_respects_n(memory):
    for i in range(5):
        memory.append_message("user", f"mesej {i}")

    recent = memory.get_recent(n=2)

    assert [m["content"] for m in recent] == ["mesej 3", "mesej 4"]


def test_clear_empties_history(memory):
    memory.append_message("user", "hai")
    memory.clear()

    assert memory.get_recent() == []


def test_history_persists_across_reload(memory, tmp_path, monkeypatch):
    memory.append_message("user", "hai")

    import src.services.dashboard_memory as reloaded
    monkeypatch.chdir(tmp_path)
    importlib.reload(reloaded)

    assert reloaded.get_recent() == [{"role": "user", "content": "hai"}]


def test_get_recent_on_missing_file_returns_empty_list(memory):
    assert memory.get_recent() == []
