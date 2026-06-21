# SSR LLM Explanation Rubric

Use this rubric for SSR Level 2 human evaluation. Each generated explanation is
rated by 3 humans on a 1-5 Likert scale.

## Rating Dimensions

| Dimension | 1 | 3 | 5 |
|---|---|---|---|
| Clarity | Confusing or too vague | Understandable but generic | Immediately clear why this action matters now |
| Personalization | No user context | Mentions one context signal | Uses recent activity and local learning state naturally |
| Pedagogical Value | Says what to do only | Mentions review/practice broadly | Explains timing, learning benefit, and next memory risk |
| Accuracy | Adds unsupported facts | Mostly faithful with minor overreach | Uses only provided facts and preserves SSR decision |

## Hard Fails

Mark the scenario as failed even if the prose is polished when the explanation:

- changes the recommended action, route, or priority;
- invents dates, topics, quiz scores, retention percentages, or user history;
- exceeds 150 words;
- sounds punitive, manipulative, or overconfident;
- hides that local SSR signals are limited.

## Aggregation

Primary score: mean of `clarity` across all 150 ratings.

Supporting score: report mean values for personalization, pedagogical value, and
accuracy. The package passes only when clarity is at least 4.0 and no accuracy
rating is below 3.
