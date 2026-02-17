"""TDD tests for opinto-ohjaus pipeline.

Two-graph architecture:
  prepare.yaml — topics, vuosikello, augmentation → save to output/
  generate.yaml — load data → fan-out lesson plans per topic → save files

Tests run standalone from projects/opinto_ohjaus/ — not collected by root pytest.
"""

from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
GRAPH_YAML = PROJECT_DIR / "graph.yaml"  # legacy single graph
PREPARE_YAML = PROJECT_DIR / "prepare.yaml"
GENERATE_YAML = PROJECT_DIR / "generate.yaml"
RESEARCH_DOC = PROJECT_DIR / "lukion-opinto-ohjaus-opetussuunnitelma-ja-sisallot.md"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def research_doc_text():
    """Load the research document as text."""
    assert RESEARCH_DOC.exists(), f"Research doc not found: {RESEARCH_DOC}"
    return RESEARCH_DOC.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Graph YAML lints without errors
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_graph_lints():
    """Both pipeline graphs pass yamlgraph lint without errors."""
    from yamlgraph.linter import lint_graph

    for yaml_path in (PREPARE_YAML, GENERATE_YAML):
        assert yaml_path.exists(), f"Graph not found: {yaml_path}"
        result = lint_graph(yaml_path, project_root=Path.cwd())
        errors = [i for i in result.issues if i.severity == "error"]
        assert result.valid, f"{yaml_path.name} lint errors: {[e.message for e in errors]}"


# ---------------------------------------------------------------------------
# Test 2: Both graphs load and compile
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_prepare_graph_loads():
    """Prepare graph loads as valid GraphConfig."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(PREPARE_YAML)
    assert config.name == "opinto-ohjaus-prepare"
    assert "list_topics" in config.nodes
    assert "extract_vuosikello" in config.nodes
    assert "extract_and_augment" in config.nodes
    assert "save_preparation" in config.nodes


@pytest.mark.req("REQ-YG-069")
def test_generate_graph_loads():
    """Generate graph loads as valid GraphConfig."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(GENERATE_YAML)
    assert config.name == "opinto-ohjaus-generate"
    assert "load_data" in config.nodes
    assert "generate_lessons" in config.nodes
    assert "save_lessons" in config.nodes


