from app.services.screening import (
    build_gaps,
    build_strengths,
    derive_score,
    extract_skills,
    generate_rubric,
)


def _rubric():
    return [
        {"id": "r1", "label": "Go", "description": "", "tag": "Must-have", "category": "Technical Skills", "weight": 20},
        {"id": "r2", "label": "PostgreSQL", "description": "", "tag": "Must-have", "category": "Technical Skills", "weight": 15},
        {"id": "r3", "label": "Kubernetes", "description": "", "tag": "Must-have", "category": "Technical Skills", "weight": 15},
        {"id": "r4", "label": "Redis", "description": "", "tag": "Nice-to-have", "category": "Technical Skills", "weight": 5},
    ]


def test_derive_score_full_coverage():
    result = derive_score(_rubric(), ["Go", "PostgreSQL", "Kubernetes", "Redis"])
    assert result["score"] == 99
    assert result["compare_verdict"] == "Advance"
    assert result["shortlisted"] is True
    assert "5 of 5" not in result["ai_note"]
    assert "must-have skills covered" in result["ai_note"]


def test_derive_score_partial_coverage():
    result = derive_score(_rubric(), ["Go", "PostgreSQL"])
    # 30 + 65*(35/50) = 75.5 -> half-to-even rounds to 76? 75.5 rounds to 76 (banker's to even = 76 is even? 75.5 -> 76 even). Actually banker's rounds .5 to even, 75.5 -> 76? nearest even of {75,76} is 76. Yes 76.
    assert result["score"] == 76
    assert result["compare_verdict"] == "Maybe"
    assert result["shortlisted"] is False


def test_derive_score_no_match():
    result = derive_score(_rubric(), ["Python"])
    assert result["score"] == 30
    assert result["compare_verdict"] == "Pass"


def test_scorecard_sorted_by_weight_desc():
    result = derive_score(_rubric(), ["Go"])
    weights = [row["weight"] for row in result["scorecard"]]
    assert weights == sorted(weights, reverse=True)


def test_build_strengths_gaps():
    result = derive_score(_rubric(), ["Go"])
    assert "Go evidenced directly on the resume." in build_strengths(result["scorecard"])
    assert any("PostgreSQL" in gap for gap in build_gaps(result["scorecard"]))


def test_extract_skills_multiword_priority():
    skills = extract_skills("I am great with React Native and React.")
    assert skills.index("React Native") < skills.index("React")


def test_extract_skills_case_insensitive():
    assert "Go" in extract_skills("working with go and postgresql")


def test_generate_rubric_from_description():
    rubric = generate_rubric("We require Go and Kubernetes. Experience with Redis is a plus.")
    labels = [r["label"] for r in rubric]
    assert "Go" in labels
    assert "Kubernetes" in labels
    assert sum(r["weight"] for r in rubric) == 100


def test_generate_rubric_required_hint():
    rubric = generate_rubric("Must have experience with Go and Kubernetes.")
    go = next(r for r in rubric if r["label"] == "Go")
    assert go["tag"] == "Must-have"
