# Plan: Generalized Lukio Lesson Plan Pipeline

## In / Out

**In:** Gemini Deep Research document (markdown) for any Finnish lukio subject
**Out:** Per-topic one-pager lesson plans (75 min) as markdown files

## Key insight

The original prompts contain domain knowledge at three levels:

1. **Subject profile** — expert role, subject name, module codes/names/descriptions
2. **Pedagogical context** — sources, collaboration partners, competence areas, methods
3. **Lesson template** — section structure, assessment model, special themes

These are naturally documents, not structured fields. The LLM summarizes the
research doc into three one-pagers. A Python node slots them into prompt
templates as text blocks. No schema mapping, no field iteration.

## Approach: summarize + slot

```
research_doc.md + basic params
        │
        ▼
┌──────────────────────────────────────────────┐
│  bootstrap.yaml  (NEW)                       │
│  Step 1: Summarize into 3 one-pagers (LLM)   │
│  Step 2: Slot into prompt templates (Python)  │
│  → project_dir/vars.yaml                     │
│  → project_dir/prompts/*.yaml                │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│  prepare.yaml  (EXISTING, parameterized)     │
└──────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────┐
│  generate.yaml  (EXISTING, parameterized)    │
└──────────────────────────────────────────────┘
```

### Step 1: Summarize into 3 one-pagers

Single LLM call with structured output. Any model with structured output
support works (gemini-flash, haiku, sonnet).

**Required input:**
- `research_doc` — the Gemini Deep Research markdown document

**Required output** — `SubjectSummaries` schema with 3 text fields:

```yaml
schema:
  name: SubjectSummaries
  fields:
    subject_profile:
      type: str
      description: >
        Aineprofiili moduuleittain. Sisältää:
        - Oppiaineen nimi
        - Asiantuntijarooli (esim. "lukion terveystiedon opettaja")
        - Jokainen moduuli: koodi, nimi, kuvaus, keskeiset aiheet
          (esim. "TE1: Terveys voimavarana — terveyttä edistävät tekijät...")
    pedagogical_context:
      type: str
      description: >
        Pedagoginen konteksti. Sisältää:
        - Keskeiset verkkolähteet URL-listana (oph.fi aina mukana)
        - Yhteistyötahot (esim. terveydenhoitaja, TE-toimisto)
        - Laaja-alaisen osaamisen alueet
        - Sopivat opetusmenetelmät
    lesson_template:
      type: str
      description: >
        Tuntisuunnitelman rakenne markdown-muodossa. Sisältää:
        - Osioiden nimet ja kuvaukset (esim. Tavoitteet, Tunnin kulku, Menetelmät)
        - Arviointimalli (esim. "suoritusmerkintä S/H" tai "numeroarviointi 4-10")
        - Aineen erityisnäkökulma (esim. "Koko koulu ohjaa")
```

The schema descriptions are the contract. They tell the LLM what structure
and content each one-pager must contain.

### Step 2: Slot into prompt templates

Python node reads the three one-pagers and renders 4 Jinja2 templates.
Templates live in `templates/`:

```
templates/
├── list-topics.yaml.j2
├── extract-vuosikello.yaml.j2
├── extract-and-augment-topic.yaml.j2
└── generate-lesson-plan.yaml.j2
```

Each template uses `{{ subject_profile }}`, `{{ pedagogical_context }}`,
`{{ lesson_template }}` as text block insertions:

```yaml
# templates/generate-lesson-plan.yaml.j2
system: |
  {{ subject_profile }}

  Laadi yksisivuinen (one-pager) tuntisuunnitelma.

  {{ lesson_template }}

  {{ pedagogical_context }}
```

No field iteration. No schema mapping. Three text blocks, four templates.
Templates are pre-validated YAML — format risk is zero.

## Template / one-pager pairs

### list-topics.yaml.j2 ← subject_profile

**Purpose:** Identify all teaching topics from the research document for one module.

