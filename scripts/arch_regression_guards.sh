#!/usr/bin/env bash
# Архитектурные регрессионные проверки (см. doc/arch_review_baseline.yaml).

set -uo pipefail

status=0

if [ -x ".venv/Scripts/python.exe" ]; then
  PYTHON_CMD=(".venv/Scripts/python.exe")
elif [ -x ".venv/bin/python" ]; then
  PYTHON_CMD=(".venv/bin/python")
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD=(python)
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD=(python3)
elif command -v py >/dev/null 2>&1; then
  PYTHON_CMD=(py -3)
else
  PYTHON_CMD=()
fi

# Разрешены os.environ в config.py и diagnostic-only ingestion.py; иначе — FAIL.
if command -v rg >/dev/null 2>&1; then
  if rg "os\.environ\[" app/ --type py -g "!app/config.py" -g "!app/ingestion.py" >/dev/null; then
    echo "FAIL: unexpected os.environ access"
    status=1
  else
    echo "OK: os.environ access guard (rg)"
  fi
elif command -v grep >/dev/null 2>&1; then
  if grep -R --line-number --include='*.py' 'os\.environ\[' app/ | grep -v "config.py\|ingestion.py" >/dev/null; then
    echo "FAIL: unexpected os.environ access"
    status=1
  else
    echo "OK: os.environ access guard (grep fallback)"
  fi
else
  echo "FAIL: neither rg nor grep found"
  status=1
fi

if [ ${#PYTHON_CMD[@]} -eq 0 ]; then
  echo "FAIL: python not found"
  status=1
elif "${PYTHON_CMD[@]}" -c "import ast,sys; t=ast.parse(open('app/query_service.py','rb').read()); bad=[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='_assemble_rag_result' and (n.end_lineno-n.lineno)>150]; sys.exit(1 if bad else 0)"; then
  echo "OK: _assemble_rag_result size"
else
  echo "FAIL: _assemble_rag_result too large"
  status=1
fi

if [ ${#PYTHON_CMD[@]} -eq 0 ]; then
  echo "FAIL: python not found"
  status=1
elif "${PYTHON_CMD[@]}" -c "import ast,sys; t=ast.parse(open('app/ingestion.py','rb').read()); bad=[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='build_index' and (n.end_lineno-n.lineno)>200]; sys.exit(1 if bad else 0)"; then
  echo "OK: build_index size"
else
  echo "FAIL: build_index too large"
  status=1
fi

if [ ${#PYTHON_CMD[@]} -eq 0 ]; then
  echo "FAIL: python not found"
  status=1
else
  actual=$("${PYTHON_CMD[@]}" -c "from pathlib import Path; print(sum(1 for line in Path('doc/adr.md').read_text(encoding='utf-8').splitlines() if line.startswith('## ADR-')))" | tr -d '\r')
  registry=$("${PYTHON_CMD[@]}" -c "from pathlib import Path; print(sum(1 for line in Path('doc/adr.md').read_text(encoding='utf-8').splitlines() if line.startswith('| [0')))" | tr -d '\r')
fi
if [ "${actual:-0}" -eq "${registry:-0}" ]; then
  echo "OK: ADR registry complete"
else
  echo "FAIL: ${actual:-unknown} ADRs but only ${registry:-unknown} in registry"
  status=1
fi

if [ ${#PYTHON_CMD[@]} -eq 0 ]; then
  echo "FAIL: python not found"
  status=1
elif "${PYTHON_CMD[@]}" -c "from pathlib import Path; files=['app/orchestrator_router.py','app/tutor_orchestrator.py']; bad=[]; [bad.append(f'{p}:{i}:{line.strip()}') for p in files for i,line in enumerate(Path(p).read_text(encoding='utf-8').splitlines(),1) if '.chat(' in line and 'chat_with_resilience' not in line and not line.strip().startswith('#')]; import sys; print('\n'.join(bad)); sys.exit(1 if bad else 0)"; then
  echo "OK: orchestrator chat resilience wrapper"
else
  echo "FAIL: direct llm.chat() outside resilience wrapper"
  status=1
fi

if command -v rg >/dev/null 2>&1; then
  if rg "from app.knowledge_graph" app/ui/ --type py >/dev/null; then
    echo "FAIL: UI importing knowledge_graph directly"
    status=1
  else
    echo "OK: no direct UI knowledge_graph imports"
  fi
else
  if grep -R --line-number --include='*.py' 'from app.knowledge_graph' app/ui/ >/dev/null; then
    echo "FAIL: UI importing knowledge_graph directly"
    status=1
  else
    echo "OK: no direct UI knowledge_graph imports"
  fi
fi

if command -v rg >/dev/null 2>&1; then
  if rg "from app\.knowledge_graph" app/routers/ --type py >/dev/null; then
    echo "FAIL: router→knowledge_graph"
    status=1
  else
    echo "OK: no direct router knowledge_graph imports"
  fi
else
  if grep -R --line-number --include='*.py' 'from app.knowledge_graph' app/routers/ >/dev/null; then
    echo "FAIL: router→knowledge_graph"
    status=1
  else
    echo "OK: no direct router knowledge_graph imports"
  fi
fi

if [ ${#PYTHON_CMD[@]} -eq 0 ]; then
  echo "FAIL: python not found"
  status=1
elif "${PYTHON_CMD[@]}" -c "import ast,sys; t=ast.parse(open('app/query_service.py','rb').read()); bad=[n for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.end_lineno-n.lineno)>100]; sys.exit(1 if bad else 0)"; then
  echo "OK: query_service fn <=100L"
else
  echo "FAIL: query_service fn >100L"
  status=1
fi

has_tutor=$(grep -c "Tutor Orchestration" doc/adr.md)
has_resilience=$(grep -c "LLM Resilience" doc/adr.md)
if [ "$has_tutor" -ge 1 ] && [ "$has_resilience" -ge 1 ]; then
  echo "OK: required ADRs present"
else
  echo "FAIL: missing subsystem ADR"
  status=1
fi

for pkg in transformers tokenizers docx; do
  if grep -qE "^${pkg}([<>=]|$)" requirements.txt; then
    if command -v rg >/dev/null 2>&1; then
      uses=$(rg "^import ${pkg}|^from ${pkg}" app/ scripts/ tests/ --type py 2>/dev/null | wc -l)
    else
      uses=$(grep -R --line-number --include='*.py' -E "^import ${pkg}|^from ${pkg}" app/ scripts/ tests/ 2>/dev/null | wc -l)
    fi
    if [ "$uses" -eq 0 ]; then
      echo "FAIL: ${pkg} in requirements.txt but no imports"
      status=1
    fi
  fi
done
echo "OK: no re-added dead deps"

exit "$status"
