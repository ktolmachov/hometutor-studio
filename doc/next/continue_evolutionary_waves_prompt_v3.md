# Continuation prompt v3 — evolutionary waves (runtime-only)

Продолжи реализацию улучшений из серии эволюционных разборов только в runtime-репозитории.

## Контекст

- Runtime-репозиторий: `D:\Projects\hometutor`
- Не переключайся в другие репозитории.
- Не читай и не меняй внешние процессные документы.
- Не запускай внешние процессные команды закрытия или синхронизации.
- Если для выбора следующего шага не хватает контекста, не спрашивай пользователя: продолжай default-направление `Full Circle / wave-full-circle-pulse` по runtime-коду и уже переданному аудиту в текущем чате.
- Do not finish with a question such as "the prompt does not contain a concrete task", "which direction should I continue?", or "continue Knowledge Fate?".
- A clean worktree, no explicit bug, or an already-open `tests/test_memory_loop_closure.py` means: continue the default target automatically.

## Шаг 0 — состояние runtime-репозитория

Выполни `git status` в `D:\Projects\hometutor`.

- Если рабочее дерево грязное, не считай все изменения своими автоматически.
- Сохрани пользовательские/предыдущие изменения: не откатывай, не переписывай и не удаляй их без явной просьбы.
- Если изменение нужно продолжить, работай поверх него аккуратно и явно назови это в финале.
- Если дерево чистое, отметь это в финале одной строкой.

## Обязательное чтение в runtime-репозитории

1. `D:\Projects\hometutor\AGENTS.md`
2. `D:\Projects\hometutor\docs\conventions.md`
3. Runtime-код и тесты только в пределах задачи/аудита.
4. Если задача касается Agent UI/roadmap — дополнительно `D:\Projects\hometutor\docs\agent_roadmap.md`.

## Правила реализации

- Работай только в `D:\Projects\hometutor`.
- Не меняй документы/файлы вне runtime-репозитория.
- Не останавливай runtime-работу из-за отсутствия внешнего статуса.
- Не запускай команды из других репозиториев.
- Write-set держи узким: меняй только runtime-файлы, необходимые для запроса.
- Не делай попутный рефакторинг.
- Runtime-docs обновляй только если изменился публичный API, UI-поведение, архитектура, config или persistence.

## Default continuation target

Если пользователь дал этот prompt без конкретного бага или выбора направления, продолжай автоматически, без уточняющих вопросов:

1. Реализуй `Full Circle / wave-full-circle-pulse`, сначала A1, затем A2.
2. A1 — «Пульс петли» в tutor chat:
   - `app/query_response_postprocessing.py`
   - `app/query_rag_assembly.py`
   - `app/query_tutor_context.py` — здесь физически живёт `_build_tutor_payload()`
     (импортируется в `query_rag_assembly.py`); новый параметр/ключ `learner_trace`
     добавляется именно тут, иначе он не попадёт в `tutor_payload` → `assistant_meta["tutor"]`
   - `app/ui/tutor_chat_response_render.py`
   - `app/ui/tutor_chat_render.py` или `app/ui/helpers.py`, только если нужен маленький formatter/renderer
   - `tests/test_memory_loop_closure.py` и/или targeted tutor metadata/UI test
3. A1 contract: learner trace должен пройти полный путь `update_outcome` → `ctx.metadata["learner_trace"]` → `assistant_meta["tutor"]["learner_trace"]` → `tutor_meta` в history message → видимая строка в tutor chat. Не считай запись в `ctx.metadata` достаточной, пока renderer её не видит.
4. A1 UI: показать короткую строку без debug-панели, например `След записан: <concept> · источников: N`. LLM source показывай только если он уже доступен в `tutor_meta`; не добавляй новый provider pipeline ради строки.
5. A2 — «Одно число Повторить сегодня»:
   - `app/ui/mission_control.py`
   - `app/ui/tutor_chat_response_render.py`
   - `app/ui/resume_cards_due.py` / `app/ui/resume_cards_smart_study.py`, только если там реально живёт surface-число
