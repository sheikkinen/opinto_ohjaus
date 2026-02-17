# Plan: Generalized Lukio Lesson Plan Pipeline — Template Approach

## In / Out

**In:** Gemini Deep Research document (markdown) for any Finnish lukio subject
**Out:** Per-topic one-pager lesson plans (75 min) as markdown files

## Key insight

The original prompts were authored by a thinking model (claude-sonnet-4-5) in an
interactive session. That model performed two distinct tasks simultaneously:

1. **Extract domain knowledge** — subject, modules, assessment, sources, methods
2. **Author YAML prompt files** — correct format, Jinja2 variables, schemas

These tasks have different complexity. Extraction is factual; a cheap model
handles it. YAML authoring is format-sensitive; better handled by pre-validated
templates. Separating them makes the pipeline cheaper, more robust, and debuggable.

## Approach: extraction + templates

```
research_doc.md + basic params
        │
        ▼
┌──────────────────────────────────────────────┐
│  bootstrap.yaml  (NEW)                       │
│  Step 1: Extract domain profile (LLM)        │
│  Step 2: Render prompt templates (Python)     │
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

### Step 1: Extract domain profile

Single LLM call with structured output (Pydantic schema). The model reads the
research document and returns a `DomainProfile`:

```yaml
schema:
  name: DomainProfile
  fields:
    subject_name:
      type: str
      description: "Oppiaineen nimi (esim. terveystieto)"
    expert_role:
      type: str
      description: "Asiantuntijarooli system-promptiin (esim. lukion terveystiedon opettaja)"
    modules:
      type: list
      description: "Moduulit: [{code, name, description, key_topics}]"
    assessment_model:
      type: str
      description: "Arviointimalli (esim. 'numeroarviointi 4-10' tai 'suoritusmerkintä S/H')"
    key_sources:
      type: list[str]
      description: "Keskeiset verkkolähteet (oph.fi aina mukana)"
    laaja_alainen:
      type: list[str]
      description: "Relevanttien laaja-alaisen osaamisen alueet"
    collaboration_partners:
      type: list[str]
      description: "Yhteistyötahot (esim. terveydenhoitaja, TE-toimisto)"
    teaching_methods:
      type: list[str]
      description: "Sopivat opetusmenetelmät"
    lesson_sections:
      type: list
      description: "Tuntisuunnitelman osiot: [{name, description}]"
    special_themes:
      type: str
      description: "Aineen erityinen koko-koulu-näkökulma (esim. 'Koko koulu ohjaa')"
```

This is factual extraction. A fast model (gemini-flash, haiku) handles it.

### Step 2: Render prompt templates

Python node reads the `DomainProfile` and renders 4 Jinja2 templates into
complete prompt YAML files. Templates live in `templates/` (not `prompts/`):

```
templates/
├── list-topics.yaml.j2
├── extract-vuosikello.yaml.j2
├── extract-and-augment-topic.yaml.j2
└── generate-lesson-plan.yaml.j2
```

Example template fragment (`generate-lesson-plan.yaml.j2`):

```yaml
system: |
  Olet {{ expert_role }}.

  Laadi yksisivuinen (one-pager) tuntisuunnitelma lukion {{ subject_name }}-kurssille.

  ## RAKENNE
  {% for section in lesson_sections %}
  ### {{ section.name }}
  {{ section.description }}
  {% endfor %}

  ## ARVIOINTI
  {{ assessment_model }}

  ## {{ special_themes | upper }}
  Huomioi {{ special_themes | lower }} -näkökulma suunnitelmassa.

  ## LÄHTEET
  {% for source in key_sources %}
  - {{ source }}
  {% endfor %}
```

No YAML generation by the LLM. Templates are pre-validated. Format risk is zero.

## Why templates over generation

| | Generation (plan v2) | Templates (this plan) |
|---|---|---|
| Model requirement | Strong (sonnet-4-5) | Weak (flash/haiku) |
| Format risk | LLM may produce broken YAML | Zero — templates are pre-validated |
| Domain nuance | LLM makes holistic choices | Structured fields, some judgment |
| Debuggability | Opaque — regenerate entire prompt | Fix one field in profile |
| Cost per bootstrap | High (200K context, strong model) | Low (extraction only) |
| Template evolution | Regenerate all prompts | Update template, re-render |

The generation approach mirrors how the original session worked: Claude authored
complete prompts. But that was a constraint of the interactive process, not a
design principle. The extraction + template split is the natural decomposition.

## What changes

### 1. Fix hardcoded paths in Python nodes

Three files: `load_data.py`, `save_preparation.py`, `save_lessons.py`.
Change `Path("projects/opinto_ohjaus/output")` → `Path(state.get("project_dir", ".")) / "output"`.
Add `project_dir: str` to state in `prepare.yaml` and `generate.yaml`.

### 2. Create templates/ directory

Convert the 4 opinto-ohjaus prompts into Jinja2 templates. Each template uses
`DomainProfile` fields instead of hardcoded domain terms.

### 3. Add prompts/extract-domain-profile.yaml

Extraction prompt with `DomainProfile` schema. Instructs the LLM to read the
research document and return structured domain knowledge.

### 4. Add nodes/render_templates.py

Reads `DomainProfile` from state, renders 4 templates, writes prompt files
and `vars.yaml` to `project_dir/`. The generated `vars.yaml` includes
`project_dir` so subsequent pipeline steps pick it up via `--var-file`.

### 5. Add bootstrap.yaml

Two nodes: `extract_profile` (LLM) → `render_templates` (Python).

### 6. Tests

- Bootstrap graph lints and loads
- Template rendering unit tests (mock profile → expected prompt output)
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

# 2. Bootstrap — extract profile + render templates
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
