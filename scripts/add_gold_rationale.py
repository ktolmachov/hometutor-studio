"""E11-Q: add gold_rationale to all router_eval cases in tutor_regression.json (v1.3 -> v1.4)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "eval_data" / "tutor_regression.json"
d = json.loads(p.read_text(encoding="utf-8"))

RATIONALES = {
    "tutor_01": (
        "MicroQuizGenerator: student asks 'how does X work' without history. "
        "Active recall > re-explain: MicroQuizGenerator reveals gaps more precisely than ConceptExplainer guessing starting level. "
        "Not ConceptExplainer — it assumes student is unfamiliar; a quiz tests this first."
    ),
    "tutor_02": (
        "SocraticQuestioner: question asked after prior BM25 explanation (history present). "
        "After explanation — deepen via probing, not re-explain. "
        "Not ConceptExplainer — history already provides context; repeating = overteaching."
    ),
    "tutor_03": (
        "ConceptExplainer: hint mode — provide partial structure/explanation without full solution. "
        "Not SocraticQuestioner — hint_gradation provides directional guidance, not questions back."
    ),
    "tutor_04": (
        "ConceptExplainer: previous_quiz_score=0.85, streak=2 — student ready to advance from recognition to recall. "
        "ConceptExplainer with deeper level; adaptive progression. "
        "Not MicroQuizGenerator — new quiz comes after the advanced explanation, not before."
    ),
    "tutor_05": (
        "MicroQuizGenerator: 'повтори X' is an explicit SM-2 / spaced repetition trigger. "
        "Activating memory via recall-quiz is more effective than re-explaining (desirable difficulty principle). "
        "Not ConceptExplainer — re-explain on 'review' request violates active recall contract."
    ),
    "tutor_06": (
        "MotivationCoach: student requests progress overview — motivational/reflective moment. "
        "MotivationCoach connects mastery to goals, reinforces intrinsic motivation. "
        "Not ConceptExplainer — no concept explanation requested."
    ),
    "tutor_07": (
        "ConceptExplainer: 'show me the solution plan' — scaffold, not full solution. "
        "ConceptExplainer in plan mode gives steps without full code. "
        "Not SocraticQuestioner — student already requested scaffold; asking more questions would frustrate."
    ),
    "tutor_08": (
        "ConceptExplainer: question about adaptive plan and gaps — informational request. "
        "ConceptExplainer structures learning plan and explains priorities. "
        "Not MotivationCoach — no emotional trigger; information is needed."
    ),
    "tutor_09": (
        "SocraticQuestioner (challenge): 'what if 10000 documents?' — counterfactual/scaling question. "
        "Correct response: challenge student to think through scaling consequences themselves. "
        "Not ConceptExplainer — providing a ready answer to 'what if' kills independent reasoning."
    ),
    "tutor_10": (
        "MicroQuizGenerator: quiz_score=0.4 — failure. Pedagogical tactic: not ErrorDiagnoser first, "
        "but MicroQuizGenerator with level_downgrade to recall. Restore confidence with easier success, "
        "then diagnose errors. Not ErrorDiagnoser — diagnosing without confidence rebuild demoralizes."
    ),
    "tutor_11": (
        "ConceptExplainer: long history, student requests condensed summary of retrieval discussion. "
        "ConceptExplainer synthesizes and reformulates — condensed question integrity. "
        "Not SocraticQuestioner — student requests information, not a question."
    ),
    "tutor_12": (
        "ConceptExplainer: after long session (15+ messages), student asks how to continue. "
        "ConceptExplainer provides consolidation: structured explanation best anchors a long session. "
        "Not MicroQuizGenerator — quiz without consolidation after 15 messages overloads cognitive load."
    ),
    "tutor_13": (
        "ConceptExplainer: prerequisites in knowledge graph — informational query about knowledge structure. "
        "ConceptExplainer with graph_overlay explains prerequisites and connections. "
        "Not SocraticQuestioner — student explicitly requested information, not a check."
    ),
    "tutor_14": (
        "ErrorDiagnoser: student chose wrong answer and asks to explain their logical error. "
        "ErrorDiagnoser diagnoses the misconception in reasoning — exact fit. "
        "Not ConceptExplainer — targeted diagnosis needed, not general re-explanation."
    ),
    "tutor_15": (
        "ConceptExplainer: request for full cycle explain->check->practice. "
        "ConceptExplainer as first cycle step — anchors subsequent quiz and homework. "
        "Not MicroQuizGenerator — quiz without explanation is no-context quiz."
    ),
    "tutor_16": (
        "ConceptExplainer: 'what is RAG pipeline?' — basic conceptual request. "
        "ConceptExplainer fulfills tutor_cycle_contract (phase, quiz_state, review_state). "
        "Only correct agent for direct 'what is X' question."
    ),
    "tutor_17": (
        "SocraticQuestioner: 'solve the whole task for me' — anti-overhelp case. "
        "Rule: explicit 'solve for me' request => scaffold first via SocraticQuestioner. "
        "Not ConceptExplainer — it would give explanation + answer, violating anti-overhelp contract."
    ),
    "tutor_18": (
        "ErrorDiagnoser: student states incorrect belief ('RAG is just vector search'). "
        "Misconception requires diagnosis and correction, not general explanation. "
        "Not ConceptExplainer — explaining without naming the error may reinforce misconception."
    ),
    "tutor_19": (
        "MotivationCoach: 'I am tired and want to stop' — explicit emotional trigger (fatigue). "
        "MotivationCoach handles emotional_state=tired/frustrated, suggests micro-step to continue. "
        "Not ConceptExplainer — no knowledge request; emotional need is primary."
    ),
    "tutor_20": (
        "MicroQuizGenerator: explicit 'give me a self-check question' = direct MicroQuizGenerator trigger. "
        "Not ConceptExplainer — student asks for a question to test themselves, not an explanation."
    ),
    "tutor_21": (
        "ErrorDiagnoser: 'I am sure BM25 is not needed' — misconception with high confidence (overconfidence). "
        "ErrorDiagnoser diagnoses and corrects nuanced misconception more effectively than ConceptExplainer. "
        "Not ConceptExplainer — overconfident misconception needs explicit diagnosis, not plain explanation."
    ),
    "tutor_22": (
        "ConceptExplainer: 'explain in simple terms' — explicit beginner explanation request. "
        "ConceptExplainer with depth=beginner_friendly. Unambiguous case."
    ),
    "tutor_23": (
        "SocraticQuestioner (probing): student poses an implications question ('what consequences do YOU see?'). "
        "Correct response: not explain (ConceptExplainer), but continue the reasoning chain via probing — "
        "make student articulate consequences themselves. "
        "Not ConceptExplainer — providing a ready list of consequences instead of probing = overteaching."
    ),
    "tutor_24": (
        "MotivationCoach: 'accomplished a lot today, how to consolidate without burnout' — positive emotional state. "
        "MotivationCoach reinforces success and suggests sustainable strategy. "
        "Not ConceptExplainer — no knowledge request; motivational support is needed."
    ),
    "tutor_25": (
        "MicroQuizGenerator: 'quick drill' — explicit keyword. "
        "Not ConceptExplainer — student wants practice/drill, not explanation."
    ),
    "tutor_26": (
        "ConceptExplainer: 'compare X and Y in two sentences' — informational contrast request. "
        "ConceptExplainer with format=contrast. Unambiguous case."
    ),
}

for case in d["test_cases"]:
    cid = case["id"]
    if cid in RATIONALES:
        case["router_eval"]["gold_rationale"] = RATIONALES[cid]

d["version"] = "1.4"
d["timestamp"] = "2026-04-11"
d["description"] = (
    "Regression dataset для tutor mode (19.2 + E6.4) + router_eval gold (E10.3/E11-Q). "
    "Покрывает quiz, Socratic, homework, adaptive difficulty, spaced repetition, mastery recommendations, "
    "anti-overhelp и misconception-handling. "
    "v1.4: добавлен gold_rationale ко всем 26 кейсам (E11-Q)."
)

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
n = len(d["test_cases"])
missing = [c["id"] for c in d["test_cases"] if not c["router_eval"].get("gold_rationale")]
print(f"Written {n} cases, version={d['version']}")
print(f"Missing rationale: {missing or 'none'}")
