# Plan: Generalize Lesson Plan Pipeline for Lukio

## Problem

The opinto-ohjaus pipeline produces high-quality 75-min lesson plans (one-pagers)
for Finnish lukio. It works: 25 lessons for OP1, 19 for OP2, all generated with
claude-sonnet-4-5. The question is how to replicate this for other lukio subjects
(terveystieto, historia, matematiikka, etc.).

**What's subject-specific:**
- 4 YAML prompts — expert role, module definitions, assessment model, lesson
  template sections, reference sources (oph.fi, opintopolku.fi, etc.)
- vars.yaml — module code, school context, hours, duration

**What's generic (shared across subjects):**
- 2 graph YAMLs (prepare.yaml, generate.yaml) — already parameterized
- 3 Python tool nodes — load_data, save_preparation, save_lessons (paths
  hardcoded but trivially parameterizable via `project_dir`)
- Architecture pattern — prepare (extract + augment + websearch) → generate
  (fan-out per topic)

**What the original build actually cost:**
- ~30 min writing initial prompts and vars
- ~4 hours debugging: race conditions, schema errors, rate limits, map wrapper
  formats, signature bloat, fan-out redesign, architecture split to two graphs
- The debugging was about YAMLGraph mechanics, not domain knowledge

## Goal

Enable a second lukio subject (e.g. terveystieto) to reach working lesson plans
with significantly less effort than the original ~4.5 hours. The realistic target
is not zero-effort ("just provide a research doc") but reduced cold-start time
for domain-specific artifacts, while acknowledging that iterative debugging
remains necessary.

## Options

Three levels of generalization were considered:

### Option A: Example project — Document the pattern

Ship opinto-ohjaus as a reference example with a "How to add a new subject" guide.
Developer manually rewrites prompts and vars for each new subject.

- **Effort**: ~30 min (only documentation)
- **Reuse**: Low — developer must understand the pipeline deeply to replicate it
- **Maintenance**: None beyond the README already written
- **When**: The pipeline is used for one or two subjects, by the original author

### Option B: Bootstrap graph — `yamlgraph graph bootstrap` (recommended)

A bootstrap graph reads a research document + basic params → produces complete
domain-tuned prompts and vars.yaml. The LLM does what Claude did in the original
session: read a curriculum document and author the 4 prompt files.

