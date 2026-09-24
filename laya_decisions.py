"""Typed Laya choice protocol shared by development and combat.

An option set is not a prewritten plan: callers discover feasible affordances
from live RimWorld state, then use this adapter to keep every option reachable
within the decision head's limited prompt budget.
"""

from __future__ import annotations

from typing import Any


def _bounded_question(agent: Any, instructions: str, options: dict[str, str]) -> dict[str, Any]:
    """Reserve Laya's short decision head for every option, not just the first few."""
    tokenizer = getattr(agent, "tok", None)
    if tokenizer is None:
        return {"type": "choice", "instructions": instructions, "criteria": options}
    config = getattr(agent, "cfg", {}) or {}
    head_limit = int(config.get("head_max_len", 192))
    instruction = str(instructions)
    while len(tokenizer(f"choice question: {instruction}", add_special_tokens=False)["input_ids"]) > 28:
        instruction = instruction[:max(8, len(instruction) - 16)]
    per_option = min(45, max(8, (head_limit - 36) // max(1, len(options)) - 1))
    criteria = {}
    for key, value in options.items():
        description = str(value)
        while description and len(tokenizer(f" {key}: {description}", add_special_tokens=False)["input_ids"]) > per_option:
            description = description[:max(0, len(description) - 12)]
        criteria[key] = description
    return {"type": "choice", "instructions": instruction, "criteria": criteria}


def ask_laya_choice(agent: Any, state: dict[str, Any], question_id: str,
                    instructions: str, options: dict[str, str]) -> tuple[str, dict[str, Any]]:
    """Run a bounded tournament: every offered option is actually seen by Laya."""
    if not options:
        raise ValueError(f"No feasible options for {question_id}")
    if len(options) == 1:
        selected = next(iter(options))
        return selected, {"question": {"id": question_id, "instructions": instructions, "criteria": options},
                          "answers": {question_id: {"choice": selected, "confidence": 1.0,
                          "probabilities": {selected: 1.0}, "resolved_without_model": True}}}
    remaining = dict(options)
    narrowing: list[dict[str, Any]] = []
    round_number = 0
    while len(remaining) > 6:
        rows = list(remaining.items())
        winners: dict[str, str] = {}
        for index in range(0, len(rows), 6):
            chunk = dict(rows[index:index + 6])
            if len(chunk) == 1:
                winners.update(chunk)
                continue
            stage_id = f"{question_id}_round_{round_number}_{index // 6}"
            question = _bounded_question(agent, instructions, chunk)
            stage = agent.predict(state, {stage_id: question})
            stage["question"] = {"id": stage_id, **question}
            selected = str((stage.get("answers") or {}).get(stage_id, {}).get("choice") or "")
            if selected not in chunk:
                raise ValueError(f"Laya returned invalid option {selected!r} for {stage_id}")
            winners[selected] = chunk[selected]
            narrowing.append(stage)
        remaining = winners
        round_number += 1
    question = _bounded_question(agent, instructions, remaining)
    raw = agent.predict(state, {question_id: question})
    raw["question"] = {"id": question_id, **question}
    selected = str((raw.get("answers") or {}).get(question_id, {}).get("choice") or "")
    if selected not in remaining:
        raise ValueError(f"Laya returned invalid option {selected!r} for {question_id}")
    if narrowing:
        raw = {**raw, "narrowing": narrowing}
    return selected, raw
