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
    """All 5 prompts load without errors."""
    from yamlgraph.utils.prompts import load_prompt

    prompts_dir = PROJECT_DIR / "prompts"
    expected = [
        "list-topics",
        "extract-vuosikello",
        "extract-and-augment-topic",
        "split-into-hours",
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
# Test 8: split-into-hours prompt has structured output schema
# ---------------------------------------------------------------------------


@pytest.mark.req("REQ-YG-069")
def test_split_into_hours_prompt_has_schema():
    """split-into-hours prompt defines a structured output schema."""
    from yamlgraph.utils.prompts import load_prompt

    config = load_prompt("split-into-hours", prompts_dir=PROJECT_DIR / "prompts")
    assert "schema" in config, "split-into-hours prompt must define schema"
    assert config["schema"]["name"] == "LessonMapping"


# ---------------------------------------------------------------------------
# Test 9: Research document is available and non-empty
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
