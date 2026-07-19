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
| `PAIN-03` | Провода без поверхности | Данные и логика уже существуют, но студент не видит результата и не может им воспользоваться? | №8: невидимая половина; №10: learner trace и due-сигнал; №20: возможности продукта без дверей из мира |
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
```
