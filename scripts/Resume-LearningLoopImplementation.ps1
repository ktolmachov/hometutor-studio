<#
.SYNOPSIS
    Continues implementation of doc/next/learning_loop_simplicity_plan.md, one
    candidate at a time, respecting the plan's own status/gates.

.DESCRIPTION
    This is a hand-off helper, not an autonomous coder. By default it:
      1. Reads current candidate statuses straight from the plan doc (no
         separate state file to drift out of sync).
      2. Picks the next candidate that is `proposed` and not gated.
      3. Runs a quick regression smoke-check in the hometutor repo before
         handing off (catches "the last candidate broke" before you spend
         time on the next one).
      4. Prints (and copies to clipboard) a self-contained implementation
         prompt for that candidate — the same kind you'd paste into a fresh
         Claude Code session.

    Candidates C1 ("needs discovery") and C3 (explicit owner sign-off gate in
    the plan) are never auto-prepped: the script prints what's blocking them
    instead of pretending they're ready to implement.

    -Run is opt-in and shells out to the `claude` CLI non-interactively. This
    starts a coding session with no human in the loop until it finishes —
    review the diff afterwards exactly as you would any other unattended run.
    The default (no -Run) only prepares the prompt; you paste it into a
    session yourself, which is the safer default and how B1/A1/A2 were done.

.PARAMETER Candidate
    Force a specific candidate (B1, B2, B3, C2) instead of auto-selecting the
    next one. C1/C3 are accepted here too, but only to print their gate status
    — never to produce an executable prompt.

.PARAMETER Run
    Actually invoke `claude -p <prompt>` in $RepoPath instead of just printing/
    copying the prompt. Off by default.

