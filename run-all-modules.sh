#!/bin/bash
# Run prepare + generate for all psykologia modules.
# Usage: bash run-all-modules.sh
# Requires: API keys loaded (source .env), run from projects/opinto_ohjaus/
set -euo pipefail

PROJECT_DIR="projects/psykologia"
VARS_FILE="$PROJECT_DIR/vars.yaml"
RESEARCH_DOC="$PROJECT_DIR/research-doc.md"

# Modules to process (PS1 already done)
MODULES=("PS2" "PS3" "PS4" "PS5")

echo "=== Psykologia: Processing ${#MODULES[@]} modules ==="
echo ""

for MODULE in "${MODULES[@]}"; do
    MOD_LOWER=$(echo "$MODULE" | tr '[:upper:]' '[:lower:]')
    echo "━━━ $MODULE: PREPARE ━━━"
    yamlgraph graph run "$PROJECT_DIR/prepare.yaml" \
        --var-file "$VARS_FILE" \
        --var "module=$MODULE" \
        --var "research_doc=@$RESEARCH_DOC" \
        2>&1 | tee "$PROJECT_DIR/run-prepare-${MOD_LOWER}.log" | tail -5
    echo ""

    echo "━━━ $MODULE: GENERATE ━━━"
    PROVIDER=anthropic yamlgraph graph run "$PROJECT_DIR/generate.yaml" \
        --var-file "$VARS_FILE" \
        --var "module=$MODULE" \
        2>&1 | tee "$PROJECT_DIR/run-generate-${MOD_LOWER}.log" | tail -5
    echo ""

    # Quick check
    LESSON_COUNT=$(ls "$PROJECT_DIR/output/$MOD_LOWER/lessons/"*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "✓ $MODULE: $LESSON_COUNT lessons generated"
    echo ""
done

echo "=== All modules complete ==="
echo ""
for MODULE in "${MODULES[@]}"; do
    MOD_LOWER=$(echo "$MODULE" | tr '[:upper:]' '[:lower:]')
    COUNT=$(ls "$PROJECT_DIR/output/$MOD_LOWER/lessons/"*.md 2>/dev/null | wc -l | tr -d ' ')
    echo "  $MODULE: $COUNT lessons"
done
