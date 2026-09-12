from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from shared.schemas.regulatory import ReviewArea, RuleDefinition, RuleMatch


@dataclass
class DeterministicRule:
    rule_id: str
    rule_name: str
    description: str
    target_document_type: str
    section_hint: str
    priority: str
    evaluate_fn: Callable[[Dict[str, Any]], Optional[RuleMatch]]

    def to_definition(self) -> RuleDefinition:
        return RuleDefinition(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            description=self.description,
            target_document_type=self.target_document_type,
            section_hint=self.section_hint,
            default_priority=self.priority,
        )


def _eval_reg_001(facts: Dict[str, Any]) -> Optional[RuleMatch]:
    prr = facts.get("prr")
    report_count = facts.get("report_count", 0)
    if isinstance(prr, (int, float)) and prr >= 2.5 and report_count >= 10:
        return RuleMatch(
            rule_id="REG-001",
            rule_name="High Disproportionality Label Review",
            condition_matched=f"PRR={prr:.2f} (>= 2.5) with {report_count} supporting reports (>= 10).",
            review_area=ReviewArea(
                document_type="Product Label",
                section_hint="Section 4.8 Undesirable Effects / Section 4.4 Special Warnings",
                rationale=(
                    "Substantial statistical disproportionality indicates potential unlisted "
                    "or under-characterized adverse drug reaction requiring product label evaluation."
                ),
                priority="high" if prr >= 3.0 else "medium",
            ),
            confidence_rationale="Deterministic threshold match based on PRR and report volume.",
        )
    return None


def _eval_reg_002(facts: Dict[str, Any]) -> Optional[RuleMatch]:
    trend_score = facts.get("trend_score")
    if isinstance(trend_score, (int, float)) and trend_score >= 0.5:
        return RuleMatch(
            rule_id="REG-002",
            rule_name="Emerging Trend Cumulative Safety Review",
            condition_matched=f"Trend Score={trend_score:.2f} (>= 0.50).",
            review_area=ReviewArea(
                document_type="PSUR / PBRER",
                section_hint="Section 16.2 Cumulative Signal Evaluation",
                rationale=(
                    "Accelerating reporting trajectory over consecutive quarters indicates an emerging "
                    "safety trend requiring formal cumulative evaluation in upcoming PSUR/PBRER."
                ),
                priority="high" if trend_score >= 0.75 else "medium",
            ),
            confidence_rationale="Deterministic threshold match based on temporal trend trajectory.",
        )
    return None


def _eval_reg_003(facts: Dict[str, Any]) -> Optional[RuleMatch]:
    priority_level = str(facts.get("priority_level", "")).lower()
    risk_score = facts.get("risk_score")
    matched_conds = []

    if priority_level in ["high", "critical"]:
        matched_conds.append(f"Priority Level='{priority_level}'")
    if isinstance(risk_score, (int, float)) and risk_score >= 0.7:
        matched_conds.append(f"Risk Score={risk_score:.2f} (>= 0.70)")

    if matched_conds:
        return RuleMatch(
            rule_id="REG-003",
            rule_name="High Priority Risk Management Review",
            condition_matched=" and ".join(matched_conds),
            review_area=ReviewArea(
                document_type="Risk Management Plan (RMP)",
                section_hint="Part II: Module SVII - Identified and Potential Risks",
                rationale=(
                    "High priority/risk score profile warrants assessment against existing "
                    "pharmacovigilance activities and risk minimization measures in the RMP."
                ),
                priority="high",
            ),
            confidence_rationale="Deterministic rule match based on signal triage priority and risk score.",
        )
    return None


