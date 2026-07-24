# Реестр сквозных болезней evolutionary analyses

Этот файл — не каталог фич и не backlog. Он хранит повторяющиеся классы
первопричин, которые проявляются в разных продуктовых областях. Перед новым
разбором автор обязан выбрать существующий `PAIN-*` или обосновать добавление
нового класса.

## Как пользоваться

1. Найти боль-якорь в коде, данных или живом прогоне.
2. Проверить, не является ли она новым экземпляром болезни ниже.
3. В шапке разбора указать `Cross-cutting pain: PAIN-NN` и конкретный экземпляр.
4. Если этот класс уже встречался, написать, почему прежнее решение не закрывает
   новый экземпляр. Совпадение — не запрет, но молчаливое переоткрытие запрещено.
5. После реализации обновить статус экземпляра: `open`, `mitigated`, `closed` или
   `reopened`, сохранив ссылку на доказательство.

## Канонические классы

| ID | Болезнь | Диагностический вопрос | Подтверждённые экземпляры в серии |
|---|---|---|---|
| `PAIN-01` | Две или более копии истины | Одно понятие вычисляется, хранится или описывается независимо в нескольких местах? | №1: `quiz_mastery` как третья копия; №7: состояние плана; №12: константы бюджетов в страже; №13: две ASR-линии; №21: риск третьего каталога |
| `PAIN-02` | Закон вне ежедневного цикла | Правило существует в документе или разовой проверке, но не исполняется тем циклом, который и так запускается каждый день? | №12: архитектурные ограничения до подключения regression guards к pytest/CI; №24: quiz-рубрика без executable content gate перед mastery; №25: grounded-answer gate вне CI/cache parity |
| `PAIN-03` | Провода без поверхности | Данные и логика уже существуют, но студент не видит результата и не может им воспользоваться? | №8: невидимая половина; №10: learner trace и due-сигнал; №20: возможности продукта без дверей из мира; №28: построенное серией упрощение (study-поверхность, одна нить) невидимо владельцу — автоапгрейд ui_level до diagnostic |
| `PAIN-04` | Две линии производства | Один пользовательский артефакт создаётся разными конвейерами с расходящимися контрактами и качеством? | №13: независимые ASR-конвейеры |

Перечень начальный, а не исчерпывающий. Новый класс добавляется только когда
существующие диагностические вопросы не объясняют причину. Новое название для
старого механизма не считается новым классом.

## Формат экземпляра

Добавляя подтверждение, фиксируй:

```text
Instance: PAIN-NN / короткое имя
Analysis: №NN
Evidence: repo@commit:path::symbol (строки Lx-Ly — только подсказка)
Observed effect: что реально видит или теряет пользователь
Status: open | mitigated | closed | reopened
Closure evidence: тест, метрика или живой прогон
```

`file:line` недостаточно как идентификатора: номера строк дрейфуют. Канонический
якорь — репозиторий, ревизия, путь и символ; диапазон строк оставляется для
удобства чтения.

## Подтверждённые экземпляры

