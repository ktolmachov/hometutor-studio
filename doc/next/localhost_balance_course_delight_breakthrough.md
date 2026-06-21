# Localhost Balance + Course Delight — Breakthrough v6 (CLOSED)

> **Дата актуализации:** 2026-06-20  
> **Статус:** Closure brief — волна `wave-localhost-balance-course-delight` закрыта целиком  
> **Версия:** v6 (model switch qwopus3.6-35b + llama.cpp + grounded validation hardening)  
> **SSoT статусов:** `doc/backlog_registry.yaml` — не этот файл

---

## 0. Что изменилось после v5

v5 фиксировал closure: Golden E2E, prompt-role unification. v6 отражает
смену модели и инфраструктурные hardening-фиксы после closure.

| Было в v5 | Стало в v6 |
|---|---|
| `qwen/qwen3.6-27b` (LM Studio :1234) — accepted local default | **`qwopus3.6-35b-a3b-v1-mtp` (llama.cpp :8080)** — новый accepted model после benchmark 2026-06-20: rank 99.55, 185 tps, 11.5/11.5 quality, smoke PASS |
| LM Studio как единственный local serving backend | **`LOCAL_LLM_PROFILE` infra**: `llama-cpp` / `lm-studio` переключение через `scripts/switch_local_llm.ps1`; config.env хранит профиль и порт |
| Grounded validation: over-citation → abstain | **Hardened**: footer-фильтрация, out-of-range `[N]` → drop (не fatal), uncited transitional sentences → drop (симметрично); `config.py` BASE_DIR fix для smoke из чужого cwd |
| `wave-course-graph-evidence-2026-06` active | **Closed 2026-06-11** целиком (все 3 пакета) |
| Следующий ход — Course Graph Evidence | Следующий ход — **proposed**: `ragas-langfuse-dataset-v1`, `smart-notes-native-generation-v1`, `workflow-skills-thin-adapter-v1` |

---

## 1. Accepted North Star

`qwopus3.6-35b-a3b-v1-mtp` принята как balanced local default model для всего
hometutor learning-plane (benchmark 2026-06-20, заменяет `qwen/qwen3.6-27b`):

```env
LOCAL_LLM_PROFILE=llama-cpp
LLM_API_BASE=http://127.0.0.1:8080/v1
LLM_MODEL=qwopus3.6-35b-a3b-v1-mtp

QUIZ_LLM_MODEL=qwopus3.6-35b-a3b-v1-mtp

GRAPH_LLM_API_BASE=http://127.0.0.1:8080/v1
GRAPH_MODEL=qwopus3.6-35b-a3b-v1-mtp

SSR_LLM_API_BASE=http://127.0.0.1:8080/v1
SSR_LLM_MODEL=qwopus3.6-35b-a3b-v1-mtp
```

Предыдущая модель (`qwen/qwen3.6-27b` через LM Studio :1234) остаётся
совместимой через `scripts/switch_local_llm.ps1 -Profile lm-studio`.

Evaluation/cloud-plane (`EVAL_JUDGE_LLM`, `REWRITE_MODEL`, `CLASSIFIER_MODEL`,
`INGESTION_MODEL`, `EVALUATE_MODEL`) остаётся explicit-route only, не default
generation.

Архитектурное решение: `doc/adr.md` → `ADR-024: Local balanced model for
hometutor learning-plane`.

---

## 2. Evidence

### 2.1 Model Benchmark (2026-06-20)

Benchmark pack v1.8: 3 кандидата, 8 задач + real hometutor smoke.

| alias | rank_score | avg tps | quality | smoke |
|---|---|---|---|---|
| **qwopus3.6-35b-a3b-v1-mtp** | **99.55** | 185.22 | 11.5/11.5 | ✅ PASS |
| qwopus3.6-27b-v2-mtp | 93.55 | 46.29 | 11.5/11.5 | — |
| qwen3.6-27b | 93.21 | 43.44 | 11.5/11.5 | — |

Все 3 модели: abstain PASS, grounded PASS, JSON PASS, quiz PASS.
qwopus35b получает +5 smoke bonus за real hometutor smoke (grounded validation
пройдена, `schema_validated=true`).

### 2.2 Smoke checker hardening