# ---------------------------------------------------------------------------
# Test 3: Prepare graph — parallel start edges
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_prepare_parallel_start_edges():
    """list_topics and extract_vuosikello both start from START."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(PREPARE_YAML)
    start_targets = [e["to"] for e in config.edges if e["from"] == "START"]
    assert "list_topics" in start_targets
    assert "extract_vuosikello" in start_targets


# ---------------------------------------------------------------------------
# Test 4: Map nodes configured correctly
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_map_node_configs():
    """Map nodes have correct over/as/collect/type configuration."""
    from yamlgraph.graph_loader import load_graph_config

    # Prepare: extract_and_augment is map + agent
    prep = load_graph_config(PREPARE_YAML)
    ea = prep.nodes["extract_and_augment"]
    assert ea["type"] == "map"
    assert ea["over"] == "{state.topic_inventory.topics}"
    assert ea["as"] == "topic"
    assert ea["collect"] == "augmented_topics"
    assert ea["node"]["type"] == "agent"

    # Generate: generate_lessons is map + llm over lesson_items
    gen = load_graph_config(GENERATE_YAML)
    gl = gen.nodes["generate_lessons"]
    assert gl["type"] == "map"
    assert gl["over"] == "{state.lesson_items}"
    assert gl["as"] == "lesson"
    assert gl["collect"] == "lesson_plans"


# ---------------------------------------------------------------------------
# Test 5: Prompts load and parse
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_prompts_load():
    """All 4 prompts load without errors."""
    from yamlgraph.utils.prompts import load_prompt

    prompts_dir = PROJECT_DIR / "prompts"
    expected = [
        "list-topics",
        "extract-vuosikello",
        "extract-and-augment-topic",
        "generate-lesson-plan",
    ]
    for name in expected:
        config = load_prompt(name, prompts_dir=prompts_dir)
        assert config is not None, f"Prompt '{name}' failed to load"
        assert config.get("user") or config.get("template"), (
            f"Prompt '{name}' has no user/template section"
        )


# ---------------------------------------------------------------------------
# Test 6: list-topics prompt has structured output schema
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_list_topics_prompt_has_schema():
    """list-topics prompt defines a structured output schema."""
    from yamlgraph.utils.prompts import load_prompt

    config = load_prompt("list-topics", prompts_dir=PROJECT_DIR / "prompts")
    assert "schema" in config, "list-topics prompt must define schema for structured output"
    assert config["schema"]["name"] == "TopicInventory"


# ---------------------------------------------------------------------------
# Test 7: extract-vuosikello prompt has structured output schema
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_extract_vuosikello_prompt_has_schema():
    """extract-vuosikello prompt defines a structured output schema."""
    from yamlgraph.utils.prompts import load_prompt

    config = load_prompt("extract-vuosikello", prompts_dir=PROJECT_DIR / "prompts")
    assert "schema" in config, "extract-vuosikello prompt must define schema"
    assert config["schema"]["name"] == "Vuosikello"


# ---------------------------------------------------------------------------
# Test 8: Research document is available and non-empty
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_research_doc_exists(research_doc_text):
    """Research document exists and has substantial content."""
    assert len(research_doc_text) > 5000, "Research doc too short"
    assert "LOPS 2019" in research_doc_text or "LOPS" in research_doc_text
    assert "vuosikello" in research_doc_text.lower()
    assert "OP1" in research_doc_text
    assert "OP2" in research_doc_text


# ---------------------------------------------------------------------------
# Test 10: Data flow — edges form correct DAG
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_prepare_edge_dag():
    """Prepare edges: START→{list,vuosikello},
    list→augment→save, vuosikello→save→END."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(PREPARE_YAML)
    edge_set = {(e["from"], e["to"]) for e in config.edges}

    expected = {
        ("START", "list_topics"),
        ("START", "extract_vuosikello"),
        ("list_topics", "extract_and_augment"),
        ("extract_and_augment", "save_preparation"),
        ("extract_vuosikello", "save_preparation"),
        ("save_preparation", "END"),
    }
    assert expected == edge_set, f"Edge mismatch. Missing: {expected - edge_set}, Extra: {edge_set - expected}"


# ===========================================================================
# GENERALIZATION TESTS (plan-generalization-3.md)
# ===========================================================================

BOOTSTRAP_YAML = PROJECT_DIR / "bootstrap.yaml"
TEMPLATES_DIR = PROJECT_DIR / "templates"


# ---------------------------------------------------------------------------
# Test G1: Bootstrap graph lints
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_bootstrap_graph_lints():
    """Bootstrap graph passes yamlgraph lint without errors."""
    from yamlgraph.linter import lint_graph

    assert BOOTSTRAP_YAML.exists(), f"Graph not found: {BOOTSTRAP_YAML}"
    result = lint_graph(BOOTSTRAP_YAML, project_root=Path.cwd())
    errors = [i for i in result.issues if i.severity == "error"]
    assert result.valid, f"bootstrap.yaml lint errors: {[e.message for e in errors]}"


# ---------------------------------------------------------------------------
# Test G2: Bootstrap graph loads with correct nodes
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_bootstrap_graph_loads():
    """Bootstrap graph loads with summarize_subject and render_templates nodes."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(BOOTSTRAP_YAML)
    assert "summarize_subject" in config.nodes
    assert "render_templates" in config.nodes


# ---------------------------------------------------------------------------
# Test G3: Bootstrap edge DAG
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_bootstrap_edge_dag():
    """Bootstrap edges: START→summarize_subject→render_templates→END."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(BOOTSTRAP_YAML)
    edge_set = {(e["from"], e["to"]) for e in config.edges}

    expected = {
        ("START", "summarize_subject"),
        ("summarize_subject", "render_templates"),
        ("render_templates", "END"),
    }
    assert expected == edge_set, (
        f"Edge mismatch. Missing: {expected - edge_set}, Extra: {edge_set - expected}"
    )


# ---------------------------------------------------------------------------
# Test G4: summarize-subject prompt has SubjectSummaries schema
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_summarize_subject_prompt_has_schema():
    """summarize-subject prompt defines SubjectSummaries schema."""
    from yamlgraph.utils.prompts import load_prompt

    config = load_prompt("summarize-subject", prompts_dir=PROJECT_DIR / "prompts")
    assert "schema" in config, "summarize-subject prompt must define schema"
    assert config["schema"]["name"] == "SubjectSummaries"
    fields = config["schema"]["fields"]
    assert "subject_profile" in fields
    assert "pedagogical_context" in fields
    assert "lesson_template" in fields


