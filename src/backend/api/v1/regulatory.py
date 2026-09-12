from typing import List
from fastapi import APIRouter

from rules.engine import list_active_rules
from shared.schemas.regulatory import RuleDefinition

router = APIRouter(prefix="/regulatory-rules", tags=["regulatory"])


@router.get("", response_model=List[RuleDefinition])
def get_regulatory_rules() -> List[RuleDefinition]:
    """List all active deterministic regulatory rules for signal-to-document mapping."""
    return list_active_rules()