`app/prompt_smoke_checks.py` теперь проверяет:

- `require_no_fallback` через `debug["fallback_used"] == false`
- `require_model` через `debug["llm_model"]` (принимает список допустимых моделей)
- `max_reasoning_tokens` через `debug["token_usage"]["reasoning_tokens"]`
  (с `allow_missing_reasoning_tokens` для бэкендов без reasoning telemetry)
- fail-closed поведение, если требуемая telemetry отсутствует

`scripts/run_prompt_smoke.py` сохраняет compact `debug_summary`, а
`eval_data/prompt_smoke_cases.json` требует эти gates для LMS A-F.

### 2.3 Grounded validation hardening (2026-06-20)

`app/grounded_answer.py` — исправлена хрупкость, из-за которой smoke
падал в abstain при корректном по существу ответе:

- Footer «Источники:/Sources:» фильтруется и на уровне предложений (>240 chars)
- Out-of-range `[N]` (over-citation) → предложение отбрасывается, не fatal
- Uncited transitional sentences → отбрасываются (симметрично с over-citation);
  если ВСЕ предложения без цитат → abstain сохраняется
- `config.py`: BASE_DIR резолвится от `__file__`, не от cwd — smoke из
  benchmark pack находит `.env`
- `Smoke-Hometutor-LlamaCpp.ps1`: `LLM_MODEL`/`QUIZ_LLM_MODEL` выставляются
  из параметра `-Model`

### 2.4 SSR fallback policy

SSR loopback больше не делает неявный fallback на primary chat LLM:

- `SSR_ALLOW_MAIN_LLM_FALLBACK=false` по умолчанию
- недоступный SSR loopback даёт явную ошибку
- fallback на `get_llm()` разрешён только через explicit opt-in
- `get_ssr_llm_resolved()` пересоздаёт клиент на каждый вызов (без lru_cache),
  чтобы loopback recovery/disappearance отражались без рестарта
- tests покрывают default block и explicit allow

### 2.5 Model-role contract

Закрытые пакеты 2026-06-03:

| Slice | Evidence |
|---|---|
| Graph model typed settings | `GRAPH_LLM_API_BASE`, `GRAPH_MODEL` в `Settings` |
| Provider routing | `get_graph_llm()` и shared role routing в `app/provider.py` |
| Privacy guard | real data + cloud fallback без consent блокируется |
| UI transparency | Q&A показывает Local/Cloud/Cache, model, fallback marker, latency |
| Static guard | `tests/test_model_role_contract.py` |

---

## 3. Delight Loop — целевая цепочка

```
ПАПКА С ДОКУМЕНТАМИ
        │
        ▼
[1] Turnkey Course ──► course candidate (детерминированно, без LLM)
     course_cache       activation inside data/docs/<course>/
        │
        ▼
[2] Graph DNA      ──► concept extraction + prerequisite chains
     knowledge_graph    GRAPH_MODEL local, get_graph_llm()
        │
        ▼
[3] First Session  ──► Q&A → Tutor → Quiz → Card → Review
     mission_control    LLM_MODEL / QUIZ_LLM_MODEL, local, grounded-only
        │
        ▼
[4] Personal SSR   ──► weekly plan + narrative + next-best-concept
     ssr_weekly_*       SSR_LLM_MODEL local, explicit fallback policy
        │
        ▼
[5] Graduation     ──► session tape: e2e_graduation + model/source metadata
     course_graduation
        │
        └──────────► данные возвращаются в SSR → адаптация
```

Все 5 шагов цепочки доставлены и соединены в ведомый поток: Golden E2E
graduation проводит learner'а Q&A → Tutor → Quiz → Card → Review → Graduation
за одну сессию на локальной модели, с progress rail в Mission Control и
session tape evidence.

---

## 4. Финальный статус gaps

| Gap из v4 | Итог |
|---|---|
| `folder-to-course-delight-v1` | ✅ Closed 2026-06-05 — папка → indexed course с graph DNA status в UI |
| User-only tutor/quiz/minicheck prompt paths | ✅ Closed 2026-06-11 — `prompt-role-unification-v1`: system+user / explicit allowlist, machine-readable smoke contract |
| Golden E2E graduation | ✅ Closed 2026-06-10 — full DoD: 6/6 course loop, 18/18 strict smoke, `fallback_used=false` |
| User-facing cloud consent control | ⏳ Остаётся future UI package — не вошёл в волну, кандидат для consent/privacy follow-up |
| Adaptive SSR L3-L5 | ✅ Инженерно доставлены (май 2026, см. `doc/team_workflow/ssr_ai_vision/ssr_ai_vision_summary.md`); serving promotion gated по данным |