.PARAMETER SkipSmokeTest
    Skip the pre-flight pytest regression check (useful if you just ran it
    yourself, or the venv isn't set up in this shell).

.EXAMPLE
    ./Resume-LearningLoopImplementation.ps1
    Auto-picks the next ready candidate (currently B1), runs the smoke test,
    prints + copies its prompt.

.EXAMPLE
    ./Resume-LearningLoopImplementation.ps1 -Candidate B3 -Run
    Skips straight to B3 and launches `claude -p` with its prompt.
#>

[CmdletBinding()]
param(
    [ValidateSet('B1', 'B2', 'B3', 'C1', 'C2', 'C3')]
    [string]$Candidate,

    [switch]$Run,

    [switch]$SkipSmokeTest,

    [string]$RepoPath = 'D:\Projects\hometutor',

    [string]$PlanPath = 'D:\Projects\hometutor-studio\doc\next\learning_loop_simplicity_plan.md'
)

$ErrorActionPreference = 'Stop'

# ── 1. Read live status straight from the plan doc — no separate state file ──

if (-not (Test-Path $PlanPath)) {
    throw "Plan doc not found: $PlanPath"
}
$planText = Get-Content -Raw $PlanPath

function Get-CandidateStatus {
    param([string]$Id, [string]$Heading)
    # Matches e.g. "### Кандидат B1 — ..." then the next "**Статус: `xxx`" line.
    $pattern = "###\s*Кандидат\s+$Id\s+—[^\n]*\n\n\*\*Статус:\s*``([^``]+)``"
    $m = [regex]::Match($planText, $pattern)
    if (-not $m.Success) {
        Write-Warning "Could not find a status line for candidate $Id ($Heading) — check the plan doc format hasn't changed."
        return 'unknown'
    }
    return $m.Groups[1].Value.Trim()
}

$statuses = [ordered]@{
    B1 = Get-CandidateStatus -Id 'B1' -Heading 'Единый источник счётчиков Knowledge Graph'
    B2 = Get-CandidateStatus -Id 'B2' -Heading 'SSR explanation без сырой диагностики'
    B3 = Get-CandidateStatus -Id 'B3' -Heading 'Предложить пресет «Основной»'
    C1 = Get-CandidateStatus -Id 'C1' -Heading 'Индекс трудности концепта'
    C2 = Get-CandidateStatus -Id 'C2' -Heading 'Видимая ступень петли обучения'
    C3 = Get-CandidateStatus -Id 'C3' -Heading 'Слияние «зеркала» прогресса'
}

Write-Host "`nCurrent candidate statuses (read from plan doc):" -ForegroundColor Cyan
$statuses.GetEnumerator() | ForEach-Object { Write-Host ("  {0,-3} {1}" -f $_.Key, $_.Value) }

$gated = @{
    C1 = 'needs discovery — card→concept_id mapping, SSR blast radius and scoring weights are unresolved. Run discovery first (see plan §C1), do not implement blind.'
    C3 = 'requires owner sign-off — wide navigation refactor with deep-link risk (plan §C3 pre-flight inventory not done). Get explicit go-ahead before touching nav.'
}

# Order matches "Рекомендованный порядок реализации" in the plan.
$queue = @('B1', 'B2', 'B3', 'C1', 'C2', 'C3')

if (-not $Candidate) {
    $Candidate = $queue | Where-Object {
        $statuses[$_] -notmatch '^done' -and -not $gated.ContainsKey($_)
    } | Select-Object -First 1
    if (-not $Candidate) {
        Write-Host "`nNo ungated 'proposed' candidate left — everything is either done or gated." -ForegroundColor Yellow
        foreach ($g in $gated.Keys) {
            if ($statuses[$g] -notmatch '^done') {
                Write-Host "  $g is gated: $($gated[$g])" -ForegroundColor Yellow
            }
        }
        return
    }
    Write-Host "`nAuto-selected next candidate: $Candidate" -ForegroundColor Green
}

if ($gated.ContainsKey($Candidate)) {
    Write-Host "`n$Candidate is gated, not auto-prepped:" -ForegroundColor Yellow
    Write-Host "  $($gated[$Candidate])"
    Write-Host "`nSee hometutor-studio/doc/next/learning_loop_simplicity_plan.md, section Кандидат $Candidate, for the discovery/sign-off checklist."
    return
}

if ($statuses[$Candidate] -match '^done') {
    Write-Host "`n$Candidate is already marked done in the plan doc. Nothing to hand off." -ForegroundColor Yellow
    Write-Host "If you believe this is stale, reconcile the plan doc first (see how A1/A2 were closed out)."
    return
}

# ── 2. Pre-flight: repo clean-ish + smoke-test the last landed candidate ──

Push-Location $RepoPath
try {
    $dirty = git status --porcelain
    if ($dirty) {
        Write-Warning "hometutor working tree is not clean:`n$dirty`nReview before continuing — uncommitted changes from a prior candidate may still be pending review."
    }

    if (-not $SkipSmokeTest) {
        Write-Host "`nRunning regression smoke test (mission-control + navigation bundle)..." -ForegroundColor Cyan
        $py = Join-Path $RepoPath '.venv\Scripts\python.exe'
        if (-not (Test-Path $py)) { $py = 'python' }
        & $py -m pytest tests/test_mission_control_progressive.py tests/test_navigation_visibility.py tests/test_feature_registry.py -q
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "Smoke test failed — fix the regression before starting $Candidate. Not preparing a prompt."
            return
        }
    }
}
finally {
    Pop-Location
}

# ── 3. Candidate prompts — mirror the plan doc's Evidence/Proposed/DoD exactly ──
# Keep these in sync with the plan doc; if they drift, trust the plan doc and
# re-generate this block rather than the other way around.