# ---------------------------------------------------------------------------
# Test G5: Template files exist
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_templates_exist():
    """All 4 Jinja2 template files exist in templates/."""
    expected = [
        "list-topics.yaml.j2",
        "extract-vuosikello.yaml.j2",
        "extract-and-augment-topic.yaml.j2",
        "generate-lesson-plan.yaml.j2",
    ]
    for name in expected:
        path = TEMPLATES_DIR / name
        assert path.exists(), f"Template not found: {path}"


# ---------------------------------------------------------------------------
# Test G6: Template rendering produces valid YAML
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_template_rendering():
    """Rendering templates with mock summaries produces valid YAML."""
    import yaml

    from jinja2 import Environment, FileSystemLoader

    assert TEMPLATES_DIR.exists(), f"Templates dir not found: {TEMPLATES_DIR}"

    mock_summaries = {
        "subject_profile": "Olet lukion terveystiedon opettaja.\n\nTE1: Terveys voimavarana.",
        "pedagogical_context": "Lähteet:\n- thl.fi\n- oph.fi",
        "lesson_template": "### Tavoitteet\n### Tunnin kulku\n### Arviointi (4-10)",
    }

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    for template_name in env.list_templates():
        if not template_name.endswith(".yaml.j2"):
            continue
        template = env.get_template(template_name)
        rendered = template.render(**mock_summaries)
        # Must parse as valid YAML
        parsed = yaml.safe_load(rendered)
        assert parsed is not None, f"Template {template_name} rendered to empty YAML"
        assert "system" in parsed or "user" in parsed, (
            f"Template {template_name} missing system/user key"
        )


# ---------------------------------------------------------------------------
# Test G7: render_templates node exists and is callable
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_render_templates_node():
    """render_templates Python function exists and is importable."""
    from projects.opinto_ohjaus.nodes.render_templates import render_templates

    assert callable(render_templates)


# ---------------------------------------------------------------------------
# Test G8: render_templates produces files
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_render_templates_writes_files(tmp_path):
    """render_templates writes prompts and vars.yaml to project_dir."""
    import yaml

    from projects.opinto_ohjaus.nodes.render_templates import render_templates

    state = {
        "subject_summaries": {
            "subject_profile": "Olet lukion terveystiedon opettaja.",
            "pedagogical_context": "Lähteet: thl.fi, oph.fi",
            "lesson_template": "### Tavoitteet\n### Tunnin kulku",
        },
        "project_dir": str(tmp_path),
        "school_context": "Testikoulu",
        "hours_per_module": 18,
        "lesson_duration": 75,
    }

    result = render_templates(state)

    # Must return state update
    assert "output_dir" in result or "current_step" in result

    # Must create prompts
    prompts_dir = tmp_path / "prompts"
    assert prompts_dir.exists(), "prompts/ dir not created"
    for name in ["list-topics.yaml", "extract-vuosikello.yaml",
                 "extract-and-augment-topic.yaml", "generate-lesson-plan.yaml"]:
        prompt_file = prompts_dir / name
        assert prompt_file.exists(), f"Prompt not created: {name}"
        parsed = yaml.safe_load(prompt_file.read_text(encoding="utf-8"))
        assert parsed is not None, f"Prompt {name} is empty"

    # Must create vars.yaml
    vars_file = tmp_path / "vars.yaml"
    assert vars_file.exists(), "vars.yaml not created"
    vars_data = yaml.safe_load(vars_file.read_text(encoding="utf-8"))
    assert vars_data["project_dir"] == str(tmp_path)


