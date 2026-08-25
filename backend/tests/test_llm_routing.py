"""The fallback engine must receive the bare question, not the assembled prompt.

Regression test for the bug where the full prompt (containing few-shot
examples with the words "average order value" and "region") made the fallback
always match its first rule.
"""
from __future__ import annotations

import pytest

from app.llm import FallbackClient, OllamaClient, llm_input_for
from app.prompt import PromptBuilder


def test_llm_input_for_routes_correctly():
    fb = FallbackClient()
    ollama = OllamaClient("http://localhost:11434", "model")
    prompt = "system... Question: how many orders? SQL:"
    question = "how many orders?"
    assert llm_input_for(fb, prompt, question) == question
    assert llm_input_for(ollama, prompt, question) == prompt


@pytest.mark.parametrize(
    "question,fragment",
    [
        ("How many orders were placed last month?", "COUNT(*)"),
        ("What's the average order value by region?", "c.region"),
        ("List all products with less than 10 units in stock.", "stock_quantity"),
        ("Show me the 3 best-selling products by quantity sold.", "units_sold"),
    ],
)
def test_fallback_not_confused_by_few_shot_prompt(demo_schema, question, fragment):
    # Simulate what the pipeline feeds the fallback: the bare question.
    prompt = PromptBuilder(demo_schema).build(question)
    fed = llm_input_for(FallbackClient(), prompt, question)
    sql = FallbackClient().generate(fed)
    assert fragment in sql
