"""Tests for prompt assembly."""
from __future__ import annotations

from app.prompt import PromptBuilder


def test_prompt_contains_schema_and_question(demo_schema):
    prompt = PromptBuilder(demo_schema).build("How many orders last month?")
    assert "orders" in prompt
    assert "order_items" in prompt
    assert "customers" in prompt
    assert "How many orders last month?" in prompt


def test_prompt_contains_few_shot_example(demo_schema):
    prompt = PromptBuilder(demo_schema).build("How many orders last month?")
    assert "top 5 customers" in prompt.lower()
    assert "DATE_SUB(CURDATE(), INTERVAL 5 YEAR)" in prompt


def test_prompt_error_context_appended(demo_schema):
    prompt = PromptBuilder(demo_schema).build(
        "Who are the top 5 customers?", error_context="Unknown column 'x'"
    )
    assert "Unknown column 'x'" in prompt
    assert "corrected SQL" in prompt
