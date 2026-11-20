import pytest

from dispute_triage.evaluation.agreement import agreement_from_csv, cohens_kappa


def test_perfect_agreement():
    assert cohens_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0


def test_known_value():
    # Classic 2x2 example: 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no -> kappa = 0.4
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert cohens_kappa(a, b) == pytest.approx(0.4, abs=1e-4)


def test_chance_level_is_zero():
    assert cohens_kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"]) == 0.0


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        cohens_kappa(["a"], ["a", "b"])


def test_from_csv_lists_disagreements(tmp_path):
    p = tmp_path / "dl.csv"
    p.write_text("complaint_id,labeler_a_root_cause,labeler_b_root_cause\n"
                 "1,duplicate_processing,duplicate_processing\n2,other,cancelled_recurring\n3,,other\n")
    out = agreement_from_csv(str(p))
    assert out["n"] == 2 and out["raw_agreement"] == 0.5 and out["to_adjudicate"] == ["2"]
