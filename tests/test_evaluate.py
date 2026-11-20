from dispute_triage.classify.rules import RulesClassifier
from dispute_triage.evaluation.evaluate import evaluate, load_gold, to_markdown
from dispute_triage.evaluation.sampling import stratified_sample
from tests.conftest import FIX


def test_evaluate_report_shape(settings, complaints):
    preds = [RulesClassifier(settings).classify(c) for c in complaints]
    rep = evaluate(preds, load_gold(FIX / "gold_labels.csv"))
    assert rep.n == 10
    assert 0 <= rep.metrics["root_cause_accuracy"] <= 1
    assert set(rep.acceptance) >= {"root_cause_accuracy", "fraud_recall", "max_review_rate"}
    assert "Evaluation report" in to_markdown(rep)


def test_perfect_predictions_pass_accuracy(settings, complaints):
    gold = load_gold(FIX / "gold_labels.csv")
    from dispute_triage.classify.base import finalize
    preds = [finalize(c, {"root_cause": gold[c.complaint_id][0].value, "priority": gold[c.complaint_id][1].value,
                          "confidence": 0.99, "rationale": "", "evidence_quote": None}, "oracle", settings)
             for c in complaints]
    rep = evaluate(preds, gold)
    assert rep.metrics["root_cause_accuracy"] == 1.0 and rep.metrics["fraud_recall"] == 1.0


def test_stratified_sample_deterministic(complaints):
    a = [c.complaint_id for c in stratified_sample(complaints, 5, seed=1)]
    b = [c.complaint_id for c in stratified_sample(complaints, 5, seed=1)]
    assert a == b and len(a) == 5