- **Effort**: ~2.5 hours (this plan's Phase 0–2)
- **Reuse**: High — any Finnish lukio subject with a Gemini Deep Research doc
- **Maintenance**: Bootstrap prompt + save_bootstrap.py
- **When**: Multiple subjects planned, or other users want to replicate the pipeline
- **Key insight**: The bootstrap prompt doesn't need few-shot lesson plans. It needs
  the YAMLGraph format specs (`reference/prompt-yaml.md`, `reference/graph-yaml.md`)
  plus the existing opinto-ohjaus prompts as structural examples. The LLM bridges
  format knowledge + domain content.

### Option C: Core YAMLGraph feature — `yamlgraph graph bootstrap <domain-doc>`

Generalize beyond lesson plans: a framework-level command that reads any domain
document + YAMLGraph format specs → generates a complete project scaffold
(graph.yaml, prompts/, nodes/, vars.yaml, tests/).

- **Effort**: ~1–2 weeks (framework design, CLI, prompt engineering, testing)
- **Reuse**: Universal — any YAML-first LLM pipeline, not just lesson plans
- **Maintenance**: Core framework feature, needs documentation, CI, versioning
- **When**: Bootstrap pattern proves valuable and demand exists beyond education
- **Risk**: Over-engineering — the generated scaffolds may need heavy editing,
  negating the automation benefit for non-standard pipelines

### Option D: Use `examples/yamlgraph_gen` as bootstrap engine

The `yamlgraph_gen` example is a YAMLGraph pipeline that generates other
YAMLGraph pipelines from natural language. It already handles:
- Pattern classification (router, map, agent, etc.)
- Snippet-based graph assembly from a composable library
- Prompt file generation for each node
- Python tool generation (`generate_tools` node)
- File writing, structure validation, and linting

The opinto-ohjaus bootstrap becomes a specialized invocation:

```bash
python examples/yamlgraph_gen/run_generator.py \
  "Create a Finnish lukio lesson plan pipeline that reads a curriculum
   research document, extracts topics, augments with websearch, and
   generates per-topic lesson plans as markdown files" \
  -o projects/terveystieto
```

- **Effort**: ~1–2 hours (test the existing generator with the lesson plan use case,
  possibly add a snippet for the prepare→generate two-phase pattern)
- **Reuse**: High — leverages an existing, tested pipeline (60 unit + 5 e2e tests)
- **Maintenance**: Maintained as part of yamlgraph_gen, not a separate artifact
- **When**: The generator already handles the complexity of this use case
- **Gap**: Domain knowledge injection — yamlgraph_gen works from a natural language
  request, but doesn't currently accept a research document as context.
  The research doc is too large for a single request string; it would need
  a `--var research_doc=@file.md` style injection into the generator's state.
- **Implication**: Invalidates the "Python boundary" constraint stated earlier.
  `yamlgraph_gen` already generates Python tools — so a full scaffold generator
  is not outside YAMLGraph's demonstrated capability.

### Constraint: The iteration gap

**Single-shot generation ≠ working pipeline.** The opinto-ohjaus session is
direct evidence: it took ~15 iterations to produce a working pipeline. Problems
encountered at runtime that no generator could predict upfront:

| Iteration | Problem | Root cause |
|-----------|---------|------------|
| 1 | Map node crashes | `over:` dot-notation wrong |
| 2 | Tool not found | `tools.websearch` missing from graph |
| 3 | Race condition | Fan-in fired on first predecessor |
| 4 | Architecture split | Single graph → two graphs |
| 5 | Signature bloat | 53% of data was `extras.signature` |
| 6 | Rate limit 429 | All topics in one LLM call |
| 7 | Fan-out redesign | Per-topic map over `lesson_items` |
| 8 | Schema error | `list[dict]` → `list[Any]` |
| 9+ | Map wrapper format | `{_map_index, value}` unwrapping |

The real value was the **iterative correction loop**: run → read error log →
diagnose root cause → targeted fix → run again. This is a human + LLM agent
debugging session, not a generation problem.

**Implications for each option:**

- **Option A** (document): Honest — acknowledges iteration is manual work
- **Option B** (bootstrap): Generates 4 prompts, but they'll likely need 3–5
  fix cycles before producing good output. Bootstrap saves the first 30 min
  of a 4-hour process.
- **Option C** (core feature): Same gap — generated scaffolds are starting points
- **Option D** (yamlgraph_gen): Generates the scaffold, but yamlgraph_gen has
  not been tested with real production use cases. The generator itself hasn't
  been through the iterative correction loop. The easy part (scaffold) is
  automated; the hard part (debugging) remains manual.

**The honest assessment**: None of the options eliminate the iteration loop.
They accelerate the cold start (scaffold + initial prompts) but don't address
the 80% of effort that goes into debugging and refinement. The most impactful
improvement would be better error messages and diagnostic tooling in YAMLGraph
itself — making each iteration cycle faster, rather than trying to skip them.

### Decision

**Option B** — bootstrap graph at project level, with realistic expectations.
The bootstrap saves ~30 min of initial prompt authoring per subject. The remaining
~2 hours of debugging and refinement remain a human + agent task.

**Option D deferred** — yamlgraph_gen is theoretically capable but unproven in
practice. Before recommending it, it needs to be validated with a real end-to-end
use case. The lesson plan pipeline could be that test case — but that's a
separate investigation, not a prerequisite for this project's generalization.

## Current Flow

```
Human provides research query → Gemini Deep Research → research_doc.md
                                                            │
Claude reads doc, authors:                                  │
├── 4 prompts (domain terms hardcoded)                      │
├── 3 Python nodes (paths hardcoded)                        │
├── vars.yaml (4 fields)                                    │
└── graphs (already generic)                                │
                                                            │
prepare.yaml (research_doc) → JSON files → generate.yaml → lessons/*.md
```

**The manual step is Claude reading the research doc and producing domain-specific prompts.** The prompts ARE the domain knowledge — not intermediate vars that get recombined. This is an LLM task that can be automated.

## Target Flow

```
research_doc.md + basic params
        │
        ▼
  bootstrap.yaml ──→ vars.yaml (basic fields)
                 ──→ prompts/*.yaml (4 complete domain-tuned prompt files)
        │
   Human review (tweak prompts/vars if needed)
        │
        ▼
  prepare.yaml ──→ JSON files ──→ generate.yaml ──→ lessons/*.md
```

## Implementation

### Phase 0: Golden file baseline (10 min)

Save current OP1 lesson 01 as regression baseline before any changes.

```bash
mkdir -p tests/golden
cp output/op1/lessons/01-siirtyminen-lukiokoulutukseen.md tests/golden/
```

After generalization, regenerate and diff against this file to verify quality.

### Phase 1: Bootstrap graph — generate prompts + vars (2h)

The bootstrap graph reads a research document and outputs **complete, domain-tuned prompt files** plus a `vars.yaml`. No intermediate parameterization step — the prompts ARE the domain knowledge. The bootstrap LLM generates them directly, just as Claude did in the original session.

#### 1.1 Fix hardcoded paths in Python nodes (20 min)

Prerequisite: make nodes generic before bootstrap can target a new project dir.

**load_data.py** line 43:
```python
# Current
out_dir = Path("projects/opinto_ohjaus/output") / module
# New
out_dir = Path(state.get("project_dir", ".")) / "output" / module
```

**load_data.py** line 31:
```python
# Current
SESSION_TYPES = ["luokkaopetus", "työpaja", "pienryhmä", "vierailu", "verkko"]
# New
session_types = state.get("session_types", ["luokkaopetus", "työpaja", "pienryhmä"])
```

**save_preparation.py** line 68:
```python
# Current
out_dir = Path("projects/opinto_ohjaus/output") / module
# New
out_dir = Path(state.get("project_dir", ".")) / "output" / module
```

**save_lessons.py** line 75:
```python
# Current
out_dir = Path("projects/opinto_ohjaus/output") / module / "lessons"
# New
out_dir = Path(state.get("project_dir", ".")) / "output" / module / "lessons"
```

Add `project_dir: str` to `state:` in both `prepare.yaml` and `generate.yaml`.
Add `project_dir` to `vars.yaml`.

#### 1.2 bootstrap.yaml (30 min)

```yaml
name: lesson-plan-bootstrap
version: "1.0"
description: >
  Read a research document and generate domain-tuned vars.yaml
  and 4 prompt files for the lesson plan pipeline.

prompts_relative: true
prompts_dir: prompts

defaults:
  temperature: 0.3

tools:
  save_bootstrap:
    type: python
    module: projects.opinto_ohjaus.nodes.save_bootstrap
    function: save_bootstrap
    description: "Save generated vars.yaml and prompt files to project dir"

state:
  research_doc: str
  project_dir: str
  school_context: str
  hours_per_module: int
  lesson_duration: int

nodes:
  bootstrap:
    type: llm
    prompt: bootstrap
    variables:
      research_doc: "{state.research_doc}"
    state_key: bootstrap_output

  save_bootstrap:
    type: python
    tool: save_bootstrap
    state_key: output_path

edges:
  - from: START
    to: bootstrap
  - from: bootstrap
    to: save_bootstrap
  - from: save_bootstrap
    to: END
```

#### 1.3 prompts/bootstrap.yaml — The meta-prompt (60 min)

This is the critical artifact. It encodes what Claude did when reading the research doc:
read a curriculum document → produce complete domain-specific YAML prompt files.

The prompt provides the existing opinto-ohjaus prompts as **examples** so the LLM
understands the exact format, structure, and quality bar.

```yaml
schema:
  name: BootstrapOutput
  fields:
    vars_yaml:
      type: str
      description: "Complete vars.yaml content as YAML string"
    prompt_list_topics:
      type: str
      description: "Complete list-topics.yaml prompt file content"
    prompt_extract_vuosikello:
      type: str
      description: "Complete extract-vuosikello.yaml prompt file content"
    prompt_extract_and_augment:
      type: str
      description: "Complete extract-and-augment-topic.yaml prompt file content"
    prompt_generate_lesson_plan:
      type: str
      description: "Complete generate-lesson-plan.yaml prompt file content"

system: |
  Olet suomalaisen lukiokoulutuksen opetussuunnitelmien asiantuntija ja
  tuntisuunnitelmageneraattorin konfiguroija.

  Tehtäväsi on lukea annettu tutkimusdokumentti ja tuottaa:
  1. vars.yaml — ainekohtaiset muuttujat
  2. Neljä prompt-tiedostoa — valmiit, domain-tuned YAML-promptit

  ANALYSOI dokumentista:
  - Mikä oppiaine? Mikä asiantuntijarooli?
  - Mitkä moduulit (koodit, nimet, kuvaukset)?
  - Miten arvioidaan?
  - Mitkä verkkosivustot keskeisiä? (oph.fi aina mukana)
  - Mitkä laaja-alaisen osaamisen alueet relevantteja?
  - Ketkä yhteistyökumppanit?
  - Mitkä opetusmenetelmät sopivat?
  - Mitä osioita tuntisuunnitelmassa?

  TUOTA neljä prompt-tiedostoa seuraavissa formaateissa:

  [Tähän tulee opinto-ohjaus-promptit esimerkkinä, leikkaus pituuden vuoksi.
   Todellinen prompt sisältää nykyiset 4 promptia esimerkkeinä ja ohjeet
   muokata ne uudelle aineelle.]

  TÄRKEÄÄ:
  - Promptien tulee olla kokonaisia, toimivia YAML-tiedostoja
  - Käytä samaa rakennetta kuin esimerkeissä
  - Muokkaa vain ainekohtainen sisältö, säilytä Jinja2-muuttujat
  - Palauta kaikki suomeksi

user: |
  Lue seuraava tutkimusdokumentti ja tuota tuntisuunnitelmageneraattorin
  konfiguraatio (vars.yaml + 4 prompt-tiedostoa).

  TUTKIMUSDOKUMENTTI:
  {{ research_doc }}
```

#### 1.4 nodes/save_bootstrap.py (30 min)

```python
"""Save bootstrap output: vars.yaml + 4 prompt files."""

from pathlib import Path

def save_bootstrap(state: dict) -> dict:
    """Write vars.yaml and prompt files to project dir."""
    output = state.get("bootstrap_output", {})
    project_dir = Path(state.get("project_dir", "."))

    # Create directories
    prompts_dir = project_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # Write vars.yaml (append runtime fields)
    vars_content = output.get("vars_yaml", "")
    vars_content += f"\nproject_dir: {project_dir}\n"
    vars_content += f"school_context: \"{state.get('school_context', '')}\"\n"
    vars_content += f"hours_per_module: {state.get('hours_per_module', 18)}\n"
    vars_content += f"lesson_duration: {state.get('lesson_duration', 75)}\n"
    (project_dir / "vars.yaml").write_text(vars_content, encoding="utf-8")

    # Write 4 prompt files
    prompt_map = {
        "list-topics.yaml": output.get("prompt_list_topics", ""),
        "extract-vuosikello.yaml": output.get("prompt_extract_vuosikello", ""),
        "extract-and-augment-topic.yaml": output.get("prompt_extract_and_augment", ""),
        "generate-lesson-plan.yaml": output.get("prompt_generate_lesson_plan", ""),
    }
    for filename, content in prompt_map.items():
        if content:
            (prompts_dir / filename).write_text(content, encoding="utf-8")

    return {"output_path": str(project_dir)}
```

#### 1.5 Tests (20 min)

- Bootstrap graph lints and loads
- Bootstrap prompt file exists and valid YAML
- Existing opinto-ohjaus tests still pass (nodes use project_dir defaulting to current)
- Golden file diff after regeneration

### Phase 2: Verify with second subject (30 min runtime + review)

Test the bootstrap with a real second subject to prove generalization.

```bash
# 1. Gemini Deep Research for terveystieto
# Query: "terveystieto, lukion opetussuunnitelma LOPS 2019, moduulit ja sisällöt"
# Save as: projects/terveystieto/terveystieto-ops.md

# 2. Bootstrap
mkdir -p projects/terveystieto
yamlgraph graph run bootstrap.yaml \
  --var research_doc=@projects/terveystieto/terveystieto-ops.md \
  --var project_dir=projects/terveystieto \
  --var school_context="Keskikokoinen lukio, noin 300 opiskelijaa" \
  --var hours_per_module=18 \
  --var lesson_duration=75

# 3. Human review
cat projects/terveystieto/vars.yaml
cat projects/terveystieto/prompts/*.yaml

# 4. Prepare + Generate
yamlgraph graph run prepare.yaml \
  --var-file projects/terveystieto/vars.yaml \
  --var research_doc=@projects/terveystieto/terveystieto-ops.md

PROVIDER=anthropic yamlgraph graph run generate.yaml \
  --var-file projects/terveystieto/vars.yaml

# 5. Review output quality
cat projects/terveystieto/output/TE1/lessons/index.md
```

## Summary

| Phase | What | Effort | Result |
|-------|------|--------|--------|
| 0 | Golden file baseline | 10 min | Regression reference |
| 1 | Bootstrap graph + fix paths | 2h | New subject = one LLM call + review |
| 2 | Verify with terveystieto | 30 min + review | Generalization proven |

**Total: ~2.5 hours**

## Risks

- **Bootstrap prompt quality** — The meta-prompt must produce prompts as good as Claude hand-wrote. Mitigate: include opinto-ohjaus prompts as few-shot examples in the bootstrap prompt.
- **Output format fragility** — LLM-generated YAML prompt files may have syntax errors. Mitigate: `save_bootstrap.py` validates YAML before writing; lint generated prompts.
- **Token limits** — Bootstrap prompt includes research doc + 4 example prompts = large context. Mitigate: use claude-sonnet-4-5 (200K context).

## Decision: Skip parameterization

The original Phase 1 (parameterize prompts with `{{ variables }}`) was an unnecessary intermediate step.
Generating prompts directly is simpler and produces better results — the LLM can make holistic
domain-specific choices (which sections, what tone, what depth) that can't be captured in
10 configuration variables. The prompts are the product, not an intermediate form.
