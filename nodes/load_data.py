"""Load preparation data and build per-topic lesson bundles.

Reads topics.json, augmented_topics.json, vuosikello.json from
output/{module}/ and creates a list of lesson items ready for
fan-out generation.
"""

import json
from pathlib import Path


SESSION_TYPES = ["luokkaopetus", "työpaja", "pienryhmä", "vierailu", "verkko"]


def load_data(state: dict) -> dict:
    """Build per-topic lesson bundles from preparation output.

    Returns:
        Dict with 'lesson_items' (list of dicts, one per topic).
    """
    module = state.get("module", "unknown").lower()
    project_dir = Path(state["project_dir"])
    out_dir = project_dir / "output" / module

    topics = json.loads((out_dir / "topics.json").read_text(encoding="utf-8"))["topics"]
    augmented = json.loads((out_dir / "augmented_topics.json").read_text(encoding="utf-8"))
    vuosikello = json.loads((out_dir / "vuosikello.json").read_text(encoding="utf-8"))

    slots = vuosikello.get("slots", [])
    module_upper = state.get("module", "OP1").upper()
    module_slots = [
        s for s in slots
        if s.get("module", "").upper().startswith(module_upper)
    ]
    if not module_slots:
        module_slots = slots

    lesson_items = []
    for i, topic in enumerate(topics):
        augmented_text = augmented[i] if i < len(augmented) else ""
        slot = module_slots[i % len(module_slots)]

        lesson_items.append({
            "id": f"{module}-lesson-{i + 1:02d}",
            "topic_id": topic.get("id", f"topic-{i + 1}"),
            "title": topic.get("title", f"Aihe {i + 1}"),
            "description": topic.get("one_line_description", ""),
            "module": module_upper,
            "augmented_content": augmented_text,
            "vuosikello_slot": {
                "year": slot.get("year", 1),
                "semester": slot.get("semester", "syksy"),
                "focus_areas": slot.get("focus_areas", []),
            },
            "session_type": SESSION_TYPES[i % len(SESSION_TYPES)],
            "duration_min": state.get("lesson_duration", 75),
        })

    return {
        "lesson_items": lesson_items,
        "current_step": "load_data",
    }