**One-pager provides:**
- Subject name and expert role (system prompt identity)
- Module codes, names, and descriptions (e.g. "OP1: Minä opiskelijana —
  lukioon kiinnittyminen, opiskelutaidot, HOPS")
- The `{% if module %}` conditional content: what to focus on per module

**Template keeps:**
- Schema definition (`TopicInventory` with `topics: list[Any]`)
- Pipeline variables: `{{ module }}`, `{{ research_doc }}`
- Instruction structure: "tunnista 15-25 aihetta", "palauta id, title, ..."

**Key:** The subject profile must include per-module descriptions so the
template can inject the right context when `{{ module }}` is set.

### extract-vuosikello.yaml.j2 ← subject_profile

**Purpose:** Extract the subject's yearly schedule from the research document.

**One-pager provides:**
- Expert role
- Module codes (to map slots to modules)

**Template keeps:**
- Schema definition (`Vuosikello` with `slots: list[Any]`)
- The 3-year × 2-semester structure (generic for all lukio subjects)
- Pipeline variable: `{{ research_doc }}`
- Instruction: "poimi vain se, mikä tutkimusdokumentissa kuvataan"

**Key:** This is the most generic template. Only the expert role and module
codes change between subjects. The vuosikello structure is universal.

### extract-and-augment-topic.yaml.j2 ← subject_profile + pedagogical_context

**Purpose:** Enrich each topic with research doc content and web search results.

**One-pager provides:**
- `subject_profile`: expert role, subject name
- `pedagogical_context`: priority web sources (URL list), laaja-alainen
  osaaminen categories, collaboration partners

**Template keeps:**
- Pipeline variables: `{{ topic.title }}`, `{{ topic.module }}`,
  `{{ topic.research_doc_sections }}`, `{{ research_doc }}`
- Output structure: title, summary, source_refs, web_sources, key_content
- Instruction to search the web and combine with document content

**Key:** The pedagogical context replaces hardcoded source lists (oph.fi,
opintopolku.fi) and collaboration categories. Different subjects have
different priority sources (e.g. THL for terveystieto, Arkisto for historia).

### generate-lesson-plan.yaml.j2 ← subject_profile + pedagogical_context + lesson_template

**Purpose:** Generate a complete one-pager lesson plan for one topic.

**One-pager provides:**
- `subject_profile`: expert role, subject header ("# OPINTO-OHJAUS" → "# TERVEYSTIETO")
- `pedagogical_context`: sources, collaboration partners for the lesson
- `lesson_template`: section structure (Tavoitteet, Tunnin kulku, Menetelmät...),
  assessment model ("suoritusmerkintä S/H" vs "numeroarviointi 4-10"),
  special theme ("Koko koulu ohjaa" vs subject-specific equivalent)

**Template keeps:**
- Pipeline variables: `{{ module }}`, `{{ school_context }}`,
  `{{ lesson.title }}`, `{{ lesson.augmented_content }}`,
  `{{ lesson.vuosikello_slot }}`, `{{ lesson.session_type }}`,
  `{{ lesson.duration_min }}`
- User prompt structure with lesson data injection

**Key:** This template uses all three one-pagers. The lesson template one-pager
is the most critical — it defines the entire output structure and tone.
The current opinto-ohjaus version has ~30 lines of markdown structure that
must be reproduced with equivalent depth for each new subject.

## What changes

### 1. Fix hardcoded paths in Python nodes

Three files: `load_data.py`, `save_preparation.py`, `save_lessons.py`.
Change `Path("projects/opinto_ohjaus/output")` → `Path(state.get("project_dir", ".")) / "output"`.
Add `project_dir: str` to state in `prepare.yaml` and `generate.yaml`.

### 2. Create templates/ directory

Convert the 4 opinto-ohjaus prompts into Jinja2 templates with three
slot variables: `subject_profile`, `pedagogical_context`, `lesson_template`.

### 3. Add prompts/summarize-subject.yaml

Summarization prompt with `SubjectSummaries` schema. Instructs the LLM to
read the research document and write three one-pager summaries.

### 4. Add nodes/render_templates.py

Reads the three one-pagers from state, renders 4 templates, writes prompt
files and `vars.yaml` to `project_dir/`. The generated `vars.yaml` includes
`project_dir` so subsequent pipeline steps pick it up via `--var-file`.

### 5. Add bootstrap.yaml

Two nodes: `summarize_subject` (LLM) → `render_templates` (Python).

### 6. Tests

- Bootstrap graph lints and loads
- Template rendering unit tests (mock summaries → expected prompt output)
- Existing 12 tests still pass

## Shared-graph pattern

Graphs and Python nodes live in `projects/opinto_ohjaus/`. A new subject gets:

```
projects/terveystieto/
├── terveystieto-ops.md       # research doc (input)
├── vars.yaml                 # rendered by bootstrap
├── prompts/*.yaml            # rendered by bootstrap
└── output/{module}/lessons/  # generated by pipeline
```

## Usage for a new subject

```bash
# 1. Gemini Deep Research
# Query: "terveystieto, lukion opetussuunnitelma LOPS 2019"

# 2. Bootstrap — summarize + render templates
mkdir -p projects/terveystieto
yamlgraph graph run projects/opinto_ohjaus/bootstrap.yaml \
  --var research_doc=@projects/terveystieto/terveystieto-ops.md \
  --var project_dir=projects/terveystieto \
  --var school_context="Keskikokoinen lukio, noin 300 opiskelijaa" \
  --var hours_per_module=18 \
  --var lesson_duration=75

# 3. Prepare
yamlgraph graph run projects/opinto_ohjaus/prepare.yaml \
  --var-file projects/terveystieto/vars.yaml \
  --var research_doc=@projects/terveystieto/terveystieto-ops.md

# 4. Generate
PROVIDER=anthropic yamlgraph graph run projects/opinto_ohjaus/generate.yaml \
  --var-file projects/terveystieto/vars.yaml

# 5. Review
cat projects/terveystieto/output/TE1/lessons/index.md
```