# ---------------------------------------------------------------------------
# Test G9: Parameterized project_dir in load_data
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_load_data_uses_project_dir(tmp_path):
    """load_data reads from project_dir instead of hardcoded path."""
    import json

    from projects.opinto_ohjaus.nodes.load_data import load_data

    module = "test"
    out_dir = tmp_path / "output" / module
    out_dir.mkdir(parents=True)

    topics = {"topics": [{"id": "t1", "title": "Test", "one_line_description": "desc", "module": "TEST"}]}
    augmented = ["content for t1"]
    vuosikello = {"slots": [{"year": 1, "semester": "syksy", "module": "TEST", "focus_areas": [], "key_activities": []}]}

    (out_dir / "topics.json").write_text(json.dumps(topics), encoding="utf-8")
    (out_dir / "augmented_topics.json").write_text(json.dumps(augmented), encoding="utf-8")
    (out_dir / "vuosikello.json").write_text(json.dumps(vuosikello), encoding="utf-8")

    state = {"module": module, "project_dir": str(tmp_path), "lesson_duration": 75}
    result = load_data(state)
    assert len(result["lesson_items"]) == 1
    assert result["lesson_items"][0]["title"] == "Test"


# ---------------------------------------------------------------------------
# Test G10: Parameterized project_dir in save_preparation
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_save_preparation_uses_project_dir(tmp_path):
    """save_preparation writes to project_dir instead of hardcoded path."""
    from projects.opinto_ohjaus.nodes.save_preparation import save_preparation

    state = {
        "module": "test",
        "project_dir": str(tmp_path),
        "topic_inventory": {"topics": [{"id": "t1", "title": "Test"}]},
        "vuosikello": {"slots": []},
        "augmented_topics": ["content"],
    }
    result = save_preparation(state)
    assert (tmp_path / "output" / "test" / "topics.json").exists()


# ---------------------------------------------------------------------------
# Test G11: Parameterized project_dir in save_lessons
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_save_lessons_uses_project_dir(tmp_path):
    """save_lessons writes to project_dir instead of hardcoded path."""
    from projects.opinto_ohjaus.nodes.save_lessons import save_lessons

    state = {
        "module": "test",
        "project_dir": str(tmp_path),
        "lesson_plans": ["# Test Lesson\n\nContent here."],
        "lesson_items": [{"title": "Test Lesson"}],
    }
    result = save_lessons(state)
    lessons_dir = tmp_path / "output" / "test" / "lessons"
    assert lessons_dir.exists()
    assert len(list(lessons_dir.glob("*.md"))) >= 1


# ---------------------------------------------------------------------------
# Test G12-G14: Missing project_dir raises KeyError (fail-fast contract)
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_load_data_fails_without_project_dir():
    """load_data raises KeyError when project_dir is missing from state."""
    from projects.opinto_ohjaus.nodes.load_data import load_data

    with pytest.raises(KeyError, match="project_dir"):
        load_data({"module": "test"})


@pytest.mark.req("REQ-YG-069")
def test_save_preparation_fails_without_project_dir():
    """save_preparation raises KeyError when project_dir is missing from state."""
    from projects.opinto_ohjaus.nodes.save_preparation import save_preparation

    with pytest.raises(KeyError, match="project_dir"):
        save_preparation({"module": "test"})


@pytest.mark.req("REQ-YG-069")
def test_save_lessons_fails_without_project_dir():
    """save_lessons raises KeyError when project_dir is missing from state."""
    from projects.opinto_ohjaus.nodes.save_lessons import save_lessons

    with pytest.raises(KeyError, match="project_dir"):
        save_lessons({"module": "test"})


# ---------------------------------------------------------------------------
# Test G15: vars.yaml includes project_dir
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_vars_yaml_includes_project_dir():
    """vars.yaml must include project_dir for pipeline execution."""
    import yaml

    vars_file = PROJECT_DIR / "vars.yaml"
    data = yaml.safe_load(vars_file.read_text(encoding="utf-8"))
    assert "project_dir" in data, "vars.yaml must include project_dir"


@pytest.mark.req("REQ-YG-069")
def test_generate_edge_dag():
    """Generate edges: START→load→generate→save→END."""
    from yamlgraph.graph_loader import load_graph_config

    config = load_graph_config(GENERATE_YAML)
    edge_set = {(e["from"], e["to"]) for e in config.edges}

    expected = {
        ("START", "load_data"),
        ("load_data", "generate_lessons"),
        ("generate_lessons", "save_lessons"),
        ("save_lessons", "END"),
    }
    assert expected == edge_set, f"Edge mismatch. Missing: {expected - edge_set}, Extra: {edge_set - expected}"
