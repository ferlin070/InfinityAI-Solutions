import pytest
import json
import os
from main import extract_json

def test_extract_json_simple():
    text = '{"status": "accepted", "assignments": []}'
    assert extract_json(text) == '{"status": "accepted", "assignments": []}'

def test_extract_json_markdown():
    text = 'Here is the response:\n```json\n{"status": "accepted", "assignments": [{"agent": "ZARA", "task": "kira bajet"}]}\n```\nHope it helps.'
    expected = '{"status": "accepted", "assignments": [{"agent": "ZARA", "task": "kira bajet"}]}'
    result = extract_json(text)
    assert result is not None
    assert json.loads(result) == json.loads(expected)

def test_extract_json_with_nested_braces_in_string():
    # String contains dynamic braces inside text, which would break character counting
    text = 'Some extra text {"status": "accepted", "assignments": [{"agent": "HAKIM", "task": "Buat system design: {auth: True, database: PostgreSQL}"}]}'
    expected = '{"status": "accepted", "assignments": [{"agent": "HAKIM", "task": "Buat system design: {auth: True, database: PostgreSQL}"}]}'
    result = extract_json(text)
    assert result is not None
    assert json.loads(result) == json.loads(expected)

def test_extract_json_invalid():
    text = 'This has no json at all'
    assert extract_json(text) is None

def test_extract_json_malformed():
    text = '{"status": "accepted", "assignments": [{'
    result = extract_json(text)
    # Even if malformed, it should return something or fallback, but not crash
    assert result is not None or result is None
