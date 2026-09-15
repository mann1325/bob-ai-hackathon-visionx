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
            "2. Do NOT invent, recalculate, or alter any statistical metrics (PRR, ROR, report counts).\n"
            "3. Do NOT declare confirmed causality or determine that a drug is definitively unsafe.\n"
            "4. Clearly articulate known data limitations and potential reporting biases.\n"
            "5. Suggest actionable, practical questions for human pharmacovigilance investigation.\n"
            "6. You MUST respond in valid JSON format with the following keys:\n"
            "   - 'why_flagged': string explaining why this drug-event pair is a candidate signal\n"
            "   - 'evidence_summary': string summarizing the quantitative and qualitative evidence\n"
            "   - 'limitations': array of strings identifying data quality / reporting limitations\n"
            "   - 'suggested_questions': array of strings for subsequent human clinical inquiry"
        )

    def _build_user_prompt(self, facts: Dict[str, Any]) -> str:
        return (
            "Here are the backend-computed structured facts for the candidate safety signal:\n\n"
            f"Drug Name: {facts.get('drug_name', 'UNKNOWN')}\n"
            f"Adverse Event: {facts.get('event_name', 'UNKNOWN')}\n"
            f"Supporting Report Count: {facts.get('report_count', 0)}\n"
            f"PRR (Proportional Reporting Ratio): {facts.get('prr', 'N/A')}\n"
            f"ROR (Reporting Odds Ratio): {facts.get('ror', 'N/A')}\n"
            f"Trend Score: {facts.get('trend_score', 'N/A')}\n"
            f"Case Quality Score: {facts.get('quality_score', 'N/A')}\n"
            f"Case Quality Flags: {', '.join(facts.get('quality_flags', [])) or 'None'}\n"
            f"Potential Duplicate Candidates Count: {facts.get('duplicate_count', 0)}\n"
            f"Representative Duplicate Rationales (sample only; not exhaustive): "
            f"{', '.join(facts.get('duplicate_rationale_sample', [])) or 'None'}\n"
            f"Known Limitations: {', '.join(facts.get('known_limitations', [])) or 'Spontaneous reporting bias'}\n\n"
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

        return {
            "why_flagged": str(parsed.get("why_flagged", f"Elevated reporting for {facts.get('drug_name')} and {facts.get('event_name')}.")),
            "evidence_summary": str(parsed.get("evidence_summary", "Summary of spontaneous reports.")),
            "limitations": list(parsed.get("limitations", facts.get("known_limitations", []))),
            "suggested_questions": list(parsed.get("suggested_questions", [])),
        }