$prompts = @{

'B1' = @'
Реализуй кандидат B1 из hometutor-studio/doc/next/learning_loop_simplicity_plan.md
(волна wave-trust-signals, P1) — единый источник счётчиков Knowledge Graph.

СТАТУС
Независим от A2 (done) и от B2/B3 — можно делать параллельно с ними, sign-off не требуется
(это чисто корректирующий фикс, а не редизайн главного экрана).

ПРОБЛЕМА
Mission Control и экран Knowledge Graph показывают разные числа под одинаковыми подписями
«концептов» и «готово учить» для одного и того же графа (наблюдалось: 76 vs 89 «концептов»;
0 vs 89 «готово учить»). Root cause подтверждён (не гипотеза) — это две независимые
реализации подсчёта над идентичным неотфильтрованным источником данных, не расхождение
данных и не scope-фильтрация.

EVIDENCE (файл:строка, hometutor, проверено — но перепроверь перед правкой, могло сместиться)
- app/ui/mission_control.py:702-721 (render_kg_mission_card): читает
  knowledge_graph.get_concepts() напрямую. total = len(valid) считает ВСЕ узлы (концепты +
  лекции). concept_nodes = total - lessons — вычитает лекции — именно concept_nodes
  подписывается «концептов». frontier = sum(d.get("frontier") for d in valid.values()) —
  читает сырой флаг frontier прямо из bundle-данных, без пересчёта.
- app/ui/knowledge_graph_d3.py:222 (build_kg_payload) — вот где на самом деле считается
  статистика для экрана графа (НЕ в dashboards_graph.py, тот только рендерит caption).
  :222 — valid = {cid: data for cid, data in concepts.items() if isinstance(data, dict)} —
  те же необработанные концепты, БЕЗ исключения узлов-лекций.
  :312-323 — frontier ПЕРЕСЧИТЫВАЕТСЯ заново из mastery_vector + prereqs_ready + learned
  (не читается как сырой флаг — это осознанное расхождение с mission_control.py).
  :378-385 — stats["total"] = len(nodes) (концепты+лекции вместе — отсюда 89 = 76+13),
  stats["frontier"] = sum(n["frontier"] for n in nodes) — по собственному пересчитанному
  значению.
- app/ui/dashboards_graph.py:1014-1093 (_render_knowledge_graph_tab) — рендерит caption
  из payload["stats"], где payload = render_d3_knowledge_graph(...) → build_kg_payload(...).
- ПОДТВЕРЖДЕНО (не предполагай заново, это уже проверено): dashboards_graph.py:1032-1039
  берёт concepts = knowledge_graph.get_concepts() от того же active_knowledge_graph
  (app.knowledge_service), что и mission_control.py:702-703 — идентичный источник.
  source_paths активного course scope передаётся в render_d3_knowledge_graph (:1064-1084),
  но используется ТОЛЬКО для resolve_compiler_health_for_kg (knowledge_graph_d3.py:461-469,
  health-сайдкар) — не фильтрует concepts/nodes/stats. Значит расхождение — чисто в
  формулах подсчёта, не в данных.
- Побочная деталь, требующая явного решения при фиксе: avg_mastery в обоих местах СЕЙЧАС
  согласован — оба делят сумму mastery на ВСЕ узлы включая лекции
  (mission_control.py:718-720, knowledge_graph_d3.py:383). Если исключить лекции из
  «концептов», реши явно, входят ли лекции в знаменатель avg_mastery — не сломай то, что
  сейчас случайно совпадает.

ЧТО СДЕЛАТЬ
1. Вынеси один общий helper (например, get_knowledge_graph_counters() в
   app/knowledge_service.py рядом с knowledge_graph — или тонкая переиспользуемая обёртка
   над уже существующим build_kg_payload() в app/ui/knowledge_graph_d3.py, чтобы не
   дублировать пересчёт frontier). Он должен возвращать согласованные:
   - total_concepts (БЕЗ узлов-лекций, явно исключая level == "lesson")
   - total_lessons
   - frontier_count (одно определение — предпочтительно ПЕРЕСЧИТАННОЕ, как в
     knowledge_graph_d3.py, а не сырой флаг из mission_control.py, потому что пересчитанное
     значение реально отражает prereqs/mastery, а не устаревший флаг в bundle)
   - avg_mastery (реши явно: по всем узлам или только по концептам — задокументируй выбор)
   - clusters
2. Переключи app/ui/mission_control.py:694-751 (render_kg_mission_card) на этот helper
   вместо самостоятельного total - lessons расчёта.
3. dashboards_graph.py менять не нужно в части расчёта — он уже использует
   build_kg_payload(); только убедись, что он использует ТОТ ЖЕ путь, если helper это
   оборачивает.
4. Если версии графа расходятся легитимно (published vs staging preview — см.
   docs/user_guide.md раздел «Knowledge Graph: точные разделы лекций» про
   published/staging/legacy read-path) — UI обязан явно показать бейдж состояния бандла на
   обоих экранах, а не молча показывать разные числа под одной подписью.

ЖЁСТКИЕ ПРАВИЛА (CLAUDE.md hometutor)
- Не трогай логику самого графа/knowledge_graph.get_concepts() — только слой подсчёта для UI.
- Scope тайт: app/knowledge_service.py (новый helper) + app/ui/mission_control.py:694-751 +
  проверка app/ui/dashboards_graph.py:1014-1093 (без изменения расчёта, только сверка, что
  использует общий путь).
- Broad except Exception в новом коде — только с # noqa: BLE001 и причиной.

DEFINITION OF DONE
- Одна и та же версия графа (published/staging) даёт идентичные числа на Mission Control и
  на экране Knowledge Graph.
- Если версии графа различаются — на обоих экранах виден явный бейдж состояния бандла.
- Явное решение зафиксировано в коде/комментарии: входят ли lesson-узлы в знаменатель
  avg_mastery.
- Regression-тест: mission_control.py больше не считает total - lessons самостоятельно —
  grep/import-проверка, что вызывает shared helper.

ТЕСТЫ
Unit-тест на shared helper (граница: узлы с/без level=="lesson", пересчитанный frontier
vs сырой флаг). Прогони targeted-тесты для затронутых модулей. Не запускай полный pytest
без нужды.

DOC-SYNC
Не требуется для внутренней консистентности; обнови docs/user_guide.md только если
добавляется явный бейдж bundle-состояния (published/staging).

Полный контекст — hometutor-studio/doc/next/learning_loop_simplicity_plan.md, раздел
«Кандидат B1». Если текущий код разошёлся с этим описанием — доверяй актуальному коду.
'@

'B2' = @'
Реализуй кандидат B2 из hometutor-studio/doc/next/learning_loop_simplicity_plan.md
(волна wave-trust-signals, P1) — SSR explanation без сырой диагностики.

СТАТУС
Независим от B1/B3, малое усилие, sign-off не требуется.

ПРОБЛЕМА (уже сужена предыдущим аудитом — не путай с "раскрыть свёрнутую панель")
Панель «Как выбрана подсказка» на Mission Control УЖЕ свёрнута по умолчанию:
app/ui/mission_control.py:356-357 рендерит нативный <details class="ssr-details"> БЕЗ
атрибута open. Ничего в механизме сворачивания чинить не нужно.

Реальная проблема — то, что видно ПОСЛЕ клика: блок «Локальные сигналы» внутри этого
(корректно свёрнутого) <details> содержит строки сырой разработческой диагностики.

EVIDENCE (файл:строка, hometutor — перепроверь перед правкой)
- app/smart_study_evidence.py:140 — строка "Коррекция по опоре на базу (source-trust)".
- app/smart_study_evidence.py:152 — EvidenceItem("steering", "Локальный руль SSR
  (сохранено)", steering_value, ...).
- app/ui/mission_control.py:303-319 — build_ssr_evidence_for_banner() собирает эти строки
  в ledger_lines, рендерятся в секции «📊 Локальные сигналы».
- app/ui/mission_control.py:356-357 — details свёрнуты по умолчанию (уже верно, не трогать).
- app/ui/smart_study_next_step_card.py:112-145 — отдельный confidence-ledger expander,
  тоже collapsed by default — проверь, нет ли там аналогичных сырых строк, раз уж трогаешь
  эту область.

ЧТО СДЕЛАТЬ
1. НЕ трогай механизм сворачивания <details> — он уже правильный.
2. Человекочитаемые секции («Другие варианты», «Если выбрать иначе», «Маршрут») оставь как
   есть — они уже написаны нормальным языком.
3. Блок «Локальные сигналы» с сырыми EvidenceItem-строками
   (app/smart_study_evidence.py:140,152 и соседние) перенеси за panel:debug_summary
   (tier 5, app/ui/feature_registry.py:77-84) — обычный пользователь не должен видеть их
   даже после клика на «Как выбрана подсказка».
4. Если решишь оставить блок видимым для всех, но переформулировать текст на
   learner-language вместо переноса за tier 5 — это тоже валидный путь, но выбери один,
   не оба одновременно, и объясни выбор в PR-описании.

ЖЁСТКИЕ ПРАВИЛА (CLAUDE.md hometutor)
- Scope тайт: app/ui/mission_control.py (_render_ssr_banner, build_ssr_evidence_for_banner),
  app/smart_study_evidence.py (текст EvidenceItem, если меняешь формулировки),
  app/ui/smart_study_next_step_card.py (только если там та же проблема).
- Не трогай логику выбора SSR-рекомендации, только представление evidence.

DEFINITION OF DONE
- Пользователь без tier 5 не видит сырых строк EvidenceItem («source-trust», «SSR-руль»)
  даже при клике «Как выбрана подсказка».
- Секции «Другие варианты» / «Если выбрать иначе» / «Маршрут» остаются доступны всем как
  есть, без изменений.
- Tier 5 / debug-режим сохраняет полную inspectability (ничего не потеряно для эксперта).

ТЕСТЫ
Найди/добавь targeted-тест, что несписочный (non-tier-5) рендер SSR banner не содержит
строк "source-trust" / "Локальный руль SSR". Прогони вместе с существующим
tests/test_mission_control_progressive.py, чтобы не сломать A2.

DOC-SYNC
docs/user_guide.md, раздел «Smart Study Router» — уточнить, какие блоки внутри
«Как выбрана подсказка» видны всем, а какие — только tier 5.

Полный контекст — hometutor-studio/doc/next/learning_loop_simplicity_plan.md, раздел
«Кандидат B2».
'@

'B3' = @'
Реализуй кандидат B3 из hometutor-studio/doc/next/learning_loop_simplicity_plan.md
(волна wave-trust-signals, P1) — предложить существующим пользователям пресет «Основной».

СТАТУС
Независим от B1/B2, малое усилие, sign-off не требуется — НО прочитай раздел
"Осторожность" ниже, там жёсткое предусловие перед формулировкой текста баннера.

ПРОБЛЕМА
Existing users по умолчанию получают уровень интерфейса «Всё включено», поэтому построенная
модель прогрессивного раскрытия (tiers 1-5) не помогает как раз тем, у кого уже накопилась
перегрузка UI.

EVIDENCE (файл:строка, hometutor — перепроверь перед правкой)
- docs/user_guide.md:70-76 — документирует пресеты «Основной» и «Всё включено» и то, что
  existing users получают «Всё включено» по умолчанию.
- app/ui_preferences.py:109-115 — возвращает LEVEL_ALL и сохраняет его, если
  _has_existing_activity() истинно и явного уровня ещё нет.
- tests/test_ui_preferences.py:24-29 — фиксирует это поведение (не ломай эти тесты, если
  они специально проверяют текущий default; при необходимости адаптируй их под новый
  banner-flow, не удаляй проверку дефолта).

ЧТО СДЕЛАТЬ
1. Одноразовый dismissible баннер для existing users без явно сохранённого выбора уровня:
   предложить переключиться на пресет «Основной».
2. Accept — переключает UI level на 2 («Основной»).
3. Dismiss — пишет флаг в app_kv («не показывать снова»), НЕ переключает уровень.
4. Explicit user choice (уже сохранённый уровень) не должен НИКОГДА перезаписываться этим
   баннером — баннер показывается только при его отсутствии.

ОСТОРОЖНОСТЬ (обязательно перед тем, как писать текст баннера)
Не пиши в баннере фразу вроде «всё останется доступным через deep-link», пока не проверил
это руками. Hidden-view navigation идёт через PENDING_CURRENT_VIEW_KEY
(app/ui/session_state.py) и связанную visible/hidden nav-логику. Перед формулировкой текста:
запусти Streamlit preview, включи уровень 2 («Основной»), и вручную пройди хотя бы один
deep-link на скрытый при этом уровне view (например, tier-3 «Живой конспект» или «Курс»,
если есть готовая ссылка/карточка на него) — убедись, что переход реально работает, а не
просто не падает молча. Только после этого пиши формулировку «всё доступно».

ЖЁСТКИЕ ПРАВИЛА (CLAUDE.md hometutor)
- Scope тайт: app/ui_preferences.py, app/ui/control_panel.py (компонент баннера),
  возможно app/ui/navigation_visibility.py. Не трогай app/ui/session_state.py, кроме
  чтения PENDING_CURRENT_VIEW_KEY для верификации.
- User-state persistence только через app/user_state*.py хелперы — используй существующий
  app_kv-паттерн (как в study_scope.py), не создавай ad hoc SQLite-соединения.

DEFINITION OF DONE
- Баннер показан ровно один раз eligible existing users без явного сохранённого выбора.
- Accept/dismiss решение персистентно (app_kv), баннер не показывается повторно.
- Явный прежний выбор пользователя никогда не перезаписывается автоматически.
- Deep-link на хотя бы один hidden-при-level-2 view вручную проверен ДО того, как текст
  баннера обещает «всё доступно» — задокументируй, какой view ты проверил и как.

ТЕСТЫ
Прогони tests/test_ui_preferences.py (адаптируй при необходимости, не удаляй проверку
дефолта для новых/existing users). Добавь targeted-тест на dismiss/accept-персистентность
баннера по аналогии с tests/test_study_scope.py (app_kv persistence pattern).

DOC-SYNC
docs/user_guide.md, раздел «Панель управления и уровни интерфейса».

Полный контекст — hometutor-studio/doc/next/learning_loop_simplicity_plan.md, раздел
«Кандидат B3».
'@

'C2' = @'
Реализуй кандидат C2 из hometutor-studio/doc/next/learning_loop_simplicity_plan.md
(волна wave-difficulty-and-mastery-mirror, P2) — видимая ступень петли обучения
(learner_stage), ранее ошибочно называвшаяся «уровни 0-4».

СТАТУС
`proposed`, но с открытыми вопросами (см. ниже) — если ответы не очевидны из кода за
разумное время, ОСТАНОВИСЬ И СПРОСИ владельца, не додумывай события произвольно
(правило CLAUDE.md: "Stop and ask if a task references... discovered a blocker").

ВАЖНОЕ ПЕРЕИМЕНОВАНИЕ — не называй это "level 0-4" нигде в коде/UI
В app/gamification_service.py УЖЕ есть отдельная XP-система уровней:
- level_from_total_xp() — app/gamification_service.py:113 (1-99, из total_xp // 1000 + 1)
- level_title() — app/gamification_service.py:119
Использование слова "уровень" для второй, никак не связанной шкалы создаст прямую
терминологическую путаницу. Новая сущность называется ступень петли обучения /
learner_stage (английский идентификатор в коде) — это ось "насколько глубоко пройдена
петля обучения", отдельная от и не заменяющая XP.

ПРЕДЛОЖЕНИЕ СТУПЕНЕЙ (из плана)
- 0 Старт: первый grounded answer с источником
- 1 Понимание: первый завершённый quiz
- 2 Память: карточка вспомнена после интервала минимум неделю (SM-2)
- 3 Карта: закрыт graph gap
- 4 Мастерство: course/concept graduation

ЧТО СДЕЛАТЬ
1. Добавь поле learner_stage — либо небольшой аккуратно изолированный блок в
   app/gamification_service.py (рядом с XP-логикой, НЕ внутри неё, чтобы оси не смешались),
   либо отдельный небольшой модуль, если так чище.
2. Показывай ступень одной компактной строкой на Mission Control (естественное место —
   рядом со строкой контекста из A2, app/ui/mission_control.py:827-874
   build_context_row_segments/_render_context_row — расширь эти сегменты, не дублируй
   отдельный рендер).
3. Храни transition state (текущая ступень + timestamp последнего перехода) в app_kv, по
   аналогии с study_scope.* (app/ui/study_scope.py) — например
   learner_stage.current, learner_stage.last_transition_at.
4. При пересечении порога — ОДНО уведомление о переходе, идемпотентное: повторный рендер
   Mission Control (в той же сессии или после рестарта) не должен показать его снова, если
   last_transition_at уже отражает этот переход.

ОТКРЫТЫЕ ВОПРОСЫ — реши через код, а если не находится ответ за разумное время, СПРОСИ
владельца вместо того, чтобы гадать:
1. Какое существующее событие в app/spaced_repetition.py доказывает "карточка вспомнена
   после интервала минимум неделю"? Поищи готовый сигнал прежде, чем вводить новый.
2. Какое существующее событие доказывает "graph gap closed"? Поищи в
   app/knowledge_service.py / app/learner_model_service.py.
3. Ступень 4 (Мастерство) — это course graduation, concept graduation, или оба? Если
   неочевидно из app/course_graduation.py — спроси, не выбирай произвольно.

ЖЁСТКИЕ ПРАВИЛА (CLAUDE.md hometutor)
- User-state persistence только через app/user_state*.py хелперы — app_kv-паттерн, как в
  study_scope.py, не ad hoc SQLite.
- Scope тайт: app/gamification_service.py (или новый модуль), app/ui/mission_control.py
  (context row), docs.

DEFINITION OF DONE
- Ступень видна одной строкой, визуально не путается с XP-уровнем (разные подписи/иконки).
- Переход ступени даёт ровно одно уведомление за счёт app_kv-хранимого
  last_transition_at.
- Уведомление не повторяется при рестарте/повторном рендере той же сессии.
- Все три "открытых вопроса" выше либо решены с конкретной evidence-ссылкой на код, либо
  явно вынесены как вопрос владельцу — не угаданы.

ТЕСТЫ
Тест на идемпотентность уведомления (переход учтён → повторный рендер не показывает снова).
Тест, что XP-level и learner_stage не считаются одной и той же функцией/полем.

DOC-SYNC
docs/user_guide.md — новый раздел «Ступени петли обучения», явно отличённый от
существующего описания XP/streak в gamification.

Полный контекст — hometutor-studio/doc/next/learning_loop_simplicity_plan.md, раздел
«Кандидат C2».
'@

}

# ── 4. Hand off ──

$promptText = $prompts[$Candidate]
Write-Host "`n=== Prompt for $Candidate ===`n" -ForegroundColor Green
Write-Host $promptText

try {
    $promptText | Set-Clipboard
    Write-Host "`n(copied to clipboard)" -ForegroundColor DarkGray
}
catch {
    Write-Verbose "Clipboard unavailable in this session — copy manually from above."
}

if ($Run) {
    Write-Host "`n-Run passed: launching 'claude -p' in $RepoPath. This runs unattended — review the diff afterwards." -ForegroundColor Yellow
    Push-Location $RepoPath
    try {
        claude -p $promptText
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "`nPaste the prompt above into a fresh Claude Code session in $RepoPath to implement $Candidate." -ForegroundColor Cyan
    Write-Host "Once it's committed, come back and ask for an audit/reconciliation pass before running this script again."
}
