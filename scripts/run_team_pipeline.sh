#!/usr/bin/env bash
set -euo pipefail

# Scripted role pipeline for doc/team_workflow/process.md.
# Requires Claude Code CLI (`claude`) in PATH and a configured API key/session.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PACKAGE_ID="${1:-}"
if [[ -z "$PACKAGE_ID" ]]; then
  echo "Usage: ./scripts/run_team_pipeline.sh <package-id>" >&2
  exit 2
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "FAIL: claude CLI is not available in PATH." >&2
  exit 2
fi

if ! grep -Fq "\`${PACKAGE_ID}\`" doc/tasklist.md && ! grep -Fq "id: ${PACKAGE_ID}" doc/backlog_registry.yaml; then
  echo "FAIL: package '${PACKAGE_ID}' is not present in doc/tasklist.md or doc/backlog_registry.yaml." >&2
  exit 2
fi

if [[ -x ".venv/Scripts/python.exe" ]]; then
  PYTHON_BIN=".venv/Scripts/python.exe"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
elif command -v py >/dev/null 2>&1; then
  PYTHON_BIN="py"
else
  echo "FAIL: no Python interpreter found (.venv/Scripts/python.exe, .venv/bin/python, python, py)." >&2
  exit 2
fi

echo "=== Preflight: roadmap sync ==="
"$PYTHON_BIN" scripts/roadmap_sync_check.py
"$PYTHON_BIN" scripts/backlog_registry_lint.py

confirm() {
  local prompt="$1"
  local reply
  read -r -p "${prompt} Continue? [y/N] " reply
  case "$reply" in
    y|Y|yes|YES) ;;
    *) echo "Stopped for human review."; exit 0 ;;
  esac
}

ARTIFACTS_DIR="archive/team_artifacts/${PACKAGE_ID}"
mkdir -p "$ARTIFACTS_DIR"

echo "=== Phase 1: Product Owner ==="
claude --print \
  --system-prompt "$(cat doc/team_workflow/product_owner.md)" \
  "Execute Prompt 1: Planning next package. Package ID: ${PACKAGE_ID}" \
  > "${ARTIFACTS_DIR}/1_po_package.md"
confirm "Review ${ARTIFACTS_DIR}/1_po_package.md."

echo "=== Phase 2: Analyst ==="
claude --print \
  --system-prompt "$(cat doc/team_workflow/analyst.md)" \
  "Execute Prompt 1: Detail specification.
Package ID: ${PACKAGE_ID}
Input from PO:
$(cat "${ARTIFACTS_DIR}/1_po_package.md")" \
  > "${ARTIFACTS_DIR}/2_analyst_spec.md"
confirm "Review ${ARTIFACTS_DIR}/2_analyst_spec.md."

echo "=== Phase 3+4: Architect + Designer (parallel) ==="
claude --print \
  --system-prompt "$(cat doc/team_workflow/architect.md)" \
  "Execute Prompt 1: Execution contract.
Package ID: ${PACKAGE_ID}
Analyst spec:
$(cat "${ARTIFACTS_DIR}/2_analyst_spec.md")" \
  > "${ARTIFACTS_DIR}/3_architect_contract.md" &
PID_ARCH=$!

claude --print \
  --system-prompt "$(cat doc/team_workflow/designer.md)" \
  "Execute Prompt 1: UI specification.
Package ID: ${PACKAGE_ID}
Analyst spec:
$(cat "${ARTIFACTS_DIR}/2_analyst_spec.md")" \
  > "${ARTIFACTS_DIR}/4_designer_ui_spec.md" &
PID_DESIGN=$!

wait "$PID_ARCH"
wait "$PID_DESIGN"
confirm "Review architect/designer artifacts."

echo "=== Phase 5: Developer ==="
claude \
  "Execute the developer role.
Package ID: ${PACKAGE_ID}
Execution contract:
$(cat "${ARTIFACTS_DIR}/3_architect_contract.md")
UI specification:
$(cat "${ARTIFACTS_DIR}/4_designer_ui_spec.md")"

echo "=== Phase 6: Tester ==="
COMMIT_RANGE="$(git log --oneline -10 | tail -1 | cut -d' ' -f1)..HEAD"
claude --print \
  "Execute the tester role.
Package ID: ${PACKAGE_ID}
Contract: ${ARTIFACTS_DIR}/3_architect_contract.md
COMMIT_RANGE: ${COMMIT_RANGE}
PACKAGE_TYPE: mixed" \
  > "${ARTIFACTS_DIR}/6_tester_verdict.md"
confirm "Review ${ARTIFACTS_DIR}/6_tester_verdict.md."

echo "=== Pipeline complete ==="
echo "Artifacts: ${ARTIFACTS_DIR}"