6. A2 contract: сначала унифицируй surface-число и подпись. Не обещай единую очередь, если реализация не вводит явный review-router. Если считаешь сумму `flashcard_due_n + sm2_due_n`, назови это суммой двух очередей; если делаешь union, явно определи ключ дедупликации.
7. Если A1/A2 уже реализованы и targeted-тесты зелёные, не останавливайся с вопросом. Выполни критический review текущей реализации на расхождения с инвариантами, исправь найденное, затем запусти targeted checks.
8. Вопрос пользователю задавай только если без ответа невозможно выбрать между двумя несовместимыми runtime-изменениями с риском потери данных или изменения публичного поведения.

## Python и проверки

Используй только команды из `D:\Projects\hometutor`:

```powershell
.\.venv\Scripts\python.exe -m pytest <targeted tests>
.\.venv\Scripts\python.exe -m ruff check <changed files>
```

- Запускай только targeted-тесты по затронутым зонам.
- Полный pytest-suite не запускай без явной просьбы.
- Если ruff недоступен из-за sandbox/tooling, сообщи это в финале.

## Критичные инварианты реализации

- `mastery_vector` должен использовать только canonical concept id из active knowledge graph.
- Не писать в `mastery_vector` свободный текст, названия тегов, human topic title или имя файла.
- Если сигнал пришёл из tutor/flashcard, сначала сопоставь его с canonical cid; если cid не найден — не загрязняй `mastery_vector`.
- `sessions_completed` = только завершённые учебные сессии/quiz-path. Tutor/flashcard события считать отдельными interaction-счётчиками.
- Не менять старую семантику quiz без явного задания: quiz может перезаписывать mastery score, включая понижение.
- Не добавлять LLM там, где достаточно deterministic/persistence/state update.
- Не добавлять новые экраны, если задача требует невидимую state/persistence доработку.
- Provider honesty: не включать cloud fallback без явного решения владельца.
- Config читать только через runtime config-layer согласно `AGENTS.md` / `docs/conventions.md`.

## Карта направлений для ориентира

Используй эту карту как ориентир. Если пользователь не выбрал направление, бери пункт 10 как default. Не ищи внешние планы.

1. Knowledge Fate / петля памяти: tutor/flashcard/quiz должны оставлять корректный учебный след.
2. First Ten Minutes / onboarding: первый экран и первые действия должны быть честными и понятными.
3. Material as Product: конспект, источники, граф, таймкоды должны ощущаться как продукт.
4. Agent as One Button: агент должен иметь понятную UI-дверь, а не скрытый флаг.
5. Trust Under Load / provider: сбои LLM должны давать быстрый честный отказ, а не долгие подвисания.
6. Infographics / living map: карта должна отражать реальное состояние материала и прогресса.
7. Learning Plan: «программа обучения» и «план на сегодня» не должны конфликтовать.
8. Invisible Half: невидимые контуры — память, честность, recovery, state; базовые провода уже закрыты, теперь нужна видимость.
9. Color Worlds: визуальные миры и присвоение пространства.
10. Full Circle: показать уже работающую петлю на экране; default — `wave-full-circle-pulse`.

## Задача сессии

1. Прочитай runtime-инструкции и релевантный код.
2. Определи ближайшее runtime-исправление из запроса пользователя или аудита в чате. Если конкретики нет, автоматически выбери default continuation target выше.
3. Реализуй его только в `D:\Projects\hometutor`; не завершай ответ просьбой выбрать направление, пока есть проверяемая runtime-работа из default target.
4. Обнови runtime-docs только при необходимости.
5. Запусти targeted-тесты и ruff по изменённым runtime-файлам, если доступно.
6. В финале дай:
   - состояние рабочего дерева на старте;
   - что реализовано;
   - изменённые runtime-файлы;
   - тесты и результат;
   - что осталось;
   - короткий следующий runtime-шаг без внешних процессных команд.
