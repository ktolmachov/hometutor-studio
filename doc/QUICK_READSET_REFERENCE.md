# Быстрая Справка: Check ReadSet (1-минутная версия)

## 🎯 Перед Каждым LLM-Вызовом

```bash
python scripts/check_readset.py <file1> <file2> ... [--signatures]
```

**Exit codes:**
- `0` = ✅ SAFE (отправляй смело)
- `1` = ⚠️ WARN (сжать и переделать)
- `2` = 🔴 BLOCK (перезапусти с меньшим read-set)

---

## 📋 Быстрый Чек-Лист

- [ ] Read-set ≤ 5 файлов?
- [ ] Ни один файл не читается целиком, если он >600 строк?
- [ ] Запущено: `python scripts/check_readset.py ... ✅ SAFE`?
- [ ] Нет папок целиком (doc/epochs/, doc/user_stories/, etc.)?

Если все ✅ → отправляй.

---

## 🚨 Красные Флаги

| Флаг | Действие |
|---|---|
| `❌ FORBIDDEN` на файл | Используй safe-method из колонки справа (grep, head, конкретная секция) |
| `⚠️ LARGE` и >600 строк | Используй `--signatures` и grep вместо полного чтения |
| Total > 12k | Убрать файлы или заменить на summaries |
| Total > 20k | Перезапусти с меньшим read-set, не retry |

---

## 💡 Типовые Шаблоны (Копируй-Вставляй)

### ✅ Planning задача
```bash
python scripts/check_readset.py \
  doc/tasklist.md \
  doc/conventions.md
# Результат: SAFE (~2–3k)
```

### ✅ Execution задача
```bash
python scripts/check_readset.py \
  doc/tasklist.md \
  doc/conventions.md
# Результат: SAFE (~2–3k)
```

### ✅ Verify задача
```bash
python scripts/check_readset.py \
  doc/tasklist.md
# Результат: SAFE (~1k)
```

### ❌ Плохой вызов (BLOCK)
```bash
python scripts/check_readset.py \
  app/query_service.py \
  app/knowledge_graph.py \
  app/prompts.py \
  doc/closed_iterations.md \
  doc/adr.md

# Результат: 🔴 BLOCK (65k > 20k)
# Действие: перезапусти с меньшим read-set
```

---

## 📖 Полная Справка

См. [`doc/token_safety.md`](token_safety.md) для:
- Таблиц запрещённых файлов
- Таблиц безопасных комбинаций
- Примеров compression
- FAQ

---

## Exit Code Поведение

```bash
python scripts/check_readset.py app/query_service.py
if [ $? -eq 0 ]; then
  echo "✅ SAFE — send prompt"
elif [ $? -eq 1 ]; then
  echo "⚠️ WARN — compress and retry"
else
  echo "🔴 BLOCK — redesign read-set"
fi
```

---

## Дополнительные Флаги

```bash
# С рекомендациями для больших файлов
python scripts/check_readset.py app/query_service.py --signatures

# Custom soft limit
python scripts/check_readset.py --budget 6000 app/query_service.py

# Custom hard limit
python scripts/check_readset.py --hard 15000 app/query_service.py

# Без system overhead (если уже учтён в контексте)
python scripts/check_readset.py --overhead 0 app/query_service.py
```

---

## Инструментальная Интеграция (Coming Soon)

Планируется добавить в `.claude/settings.json`:

```json
{
  "hooks": {
    "before_llm_call": {
      "command": "python scripts/check_readset.py",
      "auto_check": true,
      "fail_on_block": true
    }
  }
}
```

Тогда проверка будет запускаться автоматически перед каждым вызовом.

---

Дата: 2026-04-19  
Версия: v1.0

