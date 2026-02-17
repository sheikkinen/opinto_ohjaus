"""Render prompt templates using subject summaries.

Reads three one-pager summaries from state, renders 4 Jinja2 prompt
templates, and writes the resulting prompt YAML files and vars.yaml
to the target project directory. Also copies the pipeline graphs
so prompts_relative resolution works from the target directory.
"""

import shutil
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

# Templates live alongside this module's parent directory
_PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = _PROJECT_ROOT / "templates"

TEMPLATE_FILES = [
    "list-topics.yaml.j2",
    "extract-vuosikello.yaml.j2",
    "extract-and-augment-topic.yaml.j2",
    "generate-lesson-plan.yaml.j2",
]

GRAPH_FILES = [
    "prepare.yaml",
    "generate.yaml",
]


def render_templates(state: dict) -> dict:
    """Render prompt templates with subject summaries and write to project_dir.

    Reads:
        state.subject_summaries — dict with subject_profile, pedagogical_context, lesson_template
        state.project_dir — target project directory
        state.school_context, state.hours_per_module, state.lesson_duration — vars.yaml fields

    Writes:
        project_dir/prompts/*.yaml — 4 rendered prompt files
        project_dir/vars.yaml — pipeline variables including project_dir
    """
    project_dir = Path(state["project_dir"])
    summaries = state["subject_summaries"]

    # Handle Pydantic model or dict
    if hasattr(summaries, "model_dump"):
        summaries = summaries.model_dump()
    elif hasattr(summaries, "dict"):
        summaries = summaries.dict()

    # Render templates
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    prompts_dir = project_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    for template_name in TEMPLATE_FILES:
        template = env.get_template(template_name)
        rendered = template.render(**summaries)

        # Output filename: strip .j2 suffix
        out_name = template_name.removesuffix(".j2")
        (prompts_dir / out_name).write_text(rendered, encoding="utf-8")

    # Write vars.yaml
    vars_data = {
        "project_dir": str(project_dir),
        "school_context": state.get("school_context", ""),
        "hours_per_module": state.get("hours_per_module", 18),
        "lesson_duration": state.get("lesson_duration", 75),
    }
    vars_file = project_dir / "vars.yaml"
    vars_file.write_text(
        yaml.dump(vars_data, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )

    # Copy pipeline graphs so prompts_relative resolves from project_dir
    for graph_name in GRAPH_FILES:
        src = _PROJECT_ROOT / graph_name
        dst = project_dir / graph_name
        if src.exists():
            shutil.copy2(src, dst)

    return {
        "current_step": "render_templates",
        "output_dir": str(prompts_dir),
    }
