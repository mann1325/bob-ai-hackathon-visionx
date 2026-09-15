import json
import logging
import re
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiClientError(Exception):
    """Base exception for Gemini client errors."""
    pass


class GeminiAuthError(GeminiClientError):
    """Raised when authentication with Gemini fails."""
    pass


class GeminiAPIError(GeminiClientError):
    """Raised when Gemini API returns an error response."""
    pass


class GeminiClient:
    """Client for Google Gemini REST API providing document safety intelligence."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GEMINI_MODEL,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_gemini_key")

    def _build_system_instruction(self) -> str:
        return (
            "You are a pharmacovigilance document intelligence assistant for SignalTrace.\n"
            "Your task is to analyze uploaded safety/regulatory documents (such as Product Labels, "
            "RSI, PSUR/PBRER, or CTD safety documents) in the context of a candidate drug safety signal.\n\n"
            "STRICT SAFETY & REGULATORY RULES:\n"
            "1. Base your analysis ONLY on the provided document text and candidate signal context.\n"
            "2. Do NOT invent sections, text, or unsupported facts.\n"
            "3. Do NOT declare a confirmed regulatory deficiency or make definitive regulatory decisions.\n"
            "4. Do NOT establish or claim clinical causality.\n"
            "5. Label any identified omission or discrepancy strictly as a 'potential coverage gap' or 'possible inconsistency' "
            "that requires professional human expert review.\n"
            "6. You MUST respond with a valid JSON object containing exactly these keys:\n"
            "   - 'relevant_sections': array of objects with 'section_name' (string) and 'relevance_reason' (string)\n"
            "   - 'existing_related_content': string summarizing what relevant safety information already exists in the document (or null)\n"
            "   - 'potential_coverage_gap': string describing potential gaps where the signal is not adequately addressed (or null)\n"
            "   - 'analysis_status': string, one of 'completed', 'needs_review', or 'failed'"
        )

    def _build_user_prompt(
        self,
        document_text: str,
        document_filename: str,
        signal_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        prompt = (
            f"Analyze the following document '{document_filename}' against the candidate safety signal.\n\n"
        )
        if signal_context:
            prompt += (
                "--- CANDIDATE SIGNAL CONTEXT ---\n"
                f"Signal ID: {signal_context.get('signal_id', 'N/A')}\n"
                f"Drug: {signal_context.get('drug_name', 'UNKNOWN')}\n"
                f"Adverse Event: {signal_context.get('event_name', 'UNKNOWN')}\n"
                f"Report Count: {signal_context.get('report_count', 'N/A')}\n"
                f"PRR: {signal_context.get('prr', 'N/A')}\n"
                f"Potential Review Areas: {', '.join(signal_context.get('review_areas', [])) or 'None'}\n\n"
            )

        prompt += (
            "--- EXTRACTED DOCUMENT TEXT ---\n"
            f"{document_text[:15000]}\n\n"
            "Please return your analysis in valid JSON format."
        )
        return prompt

    def analyze_document(
        self,
        document_text: str,
        document_filename: str,
        signal_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Call Gemini API to analyze document text against signal context."""
        if not self.is_configured:
            raise GeminiAuthError("GEMINI_API_KEY is not configured or is invalid.")

        url = f"{GEMINI_API_BASE_URL}/{self.model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        system_instruction = self._build_system_instruction()
        user_prompt = self._build_user_prompt(document_text, document_filename, signal_context)

        payload = {
            "system_instruction": {
                "parts": [{"text": system_instruction}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "maxOutputTokens": 2048,
            },
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code == 401 or response.status_code == 403:
                raise GeminiAuthError("Invalid Gemini API key or unauthorized request.")
            if response.status_code >= 400:
                raise GeminiAPIError(
                    f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}"
                )

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiAPIError("Gemini API returned no candidates.")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts:
                raise GeminiAPIError("Gemini candidate has no content parts.")

            raw_text = content_parts[0].get("text", "")
            return self._parse_json_response(raw_text, signal_context)

        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            logger.error("Network error connecting to Gemini API: %s", type(exc).__name__)
            raise GeminiAPIError("Timeout or network error connecting to Gemini API.") from exc
        except (GeminiAuthError, GeminiAPIError):
            raise
        except Exception as exc:
            logger.error("Unexpected error calling Gemini API: %s", type(exc).__name__)
            raise GeminiAPIError(f"Failed to process response from Gemini API: {exc}") from exc

    def _parse_json_response(
        self,
        raw_text: str,
        signal_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Parse and sanitize JSON response from Gemini."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("Could not decode JSON from Gemini output; using structured fallback.")
            parsed = {
                "relevant_sections": [
                    {
                        "section_name": "General Safety",
                        "relevance_reason": "Automated fallback parsing of document analysis.",
                    }
                ],
                "existing_related_content": cleaned[:300],
                "potential_coverage_gap": "Potential coverage gap requires human expert verification.",
                "analysis_status": "needs_review",
            }

        # Normalize relevant_sections
        raw_sections = parsed.get("relevant_sections", [])
        normalized_sections: List[Dict[str, str]] = []
        if isinstance(raw_sections, list):
            for sec in raw_sections:
                if isinstance(sec, dict):
                    normalized_sections.append(
                        {
                            "section_name": str(sec.get("section_name", "Section")),
                            "relevance_reason": str(sec.get("relevance_reason", "Safety relevance")),
                        }
                    )
                elif isinstance(sec, str):
                    normalized_sections.append(
                        {"section_name": sec, "relevance_reason": "Identified section"}
                    )

        status_val = parsed.get("analysis_status", "completed")
        if status_val not in ("completed", "needs_review", "failed"):
            status_val = "completed"

        return {
            "relevant_sections": normalized_sections,
            "existing_related_content": (
                str(parsed["existing_related_content"])
                if parsed.get("existing_related_content") is not None
                else None
            ),
            "potential_coverage_gap": (
                str(parsed["potential_coverage_gap"])
                if parsed.get("potential_coverage_gap") is not None
                else None
            ),
            "analysis_status": status_val,
        }