```text
Instance: PAIN-02 / Quiz content gate outside mastery cycle
Analysis: №24
Evidence: hometutor@07c8a2a8:app/quiz_micro.py::process_micro_quiz_outcome; hometutor@07c8a2a8:app/fact_source_binding.py::apply_quiz_outcome_to_learner_state
Observed effect: студент получает mastery/SM-2 update из structurally valid quiz without source-grounded content validation.
Status: open
Closure evidence: отсутствует; требуется live baseline VLQR и executable gate до записи mastery.

Instance: PAIN-02 / Grounded answer gate outside CI and cache parity
Analysis: №25
Evidence: hometutor@1c9c56961:app/grounded_answer.py::apply_grounded_validation; hometutor@1c9c56961:scripts/home_rag_integration_gate_v1.py::main; hometutor@1c9c56961:.github/workflows/ci.yml
Observed effect: студент может получить ответ с формальными цитатами без измеренной semantic grounding guarantee; cache_hit path может обходить актуальную grounded validation.
Status: open
Closure evidence: отсутствует; требуется E2 semantic audit packet and CI/cache parity decision.

Instance: PAIN-02 / Content quality instruments outside the learning route (mega-bundle)
Analysis: №26
Evidence: hometutor@84b7b5668:app/async_quality_judge.py::schedule_async_quality_judge_if_sampled (выключен по умолчанию, оценки только в metrics); hometutor@84b7b5668:app/query_metrics.py::_compute_deterministic_quality_checks (→ debug); hometutor@84b7b5668:app/konspekt_learning_passport.py::build_konspekt_learning_passport (рубрика/staleness → 2 UI-вью); hometutor@84b7b5668:app/ui/knowledge_graph_d3_analysis.py::node_worth (без качества/свежести); live E2: quiz_sample r1/guardrails#3 (искажение из ASR-оговорки прошло структурные проверки), user_state.db::quiz_results (нет колонок origin/evidence), get_topics_catalog() → 0 тем (weak-spot→quiz петля мертва).
Observed effect: измерительные приборы качества существуют, но ни одно их число не участвует в решениях «что показать, что спросить, что записать в mastery, куда вести»; сырой ASR-транскрипт питает экзамен наравне с вычитанным конспектом.
Status: open
Closure evidence: отсутствует; требуется P0-A gate packet + P0-B verified step contract (doc/next/course_content_gate_compiler_plan.md) и post-ship replay E2-семпла.

Instance: PAIN-02 / Local-model write-set and tests validated against the model's own declaration, not the task
Analysis: №27
Evidence: hometutor-studio@545d155:scripts/llamacpp_agent_trigger.ts::validatePatchAgainstWriteSet (строка 748, сверяет diff с parsed.writeSetRaw — ответом модели; authoritative task write-set нигде не извлекается); hometutor-studio@545d155:scripts/llamacpp_agent_trigger.ts::callLlamaCpp (строка 804, extractTestCommands(parsed.testsRaw) — команды тестов берутся из ответа модели, не из задачи); тот же файл, строка 22, DEFAULT_MODEL="qwen/qwen3-coder-next" — не совпадает с production alias qwen3-coder-next-q4ks. Live E2: прогон триггера с дефолтным alias против запущенного production-сервера → exit 2 за 54мс (model_alias_not_found); после правки alias — полный PASS за 2860мс, execution_contract.md с test-output evidence, но model-authored summary/risks всё ещё смешаны с доказательствами; 98/98 vitest.
Observed effect: правило «границы задаёт задача, не модель» существует только в тексте guide (agent_adapter_llamacpp.md §5–6); код, который реально исполняется каждый прогон, доверяет декларации модели на входе (write-set) и на выходе (tests) — auto-routing на этом контуре сегодня был бы недоказуемым по построению.
Status: open
Closure evidence: отсутствует; требуется полный P0-1→P0-3 плана v1.4 (doc/next/local_model_execution_packet_plan.md): authoritative task gates + deterministic evidence, durable patch journal/locks/recovery и исполнимый finalize-review. До live shadow-run с чистым worktree и terminal verified статус остаётся open.

Instance: PAIN-03 / Series-level simplification without surface (упрощение серии невидимо владельцу)
Analysis: №28
Evidence: hometutor@05565efe9:app/ui_preferences.py::get_ui_level (строки 140–152 — профиль с существующей активностью молча повышается до LEVEL_DIAGNOSTIC → все 18 nav-вью); hometutor@05565efe9:app/ui/feature_registry.py::FEATURES (докстринг «аддитивный слой», 26 фич, 18 nav); git 2026-07-10..05565efe9: app/ui +22 639/−2 739 строк, 29 новых файлов, 0 удалённых.
Observed effect: после 27 разборов владелец открывает приложение и видит ту же поверхность из 18 экранов; построенная study-поверхность (~10 вью) и «одна нить» №23 по построению достаются только пустому профилю — ощущение «кардинального упрощения не произошло» при 24 отгруженных структурных ядрах; outcome доказан лишь у 1/27 разборов (OVR 3.7%).
Status: mitigated (2026-07-24)
Closure evidence: hometutor@589636dab+:app/ui_preferences.py::get_ui_level — автоапгрейд до LEVEL_DIAGNOSTIC удалён, undecided-профиль резолвится в LEVEL_STUDY без записи; app/ui_preferences.py::should_offer_first_choice/is_ui_level_decided добавлены; app/ui/mission_control.py::_render_first_level_choice_banner — one-time баннер «Простой/Полный вид». Тесты: tests/test_ui_preferences.py, tests/test_mission_control_first_level_choice.py — зелёные; регрессий в test_navigation_visibility.py/test_global_navigation.py/test_architecture_guards.py нет.
Не closed: это структурный фикс причины, не поведенческое подтверждение «стало ли легче владельцу» — тот замер (visible_nav_views_for_level на реальном профиле владельца + субъективное ощущение) не проводился; см. doc/next/series_summit_validation_plan.md P0-2 и replay_artifacts_2026-07/replay_2026-07-24.md.
```
