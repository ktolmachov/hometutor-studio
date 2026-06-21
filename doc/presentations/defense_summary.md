# home-rag_v2 — Итоговое резюме трёх виртуальных защит

> **Проект:** home-rag_v2 · Персональный учебный ассистент на основе ваших материалов  
> **Дата:** май 2026  
> **Формат:** Резюме трёх раундов виртуальной защиты

---

## 📋 Обзор защит

Проект прошёл три раунда виртуальной защиты с разными типами судей:

1. **🎓 Защита перед руководителем и студентами** ([defense_virtual_defense.md](defense_virtual_defense.md))
   - 20 вопросов от руководителя
   - 5 вопросов от студентов-наблюдателей
   - Фокус: техническая корректность, архитектурные решения, завершённость

2. **🧑‍⚖️ Защита перед экспертной панелью** ([defense_expert_panel.md](defense_expert_panel.md))
   - 8 экспертов: RAG Architect, Retrieval Scientist, LLM Evaluation Lead, AI Safety Engineer, MLOps Lead, Privacy Engineer, Educational AI Researcher, Product Reviewer
   - Фокус: глубокие технические вопросы, eval-методология, security, privacy, learning outcomes

3. **👥 Защита перед пользователями** ([defense_user_panel.md](defense_user_panel.md))
   - 10 персон: от новичков до power users, включая хейтеров, конкурентов и критиков
   - Фокус: реальные боли, usability, сравнение с конкурентами, доступность

---

## 🎯 Ключевые выводы

### ✅ Сильные стороны проекта (подтверждены всеми панелями)

1. **Полный учебный цикл** — это не просто RAG-чат и не просто SRS-система, а интеграция: `answer → tutor → quiz → SRS → mastery → plan`
2. **Архитектурная зрелость** — чёткие границы (provider, config, prompts, router, guardrails), инварианты, DoD
3. **Local-first** — индекс и state на машине пользователя; полный offline возможен с локальными LLM
4. **Гибкость** — переключение local ↔ cloud через `.env` без изменения кода
5. **Честность** — явное признание ограничений, trade-offs и зон риска
6. **Паттерн умного роутера** — одна точка входа, которая снимает вопрос "что делать дальше"; этот же паттерн можно перенести в учебный UX

---

### ⚠️ Слабые места и зоны улучшения

#### 1. Eval и доказательство качества

**Проблема (экспертная панель):**
- Нет опубликованного eval-run с baseline
- Нет сравнения `vector_only` vs `hybrid` vs `doc_then_chunk` на одном dataset
- Нет численных доказательств learning outcomes

**Решение:**
- Зафиксировать eval dataset: qa, keyword, overview, synthesis, negative, injection
- Прогнать retrieval metrics: recall@k, MRR, hit rate, latency
- Добавить educational metrics: retention, transfer, quiz outcomes
- Опубликовать baseline JSON и regression gate

---

#### 2. Onboarding и доступность

**Проблема (пользовательская панель):**
- Установка требует Python, терминал, настройку `.env`
- Не для всех пользователей, особенно нетехнических

**Решение:**
- Desktop installer с GUI (Windows `.exe`, macOS `.dmg`, Linux `.AppImage`)
- Onboarding wizard: выбор LLM, первая индексация, demo-сценарий
- Quickstart video или interactive tutorial

---

#### 3. Сравнение с конкурентами

**Проблема (пользовательская панель):**
- NotebookLM делает Q&A бесплатно и без установки
- Anki лучше в SRS
- Не всегда понятно, зачем менять работающий workflow

**Решение:**
- Чёткое позиционирование: "единственный инструмент с полным учебным циклом"
- Сравнительная таблица в презентации (добавлена в Слайд 10)
- Killer demo: от вопроса до mastery за 3 минуты

---

#### 4. Security и privacy

**Проблема (экспертная панель):**
- Document-borne prompt injection не покрыт input guardrails
- Cloud LLM режим передаёт фрагменты провайдеру
- Нет audit logs для compliance

**Решение:**
- Document-level sanitization и adversarial corpus
- Явный disclaimer: "local-first storage; inference privacy depends on provider"
- Audit trail для enterprise: кто, когда, какой документ, какой вопрос

---

#### 5. Групповые функции

**Проблема (пользовательская панель):**
- Преподаватели не могут использовать для класса
- Нет dashboard прогресса группы
- Нет экспорта в Anki для power users

**Решение:**
- Multi-user backend (следующий major scope)
- Teacher dashboard с progress aggregation
- Экспорт в Anki через AnkiConnect API

---

## 📊 Матрица улучшений по приоритетам

| Улучшение | Приоритет | Сложность | Impact | Для кого |
|---|---|---|---|---|
| **Eval baseline + retrieval metrics** | 🔴 Высокий | Средняя | Доказательство качества | Академическая защита, эксперты |
| **Desktop installer + onboarding** | 🔴 Высокий | Высокая | Доступность для нетехнических | Новички, массовый рынок |
| **Сравнительная таблица в презентации** | 🟢 Низкий | Низкая | Чёткое позиционирование | Все аудитории |
| **Killer demo сценарий** | 🟢 Низкий | Низкая | Убедительность защиты | Академическая защита |
| **Экспорт в Anki** | 🟡 Средний | Средняя | Интеграция с workflow | Power users |
| **Document-level security** | 🟡 Средний | Средняя | Enterprise-готовность | Корпоративные пользователи |
| **Multi-user backend** | 🔵 Низкий | Очень высокая | Групповое использование | Преподаватели, команды |
| **Learning outcomes research** | 🔵 Низкий | Очень высокая | Научное доказательство | Академическое сообщество |

