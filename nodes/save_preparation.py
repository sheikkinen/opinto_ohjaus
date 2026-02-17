"""Save preparation results to output files.

Writes topic_inventory, vuosikello, and augmented_topics
to output/{module}/ as JSON files for the generate phase.

Strips LLM response metadata (signatures, extras, content block
wrappers) to keep only useful text content.
"""

import json
from pathlib import Path


def _to_serializable(obj: object) -> object:
    """Convert Pydantic models and other objects to JSON-serializable form."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, list):
        return [_to_serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj


def _clean_augmented_topics(raw: list) -> list[str]:
    """Extract plain text from map+agent results.

    Raw format: [{"_map_index": N, "value": [{"type": "text", "text": "...", "extras": {"signature": "..."}}]}]
    Output: list of text strings, one per topic.
    """
    cleaned = []
    for item in raw:
        if isinstance(item, dict) and "value" in item:
            blocks = item["value"]
            if isinstance(blocks, list):
                texts = []
                for block in blocks:
                    if isinstance(block, dict):
                        texts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        texts.append(block)
                cleaned.append("\n".join(t for t in texts if t))
            elif isinstance(blocks, str):
                cleaned.append(blocks)
        elif isinstance(item, str):
            cleaned.append(item)
    return cleaned


def save_preparation(state: dict) -> dict:
    """Save preparation phase results to output/{module}/.

    Writes:
      - topics.json: extracted topic inventory
      - vuosikello.json: extracted vuosikello
      - augmented_topics.json: clean text per topic (signatures stripped)
    """
    module = state.get("module", "unknown").lower()
    project_dir = Path(state.get("project_dir", "projects/opinto_ohjaus"))
    out_dir = project_dir / "output" / module
    out_dir.mkdir(parents=True, exist_ok=True)

    topic_inventory = state.get("topic_inventory")
    vuosikello = state.get("vuosikello")
    augmented_topics = state.get("augmented_topics")

    if topic_inventory:
        data = _to_serializable(topic_inventory)
        (out_dir / "topics.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if vuosikello:
        data = _to_serializable(vuosikello)
        (out_dir / "vuosikello.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    if augmented_topics:
        cleaned = _clean_augmented_topics(
            _to_serializable(augmented_topics)
        )
        (out_dir / "augmented_topics.json").write_text(
            json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return {
        "output_dir": str(out_dir),
        "current_step": "save_preparation",
    }
