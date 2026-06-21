# Eval data (defense golden set)

`defense_eval_questions.json` — защитно-ориентированный golden eval: шесть категорий
(qa, keyword, overview, synthesis, negative, injection), минимум по три кейса на категорию,
уникальные `id`, проверяемые `expected_characteristics`. Категория `injection` ссылается на
файлы в `adversarial/injection/` как на контролируемые источники с попытками prompt injection.