---

## 🎓 Рекомендации для академической защиты

### 1. Структура презентации (11 слайдов)

✅ **Слайд 1:** Проблема и решение — фрагментация учебного процесса  
✅ **Слайд 2:** Архитектура — 4 слоя, инварианты  
✅ **Слайд 3:** RAG pipeline — 5 ступеней, eval-контур  
✅ **Слайд 4:** Учебный цикл — от вопроса до квиза  
✅ **Слайд 5:** Прогресс и mastery tracking  
✅ **Слайд 6:** Local vs Cloud LLM  
✅ **Слайд 7:** Процесс разработки — AI-assisted workflow  
✅ **Слайд 8:** Идеи развития — 5 концептов  
✅ **Слайд 9:** Для кого этот проект — fit-анализ  
✅ **Слайд 10:** Сравнение с конкурентами — таблица  
✅ **Слайд 11:** Связанные документы

---

### 2. Killer Demo (3 минуты)

**Сценарий:**
1. Загрузка материала или готовый индекс: показать, что источник локальный и пользовательский.
2. Сложный вопрос: синтез из нескольких фрагментов, не поиск одного определения.
3. Ответ с источниками: citations, confidence, проверяемые фрагменты.
4. "Учить эту тему": переход из Q&A в tutor.
5. Tutor → quiz → flashcard: понимание, проверка, запоминание.
6. Mastery dashboard → adaptive plan: следующий персональный шаг.

**Что это доказывает:** Полный учебный цикл в одном инструменте: источник → объяснение → проверка → запоминание → план.

Подробный сценарий, реплики докладчика, риски live-demo и лог идеальной сессии: [`defense_killer_demo.md`](defense_killer_demo.md).

---

### 3. Ответы на сложные вопросы

**"Почему не просто ChatGPT?"**  
→ ChatGPT не знает ваших материалов, не создаёт квизы, не ведёт SRS, не строит план повторения.

**"Почему не NotebookLM?"**  
→ NotebookLM силён в Q&A, но не закрывает учебный цикл: нет quiz, SRS, mastery, плана.

**"Где доказательства качества?"**  
→ Есть eval-инфраструктура и методика; численные метрики показываются по конкретному eval-run.

**"Где доказательства learning outcomes?"**  
→ Нет опубликованных исследований; это следующий шаг для научной валидации.

**"Это production-ready?"**  
→ Production-oriented для локального one-user сценария; internet-scale требует отдельной infra.

---

### 4. Честные ограничения

✅ **BM25 in-memory** — риск RAM на больших корпусах  
✅ **OCR/PDF parsing** — качество зависит от источника  
✅ **Локальные модели** — слабее cloud frontier-моделей  
✅ **Confidence** — не вероятность истинности, а retrieval signal  
✅ **Onboarding** — требует технических навыков  
✅ **Групповые функции** — пока нет  

---

## 🚀 Roadmap после защиты

### Immediate (для защиты)

- [x] Три виртуальные защиты с разными панелями
- [x] Улучшения презентации: новые слайды, сравнительная таблица, fit-анализ
- [x] Killer demo сценарий
- [x] Честные ограничения и trade-offs

### Short-term (следующие 2 недели)

- [ ] Eval baseline: зафиксировать dataset, прогнать retrieval metrics
- [ ] Latency/cost breakdown по стадиям pipeline
- [ ] Adversarial corpus: prompt injection, no-answer, conflicting sources
- [ ] Quickstart video или interactive tutorial

### Mid-term (следующие 2 месяца)

- [ ] Desktop installer с GUI (Windows/macOS/Linux)
- [ ] Onboarding wizard
- [ ] Экспорт в Anki через AnkiConnect
- [ ] Multilingual eval (русский, английский, китайский)

### Long-term (следующие 6 месяцев)

- [ ] Learning outcomes research с участниками
- [ ] Multi-user backend для преподавателей
- [ ] Document-level security и audit logs
- [ ] Peer-reviewed publication

---

## 💡 Главный вывод

**Проект технически зрелый и решает реальную проблему — фрагментацию учебного процесса.**

Сильные стороны:
- Полный учебный цикл (уникально)
- Архитектурная зрелость (инварианты, границы, DoD)
- Local-first (приватность, offline)
- Честность (явные ограничения и trade-offs)

Зоны улучшения:
- Eval baseline и доказательство качества
- Onboarding для нетехнических пользователей
- Smart Study Router: умная подсказка следующего учебного шага
- Learning outcomes research
- Групповые функции для преподавателей

**Для академической защиты проект готов.** Следующие шаги — усиление eval-контура, упрощение onboarding и перенос прорыва workflow-роутера в пользовательский сценарий: `learning state → next_action + reason + кнопка`.

---

## 📚 Связанные документы

- 📘 [defense_presentation.md](defense_presentation.md) — Основная презентация (11 слайдов)
- 🎓 [defense_virtual_defense.md](defense_virtual_defense.md) — Защита перед руководителем
- 🧑‍⚖️ [defense_expert_panel.md](defense_expert_panel.md) — Защита перед экспертами
- 👥 [defense_user_panel.md](defense_user_panel.md) — Защита перед пользователями

---

<sub>📅 Документ подготовлен как итоговое резюме трёх виртуальных защит · май 2026</sub>
