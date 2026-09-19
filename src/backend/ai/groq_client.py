import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClientError(Exception):
    """Base exception for Groq client errors."""
    pass


class GroqAuthError(GroqClientError):
    """Raised when authentication with Groq fails."""
    pass


class GroqAPIError(GroqClientError):
    """Raised when Groq API returns an error response."""
    pass


class GroqClient:
    """Client for Groq API providing pharmacovigilance evidence explanations."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GROQ_MODEL,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_groq_key")

    def _build_system_prompt(self) -> str:
        return (
            "You are a pharmacovigilance decision-support assistant for SignalTrace.\n"
            "Your task is to explain candidate drug safety signals to human safety reviewers.\n\n"
            "STRICT RULES:\n"
            "1. Base your explanation ONLY on the structured facts provided by the user.\n"
            "2. Treat every non-null deterministic value as authoritative. Never say an explicitly supplied field is unavailable.\n"
            "3. The exact marker 'NOT AVAILABLE IN EVIDENCE BUNDLE' means the field was not supplied; do not infer a value.\n"
            "4. Do NOT invent, recalculate, or alter any statistical metrics (PRR, ROR, report counts, chi-square).\n"
            "5. Do NOT declare confirmed causality, drug unsafety, a regulatory violation, or a regulatory decision.\n"
            "6. Clearly distinguish observed deterministic evidence, limitations, and AI interpretation/questions.\n"
            "7. Suggest actionable, practical questions for human pharmacovigilance investigation.\n"
            "8. You MUST respond in valid JSON format with the following keys:\n"
            "   - 'why_flagged': string explaining why this drug-event pair is a candidate signal\n"
            "   - 'evidence_summary': string summarizing the quantitative and qualitative evidence\n"
            "   - 'limitations': array of strings identifying data quality / reporting limitations\n"
            "   - 'suggested_questions': array of strings for subsequent human clinical inquiry"
        )

    def _build_user_prompt(self, facts: Dict[str, Any]) -> str:
        quality = facts.get("case_quality") or {}
        unavailable = "NOT AVAILABLE IN EVIDENCE BUNDLE"
        duplicate_sample = facts.get("duplicate_sample", facts.get("duplicate_rationale_sample"))
        def value(field: str) -> Any:
            return facts.get(field) if facts.get(field) is not None else unavailable

        return (
            "Here are the backend-computed structured facts for the candidate safety signal. "
            "DATA + CODE = FACTS; AI = EXPLANATION.\n\n"
            f"Signal ID: {value('signal_id')}\n"
            f"Drug Name: {value('drug_name')}\n"
            f"Adverse Event: {value('event_name')}\n"
            f"Candidate Status: {value('candidate_status')}\n"
            f"Priority: {value('priority_level')}\n"
            f"Risk Score: {value('risk_score')}\n"
            f"Dataset Release: {value('dataset_version')}\n"
            f"Supporting Report Count: {value('report_count')}\n"
            f"PRR (Proportional Reporting Ratio): {value('prr')}\n"
            f"ROR (Reporting Odds Ratio): {value('ror')}\n"
            f"Chi-square (Pearson, existing calculation): {value('chi_square')}\n"
            f"Contingency Table: {value('contingency_table')}\n"
            f"Trend Score: {value('trend_score')}\n"
            f"Trend Data: {value('trend_data')}\n"
            f"Case Quality Score: {quality.get('quality_score', unavailable)}\n"
            f"Case Quality Total Reports: {quality.get('total_reports', unavailable)}\n"
            f"Missing Age Count: {quality.get('missing_age_count', unavailable)}\n"
            f"Missing Sex Count: {quality.get('missing_sex_count', unavailable)}\n"
            f"Missing Event Date Count: {quality.get('missing_date_count', unavailable)}\n"
            f"Case Quality Flags: {', '.join(quality.get('quality_flags', [])) or unavailable}\n"
            f"Case Quality Indicators: {quality.get('indicators', unavailable)}\n"
            f"Potential Duplicate Candidates Count: {value('duplicate_count')}\n"
            f"Potential Duplicate Sample (sample only; not exhaustive): {duplicate_sample if duplicate_sample else unavailable}\n"
            f"Known Limitations: {value('known_limitations')}\n"
            f"Potential Review Areas: {value('regulatory_review_areas')}\n"
            f"Deterministic Rule Matches: {value('regulatory_rule_matches')}\n\n"
            "The JSON below is the same deterministic context. Do not contradict it or calculate new metrics:\n"
            f"{json.dumps(facts, sort_keys=True, default=str)}\n\n"
            "Please generate the structured explanation JSON."
        )

    def generate_explanation(self, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Call Groq API with structured facts and return explanation dictionary."""
        if not self.is_configured:
            raise GroqAuthError("GROQ_API_KEY is not configured or is invalid.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": self._build_user_prompt(facts)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 1024,
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(GROQ_API_URL, headers=headers, json=payload)

            if response.status_code == 401:
                raise GroqAuthError("Invalid Groq API key or unauthorized request.")
            if response.status_code >= 400:
                raise GroqAPIError(
                    f"Groq API returned HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON content
            return self._parse_json_response(content, facts)

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.error("Network error communicating with Groq API: %s", exc)
            raise GroqAPIError("Timeout or network error connecting to Groq API.") from exc
        except (KeyError, IndexError, ValueError) as exc:
            logger.error("Error parsing Groq response: %s", exc)
            raise GroqAPIError("Failed to parse response from Groq API.") from exc

    @staticmethod
    def _deterministic_evidence_summary(facts: Dict[str, Any]) -> str:
        """Return authoritative facts that must remain visible beside AI text."""
        quality = facts.get("case_quality")
        quality_text = "NOT AVAILABLE IN EVIDENCE BUNDLE"
        if quality:
            quality_text = (
                f"score={quality.get('quality_score')}, "
                f"reports={quality.get('total_reports')}, "
                f"missing_age={quality.get('missing_age_count')}, "
                f"missing_sex={quality.get('missing_sex_count')}, "
                f"missing_event_date={quality.get('missing_date_count')}, "
                f"flags={quality.get('quality_flags') or []}"
            )
        return (
            f"Reports={facts.get('report_count')}; PRR={facts.get('prr')}; "
            f"ROR={facts.get('ror')}; chi-square={facts.get('chi_square')}; "
            f"case quality ({quality_text}); "
            f"potential duplicate candidates={facts.get('duplicate_count')}; "
            f"trend data={facts.get('trend_data') if facts.get('trend_data') is not None else 'NOT AVAILABLE IN EVIDENCE BUNDLE'}; "
            f"potential review areas={len(facts.get('regulatory_review_areas') or [])}; "
            f"deterministic rule matches={len(facts.get('regulatory_rule_matches') or [])}."
        )

    @staticmethod
    def _filter_contradictory_limitations(limitations: List[str], facts: Dict[str, Any]) -> List[str]:
        quality = facts.get("case_quality")
        if not quality:
            return limitations
        filtered = []
        for limitation in limitations:
            lowered = limitation.lower()
            mentions_quality = "quality" in lowered or "missing-field" in lowered or "missing field" in lowered
            says_unavailable = "not available" in lowered or "unavailable" in lowered or "no case" in lowered
            if not (mentions_quality and says_unavailable):
                filtered.append(limitation)
        return filtered

    def _parse_json_response(self, text: str, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and validate JSON fields from model output."""
        cleaned = text.strip()
        # Handle markdown code fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from Groq output; using fallback wrapper.")
            parsed = {
                "why_flagged": cleaned[:300],
                "evidence_summary": cleaned,
                "limitations": facts.get("known_limitations", ["Spontaneous reporting bias"]),
                "suggested_questions": ["Review detailed case narratives."],
            }

        limitations = list(parsed.get("limitations", facts.get("known_limitations", [])))
        evidence_summary = str(parsed.get("evidence_summary", "Summary of spontaneous reports."))
        deterministic_summary = self._deterministic_evidence_summary(facts)
        return {
            "why_flagged": str(parsed.get("why_flagged", f"Elevated reporting for {facts.get('drug_name')} and {facts.get('event_name')}.")),
            "evidence_summary": f"Deterministic evidence: {deterministic_summary} AI interpretation: {evidence_summary}",
            "limitations": self._filter_contradictory_limitations(limitations, facts),
            "suggested_questions": list(parsed.get("suggested_questions", [])),
        }
