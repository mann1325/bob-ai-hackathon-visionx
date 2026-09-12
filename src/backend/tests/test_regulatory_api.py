from rules.definitions import ACTIVE_RULES
from rules.engine import evaluate_rules


def test_list_regulatory_rules(client):
    response = client.get("/api/v1/regulatory-rules")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 5

    rule_ids = {r["rule_id"] for r in body}
    assert "REG-001" in rule_ids
    assert "REG-002" in rule_ids
    assert "REG-003" in rule_ids
    assert "REG-004" in rule_ids
    assert "REG-005" in rule_ids

    doc_types = {r["target_document_type"] for r in body}
    assert "Product Label" in doc_types
    assert "PSUR / PBRER" in doc_types
    assert "Risk Management Plan (RMP)" in doc_types
    assert "Reference Safety Information (RSI)" in doc_types
    assert "Relevant CTD safety content" in doc_types


def test_signal_regulatory_impact_multiple_matches(client):
    # sig-001 has: PRR 3.4, count 120, trend 0.85, priority high, status candidate
    response = client.get("/api/v1/signals/sig-001/regulatory-impact")
    assert response.status_code == 200
    body = response.json()

    assert body["signal_id"] == "sig-001"
    assert body["human_review_required"] is True

    matched_rule_ids = {m["rule_id"] for m in body["rule_matches"]}
    assert "REG-001" in matched_rule_ids
    assert "REG-002" in matched_rule_ids
    assert "REG-003" in matched_rule_ids
    assert "REG-004" in matched_rule_ids

    affected_doc_types = {a["document_type"] for a in body["review_areas"]}
    assert "Product Label" in affected_doc_types
    assert "PSUR / PBRER" in affected_doc_types
    assert "Risk Management Plan (RMP)" in affected_doc_types
    assert "Reference Safety Information (RSI)" in affected_doc_types

    # Safeguards: Potential impact language & non-causality disclaimer
    assert "potential" in body["disclaimer"].lower()
    assert "deficiency" in body["disclaimer"].lower()
    assert "causality" in body["disclaimer"].lower()


def test_signal_regulatory_impact_low_signal(client):
    # sig-003 has: PRR 2.1, count 45, trend 0.40, priority low, status closed
    response = client.get("/api/v1/signals/sig-003/regulatory-impact")
    assert response.status_code == 200
    body = response.json()

    assert body["signal_id"] == "sig-003"
    assert body["human_review_required"] is True

    matched_rule_ids = {m["rule_id"] for m in body["rule_matches"]}
    assert "REG-001" not in matched_rule_ids
    assert "REG-002" not in matched_rule_ids
    assert "REG-003" not in matched_rule_ids
    assert "REG-004" not in matched_rule_ids


def test_signal_regulatory_impact_not_found(client):
    response = client.get("/api/v1/signals/sig-nonexistent/regulatory-impact")
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "error"
    assert "not found" in body["error"]["message"].lower()


def test_rule_engine_deterministic_isolation():
    # Test case quality rule (REG-005) exclusively
    facts_low_quality = {
        "prr": 1.5,
        "report_count": 4,
        "trend_score": 0.1,
        "priority_level": "low",
        "candidate_status": "closed",
        "quality_score": 0.65,
        "quality_flags": ["high_missing_age"],
    }
    review_areas, matches = evaluate_rules(facts_low_quality)
    assert len(matches) == 1
    assert matches[0].rule_id == "REG-005"
    assert matches[0].review_area.document_type == "Relevant CTD safety content"
    assert len(review_areas) == 1


def test_rule_engine_empty_matches_on_baseline():
    facts_baseline = {
        "prr": 1.2,
        "report_count": 2,
        "trend_score": 0.05,
        "priority_level": "low",
        "candidate_status": "closed",
        "quality_score": 1.0,
        "quality_flags": [],
    }
    review_areas, matches = evaluate_rules(facts_baseline)
    assert len(matches) == 0
    assert len(review_areas) == 0