def _eval_reg_004(facts: Dict[str, Any]) -> Optional[RuleMatch]:
    report_count = facts.get("report_count", 0)
    candidate_status = str(facts.get("candidate_status", "")).lower()

    if report_count >= 5 and candidate_status in ["candidate", "under_review"]:
        return RuleMatch(
            rule_id="REG-004",
            rule_name="Active Candidate Trial Safety Assessment",
            condition_matched=(
                f"Active status='{candidate_status}' with {report_count} reports (>= 5)."
            ),
            review_area=ReviewArea(
                document_type="Reference Safety Information (RSI)",
                section_hint="Section 7 Reference Safety Information (Investigator's Brochure)",
                rationale=(
                    "Active candidate safety signal under investigation requires checking against "
                    "expected adverse reaction lists in clinical trial Reference Safety Information."
                ),
                priority="medium",
            ),
            confidence_rationale="Deterministic match on active candidate status and supporting reports.",
        )
    return None


def _eval_reg_005(facts: Dict[str, Any]) -> Optional[RuleMatch]:
    quality_score = facts.get("quality_score")
    quality_flags = facts.get("quality_flags", [])

    is_low_quality = isinstance(quality_score, (int, float)) and quality_score < 0.8
    has_critical_flags = any("high_missing" in flag for flag in quality_flags)

    if is_low_quality or has_critical_flags:
        cond_text = f"Quality Score={quality_score} (< 0.80)" if is_low_quality else f"Quality Flags={quality_flags}"
        return RuleMatch(
            rule_id="REG-005",
            rule_name="Case Quality Clinical Documentation Review",
            condition_matched=cond_text,
            review_area=ReviewArea(
                document_type="Relevant CTD safety content",
                section_hint="Module 2.7.4 Summary of Clinical Safety / Module 5.3.5.3",
                rationale=(
                    "Spontaneous report data quality or missingness concerns necessitate targeted clinical "
                    "narrative follow-up in CTD clinical safety summary documentation."
                ),
                priority="medium",
            ),
            confidence_rationale="Deterministic match on case-quality flags and missingness thresholds.",
        )
    return None


ACTIVE_RULES: List[DeterministicRule] = [
    DeterministicRule(
        rule_id="REG-001",
        rule_name="High Disproportionality Label Review",
        description="PRR >= 2.5 and report_count >= 10 indicates potential product label review.",
        target_document_type="Product Label",
        section_hint="Section 4.8 Undesirable Effects / Section 4.4 Special Warnings",
        priority="high",
        evaluate_fn=_eval_reg_001,
    ),
    DeterministicRule(
        rule_id="REG-002",
        rule_name="Emerging Trend Cumulative Safety Review",
        description="Trend score >= 0.50 indicates emerging trend for PSUR/PBRER review.",
        target_document_type="PSUR / PBRER",
        section_hint="Section 16.2 Cumulative Signal Evaluation",
        priority="high",
        evaluate_fn=_eval_reg_002,
    ),
    DeterministicRule(
        rule_id="REG-003",
        rule_name="High Priority Risk Management Review",
        description="Priority in ['high', 'critical'] or risk_score >= 0.70 triggers RMP review.",
        target_document_type="Risk Management Plan (RMP)",
        section_hint="Part II: Module SVII - Identified and Potential Risks",
        priority="high",
        evaluate_fn=_eval_reg_003,
    ),
    DeterministicRule(
        rule_id="REG-004",
        rule_name="Active Candidate Trial Safety Assessment",
        description="Active status and report count >= 5 triggers trial RSI assessment.",
        target_document_type="Reference Safety Information (RSI)",
        section_hint="Section 7 Reference Safety Information (Investigator's Brochure)",
        priority="medium",
        evaluate_fn=_eval_reg_004,
    ),
    DeterministicRule(
        rule_id="REG-005",
        rule_name="Case Quality Clinical Documentation Review",
        description="Quality score < 0.80 or high missingness triggers CTD safety review.",
        target_document_type="Relevant CTD safety content",
        section_hint="Module 2.7.4 Summary of Clinical Safety / Module 5.3.5.3",
        priority="medium",
        evaluate_fn=_eval_reg_005,
    ),
]
