"""Save generated lesson plans as individual markdown files.

Writes each lesson plan to output/{module}/lessons/NN-title.md
and a summary index file. Handles map output format
({'_map_index': N, 'value': '...'}) and strips signatures.
"""

import re
from pathlib import Path


def _slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:60]


def _unwrap_map_value(item: object) -> str:
    """Extract plain text from a map output item.

    Handles: str, {'_map_index': N, 'value': str|list[{'text': str}]}
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        value = item.get("value", item)
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            texts = []
            for block in value:
                if isinstance(block, dict):
                    texts.append(block.get("text", ""))
                elif isinstance(block, str):
                    texts.append(block)
            return "\n".join(t for t in texts if t)
    return str(item)


def _extract_title(lesson_plan: str) -> str:
    """Extract title from lesson plan markdown.

    Looks for '## Tunti N — Title' first (standard format),
    then falls back to first # or ## heading.
    """
    for line in lesson_plan.split("\n"):
        line = line.strip()
        m = re.match(r"^##\s+Tunti\s+\d+\s*[—–-]\s*(.+)", line)
        if m:
            return m.group(1).strip()
    for line in lesson_plan.split("\n"):
        line = line.strip()
        if line.startswith("## "):
            return line[3:].strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "untitled"


def save_lessons(state: dict) -> dict:
    """Save lesson plans as individual markdown files.

    Writes:
      - output/{module}/lessons/01-slug.md, 02-slug.md, ...
      - output/{module}/lessons/index.md (summary)
    """
    module = state.get("module", "unknown").lower()
    out_dir = Path("projects/opinto_ohjaus/output") / module / "lessons"
    # Clean previous run
    if out_dir.exists():
        for f in out_dir.glob("*.md"):
            f.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)

    lesson_plans = state.get("lesson_plans", [])
    lesson_items = state.get("lesson_items", [])

    index_lines = [
        f"# {module.upper()} – Tuntisuunnitelmat\n",
        f"Yhteensä {len(lesson_plans)} tuntisuunnitelmaa.\n",
    ]

    for i, plan in enumerate(lesson_plans):
        if not plan:
            continue

        content = _unwrap_map_value(plan)

        # Get title from lesson_items metadata or extract from content
        title = ""
        if i < len(lesson_items):
            title = lesson_items[i].get("title", "") if isinstance(lesson_items[i], dict) else ""
        if not title:
            title = _extract_title(content)

        slug = _slugify(title) or f"lesson-{i + 1}"
        filename = f"{i + 1:02d}-{slug}.md"

        (out_dir / filename).write_text(content, encoding="utf-8")

        index_lines.append(f"- [{i + 1:02d}. {title}]({filename})")

    (out_dir / "index.md").write_text("\n".join(index_lines), encoding="utf-8")

    return {
        "output_dir": str(out_dir),
        "current_step": "save_lessons",
    }
