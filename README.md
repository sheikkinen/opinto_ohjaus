# Opinto-ohjaus — Tuntisuunnitelmageneraattori

Lukion opinto-ohjauksen tuntisuunnitelmien automaattinen generointi YAMLGraph-pipelinellä. Lähdeaineistona LOPS 2019 opetussuunnitelma ja ajankohtaiset verkkosisällöt.

Gemini Deep Research: opinto-ohjaus, opetussuunnitelma - opintoohjauksen aiheet ja sisältö lukiossa

## Tulokset

| Moduuli | Kuvaus | Tunteja | Suunnitelmia |
|---------|--------|---------|--------------|
| **OP1** | Minä opiskelijana (2 op) | 18 × 75 min | 25 tuntisuunnitelmaa |
| **OP2** | Jatko-opinnot, työelämä ja tulevaisuus (2 op) | 18 × 75 min | 19 tuntisuunnitelmaa |

Tuntisuunnitelmat: `output/{module}/lessons/index.md`

Jokainen tuntisuunnitelma sisältää:
- Tavoitteet (LOPS 2019)
- Laaja-alainen osaaminen
- Tunnin kulku (75 min): virittäytyminen, työskentely, koonti
- Menetelmät ja materiaalit
- Arviointi ja eriyttäminen
- Koko koulu ohjaa -näkökulma

## Arkkitehtuuri

Kaksivaihepipeline, jossa prepare-vaihe kerää ja rikastaa aineiston ja generate-vaihe tuottaa tuntisuunnitelmat fan-out-periaatteella (yksi LLM-kutsu per aihe).

```
┌─────────────────────────────────────────────────────────┐
│  prepare.yaml                                           │
│                                                         │
│  START ──┬── list_topics ──┐                            │
│          │                 ├── extract_and_augment ──┐   │
│          └── extract_vuosikello ────────────────────┤   │
│                                                     │   │
│                                    save_preparation ──► │
│                                    output/{module}/     │
└─────────────────────────────────────────────────────────┘
                          │
                     JSON-tiedostot
                          │
┌─────────────────────────────────────────────────────────┐
│  generate.yaml                                          │
│                                                         │
│  START → load_data → generate_lessons → save_lessons    │
│                      (map: 1 LLM-kutsu/aihe)           │
│                                                         │
│                      output/{module}/lessons/*.md       │
└─────────────────────────────────────────────────────────┘
```

### Tiedostorakenne

```
projects/opinto_ohjaus/
├── prepare.yaml              # Vaihe 1: aineiston keruu ja rikastus
├── generate.yaml             # Vaihe 2: tuntisuunnitelmien generointi
├── vars.yaml                 # Muuttujat (module, school_context, ...)
├── prompts/
│   ├── list-topics.yaml
│   ├── extract-vuosikello.yaml
│   ├── extract-and-augment-topic.yaml
│   └── generate-lesson-plan.yaml
├── nodes/
│   ├── load_data.py          # Lataa JSON-data, rakentaa per-aihe-niput
│   ├── save_preparation.py   # Tallentaa prepare-vaiheen tulokset
│   └── save_lessons.py       # Tallentaa tuntisuunnitelmat .md-tiedostoina
├── tests/
│   └── test_pipeline.py      # 12 testiä (lint, load, edges, prompts, schemas)
└── output/
    ├── op1/
    │   ├── topics.json
    │   ├── vuosikello.json
    │   ├── augmented_topics.json
    │   └── lessons/
    │       ├── index.md
    │       ├── 01-siirtyminen-lukiokoulutukseen.md
    │       └── ...
    └── op2/
        └── lessons/
            ├── index.md
            ├── 01-jatko-opintojen-ja-urasuunnitelmien-paatoksenteko.md
            └── ...
```

## Käyttö

### Edellytykset

```bash
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=...   # tai muu provider
```

### 1. Validoi graafit

```bash
yamlgraph graph lint projects/opinto_ohjaus/prepare.yaml
yamlgraph graph lint projects/opinto_ohjaus/generate.yaml
```

### 2. Aja prepare-vaihe

```bash
yamlgraph graph run projects/opinto_ohjaus/prepare.yaml \
  --var-file projects/opinto_ohjaus/vars.yaml \
  --var research_doc=@projects/opinto_ohjaus/lukion-opinto-ohjaus-opetussuunnitelma-ja-sisallot.md
```

Tuottaa `output/{module}/` -hakemistoon:
- `topics.json` — aiheiden inventaario
- `vuosikello.json` — lukuvuoden jaksotus
- `augmented_topics.json` — web-haulla rikastetut aiheet

### 3. Aja generate-vaihe

```bash
PROVIDER=anthropic yamlgraph graph run projects/opinto_ohjaus/generate.yaml \
  --var-file projects/opinto_ohjaus/vars.yaml
```

Tuottaa `output/{module}/lessons/` -hakemistoon yksittäiset markdown-tiedostot ja `index.md`.

### 4. Vaihda moduuli

Moduuli asetetaan `vars.yaml`-tiedostossa:

```yaml
module: OP2   # OP1 tai OP2
```

Tai ylikirjoitetaan komentoriviltä:

```bash
yamlgraph graph run projects/opinto_ohjaus/prepare.yaml \
  --var-file projects/opinto_ohjaus/vars.yaml \
  --var module=OP2 \
  --var research_doc=@projects/opinto_ohjaus/lukion-opinto-ohjaus-opetussuunnitelma-ja-sisallot.md
```

### 5. Testit

```bash
pytest projects/opinto_ohjaus/tests/ -v --no-cov
```

## Uuden aineen lisääminen

Pipeline on suunniteltu yleiskäyttöiseksi. Uuden aineen (esim. terveystieto, historia) tuntisuunnitelmien generointi:

1. **Lähdeaineisto** — Tallenna opetussuunnitelma markdown-tiedostona projektin juureen
2. **vars.yaml** — Päivitä `module`, `school_context`, `hours_per_module`, `lesson_duration` uuden aineen tiedoilla
3. **Promptit** — Tarkista ja muokkaa prompteja `prompts/`-hakemistossa:
   - `list-topics.yaml` — aiheiden poimintakriteerit
   - `extract-and-augment-topic.yaml` — rikastuksen painopisteet
   - `generate-lesson-plan.yaml` — tuntisuunnitelman rakenne ja muoto
4. **Aja pipeline** — `prepare.yaml` → `generate.yaml` kuten yllä
5. **Tarkista tulokset** — `output/{module}/lessons/index.md`

### Huomioita

- `PROVIDER=anthropic` suositeltava generate-vaiheessa (Gemini rate-limit 1M tok/min rajoittaa fan-out-kutsuja)
- Prepare-vaihe käyttää websearch-työkalua ajankohtaisen tiedon hakuun — tarkista verkkoyhteys
- Augmented topics -tiedoston koko pysyy hallinnassa automaattisen signature-strippauksen ansiosta
- Map-nodien `on_error: skip` varmistaa, ettei yksittäinen virhe kaada koko ajoa
