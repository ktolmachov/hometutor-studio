# Level 1: Local ML Layer — 5-Minute Quick Start

**Дата:** 2026-05-08  
**Цель:** Запустить Level 1 за 5 минут без чтения полной документации

---

## ⚡ Quick Start (5 минут)

### Step 1: Проверить prerequisites (30 секунд)

```powershell
# Проверить Python и venv
.\.venv\Scripts\python.exe --version
# Ожидается: Python 3.9+

# Проверить sklearn
.\.venv\Scripts\python.exe -c "import sklearn; print(sklearn.__version__)"
# Ожидается: 1.0+

# Проверить user_state.db
Test-Path data/user_state.db
# Ожидается: True
```

**Если что-то не работает:**
```powershell
# Установить sklearn
.\.venv\Scripts\python.exe -m pip install scikit-learn joblib pandas
```

---

### Step 2: Собрать данные (1 минута)

```powershell
# Собрать training data из user_state.db
.\.venv\Scripts\python.exe scripts/ml/data_collection_ssr.py \
    --output data/ml/ssr_forgetting_curve_train.parquet

# Проверить размер данных
.\.venv\Scripts\python.exe scripts/ml/data_collection_ssr.py --validate
```

**Ожидаемый вывод:**
```
✅ Collected 1234 samples
✅ Train set: 987 samples (80%)
✅ Test set: 247 samples (20%)
✅ Features: 9
✅ Target: retention_probability (0-1)
```

**Если данных мало (< 1000 samples):**
```powershell
# Генерировать synthetic data
.\.venv\Scripts\python.exe scripts/ml/generate_synthetic_ssr_data.py \
    --output data/ml/ssr_forgetting_curve_train.parquet \
    --samples 1000
```

---

### Step 3: Обучить модель (2 минуты)

```powershell
# Обучить Logistic Regression
.\.venv\Scripts\python.exe scripts/ml/train_ssr_forgetting_curve.py \
    --train data/ml/ssr_forgetting_curve_train.parquet \
    --test data/ml/ssr_forgetting_curve_test.parquet \
    --output models/ssr_forgetting_curve_v1.pkl
```

**Ожидаемый вывод:**
```
Training Logistic Regression...
CV AUC-ROC: 0.78 ± 0.03
Test AUC-ROC: 0.76
Model size: 0.8 MB
✅ Model saved to models/ssr_forgetting_curve_v1.pkl
```

**Если AUC-ROC < 0.75:**
- Проверить качество данных (`--validate`)
- Увеличить training samples (synthetic data)
- Попробовать XGBoost (см. Full Guide)

---

### Step 4: Запустить evaluation (1 минута)

```powershell
# Запустить evaluation harness
.\.venv\Scripts\python.exe scripts/ml/eval_ssr_forgetting_curve.py \
    --model models/ssr_forgetting_curve_v1.pkl \
    --test data/ml/ssr_forgetting_curve_test.parquet \
    --output archive/ml_eval/ssr_forgetting_curve_v1_report.md
```

**Ожидаемый вывод:**
```
✅ AUC-ROC: 0.76 (target: ≥ 0.75) PASS
✅ Precision@5: 0.82 (target: ≥ 0.80) PASS
✅ Recall@5: 0.73 (target: ≥ 0.70) PASS
✅ Inference latency p95: 12ms (target: < 50ms) PASS
✅ Model size: 0.8MB (target: < 1MB) PASS

Report saved to archive/ml_eval/ssr_forgetting_curve_v1_report.md
```

---

### Step 5: Интегрировать в SSR (30 секунд)

```powershell
# Модель уже сохранена в models/ssr_forgetting_curve_v1.pkl
# SSR автоматически загрузит её при старте

# Проверить интеграцию
.\.venv\Scripts\python.exe -c "
from app.ui.adaptive_plan_card import _load_ml_model
model = _load_ml_model()
print('✅ Model loaded' if model else '❌ Model not found')
"
```

**Ожидаемый вывод:**
```
✅ Model loaded
```

---

## ✅ Done! (5 минут)

Level 1 готов к использованию! 🎉

**Что дальше:**
1. Запустить SSR и проверить ML reranking в action
2. Мониторить metrics (inference latency, fallback rate)
3. Retrain модель каждую ночь (cron job)

---

## 🔍 Troubleshooting

### Проблема: "No module named 'sklearn'"

**Решение:**
```powershell
.\.venv\Scripts\python.exe -m pip install scikit-learn
```

### Проблема: "Insufficient data (< 1000 samples)"

**Решение:**
```powershell
# Генерировать synthetic data
.\.venv\Scripts\python.exe scripts/ml/generate_synthetic_ssr_data.py \
    --output data/ml/ssr_forgetting_curve_train.parquet \
    --samples 1000
```

### Проблема: "AUC-ROC < 0.75"

**Решение:**
1. Проверить качество данных (`--validate`)
2. Увеличить training samples
3. Попробовать XGBoost:
```powershell
.\.venv\Scripts\python.exe scripts/ml/train_ssr_forgetting_curve.py \
    --model xgboost \
    --train data/ml/ssr_forgetting_curve_train.parquet \
    --output models/ssr_forgetting_curve_v1.pkl
```

### Проблема: "Model not found"

**Решение:**
```powershell
# Проверить путь
Test-Path models/ssr_forgetting_curve_v1.pkl

# Если нет → retrain
.\.venv\Scripts\python.exe scripts/ml/train_ssr_forgetting_curve.py \
    --train data/ml/ssr_forgetting_curve_train.parquet \
    --output models/ssr_forgetting_curve_v1.pkl
```

---

## 📚 Full Documentation

Для детального понимания читайте:
- [`ssr_ai_vision_level1_prompt.md`](ssr_ai_vision_level1_prompt.md) — Copy-Paste Prompt
- [`smart_study_router.md`](../smart_study_router.md) — Level 1 Deep Dive

---

**Версия:** 1.0  
**Дата:** 2026-05-08  
**Время:** 5 минут