Также закрыты ранее: smoke checker hardening, SSR loopback explicit fallback
policy, model-role contract hardening, ADR-024 (balanced local model).

**Новый gap, открытый этой волной:** аудит графа курса «ИИ Агенты»
(2026-06-10) показал, что graph DNA был filename-fallback картой (5 nodes,
0 relations, 0 triplets) — delight loop работал, но «Graph DNA» шаг не давал
семантической ценности. Это породило волну `wave-course-graph-evidence-2026-06`.

---

## 5. Закрытые волны после Localhost Delight

### 5.1 Course Graph Evidence (closed 2026-06-11)

Волна `wave-course-graph-evidence-2026-06` — все 3 пакета closed:

| Package | Статус | Суть |
|---|---|---|
| `course-graph-compiler-v1` | ✅ closed 2026-06-11 | Нормализованный граф концептов с typed relations и provenance до source chunks |
| `course-graph-relation-ux-v1` | ✅ closed 2026-06-11 | Типы связей, confidence, source evidence в UI |
| `course-graph-aware-uplift-gate-v1` | ✅ closed 2026-06-11 | Graph-aware retrieval включается только при измеримом uplift |

### 5.2 Flashcard Handoff Fast Path (closed 2026-06-20)

Волна `wave-flashcard-handoff-fast-path` — 1 пакет:

| Package | Статус | Суть |
|---|---|---|
| `flashcard-handoff-fast-path-v1` | ✅ closed 2026-06-20 | «Не знаю / Объясни» → fast RAG (vector_only, top_k=2, no reranker), prose prompt, honest latency split, one-shot lifecycle |

### 5.3 Следующий ход

Активного пакета нет. Очередь proposed (SSoT — `backlog_registry.yaml`):
`ragas-langfuse-dataset-v1`, `smart-notes-native-generation-v1`,
`redaction-sink-coverage-v1`, `multi-query-expansion-v1`,
`workflow-skills-thin-adapter-v1`, `workflow-role-subagents-v1`.

---

## 6. Quality follow-up — закрыт

`prompt-role-unification-v1` closed 2026-06-11. Все live learning-plane
LLM-вызовы идут как `system + user` либо в explicit allowlist; контракт
проверяется в `tests/test_prompt_smoke_checks.py` и
`scripts/run_prompt_smoke.py --strict` (gates: `require_model`,
`require_no_fallback`, `max_reasoning_tokens=0`, role wiring).

---

## 7. Kill Switches

1. **Cloud call без явного consent на real data** → blocker.
2. **Graph enrichment идёт не через `get_graph_llm()`** → blocker.
3. **Course activation пишет вне `data/docs/<course>/`** → blocker.
4. **Smoke проходит без model/fallback/reasoning telemetry** → blocker.
5. **Tutor/quiz JSON ломается после prompt-role unification** → rollback или allowlist.
6. **Golden E2E тихо уходит в cloud из-за latency** → E2E должен assert `fallback_used == false`.

---

## 8. Итоговый вердикт

AI workstation: **ACCEPTED**  
llama.cpp + `qwopus3.6-35b-a3b-v1-mtp`: **ACCEPTED** (benchmark 2026-06-20, rank 99.55)  
hometutor local RAG smoke gate: **ACCEPTED**  
`qwopus3.6-35b-a3b-v1-mtp` as balanced local learning-plane default: **CONFIRMED**  
Breakthrough «папка → курс → graduation за 10 минут локально»: **DELIVERED 2026-06-10**  
Model upgrade path (qwen→qwopus, LM Studio→llama.cpp): **VALIDATED 2026-06-20**

Волна закрыта. Этот документ — исторический closure brief; новые статусы не
ведутся здесь. Модель и backend эволюционировали (v6), но breakthrough loop
остаётся тем же: папка → курс → graduation локально без cloud fallback.
