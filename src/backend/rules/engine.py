from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from rules.definitions import ACTIVE_RULES, DeterministicRule
from services.investigation_service import get_case_quality_for_signal
from services.signal_service import get_signal_detail
from shared.schemas.regulatory import (
    RegulatoryImpact,
    ReviewArea,
    RuleDefinition,
    RuleMatch,
)


def list_active_rules() -> List[RuleDefinition]:
    """Return definitions of all active deterministic regulatory rules."""
    return [rule.to_definition() for rule in ACTIVE_RULES]


def evaluate_rules(facts: Dict[str, Any]) -> Tuple[List[ReviewArea], List[RuleMatch]]:
    """Evaluate all deterministic regulatory rules against signal facts."""
    rule_matches: List[RuleMatch] = []
    review_areas_map: Dict[str, ReviewArea] = {}

    for rule in ACTIVE_RULES:
        match = rule.evaluate_fn(facts)
        if match:
            rule_matches.append(match)
            # Store or merge review area by document type
            doc_type = match.review_area.document_type
            if doc_type not in review_areas_map:
                review_areas_map[doc_type] = match.review_area
            else:
                # If existing has lower priority, upgrade to higher
                if match.review_area.priority == "high":
                    review_areas_map[doc_type] = match.review_area

    return list(review_areas_map.values()), rule_matches


def evaluate_regulatory_impact(db: Session, signal_id: str) -> Optional[RegulatoryImpact]:
    """Retrieve signal facts and evaluate deterministic regulatory impact."""
    signal = get_signal_detail(db, signal_id)
    if not signal:
        return None

    case_quality = get_case_quality_for_signal(db, signal_id)

    facts: Dict[str, Any] = {
        "signal_id": signal.signal_id,
        "drug_name": signal.drug_name,
        "event_name": signal.event_name,
        "report_count": signal.supporting_report_count,
        "prr": signal.prr,
        "ror": signal.ror,
        "trend_score": signal.trend_score,
        "risk_score": signal.risk_score,
        "priority_level": signal.priority_level,
        "candidate_status": signal.candidate_status,
        "quality_score": case_quality.quality_score if case_quality else None,
        "quality_flags": case_quality.quality_flags if case_quality else [],
    }

    review_areas, rule_matches = evaluate_rules(facts)

    return RegulatoryImpact(
        signal_id=signal_id,
        review_areas=review_areas,
        rule_matches=rule_matches,
        human_review_required=True,
        disclaimer=(
            "Deterministic regulatory mapping for triage guidance only. "
            "Identifies potential regulatory review areas and does not constitute "
            "a confirmed regulatory deficiency or proof of causality. "
            "Final regulatory determinations require qualified professional review."
        ),
    )
