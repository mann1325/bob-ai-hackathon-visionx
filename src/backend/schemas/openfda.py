from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OpenFDADrugItem(BaseModel):
    brand_name: List[str] = Field(default_factory=list)
    generic_name: List[str] = Field(default_factory=list)
    manufacturer_name: List[str] = Field(default_factory=list)
    product_type: Optional[str] = None
    route: List[str] = Field(default_factory=list)
    substance_name: List[str] = Field(default_factory=list)
    purpose: Optional[str] = None
    warnings: Optional[str] = None


class OpenFDADrugSearchResponse(BaseModel):
    query: str
    total: int = 0
    results: List[OpenFDADrugItem] = Field(default_factory=list)
    source: str = "openFDA"
    is_auxiliary_lookup: bool = True
    disclaimer: str = (
        "Auxiliary openFDA drug lookup data. Does not represent SignalTrace-computed "
        "signal statistics, PRR/ROR calculations, or regulatory determinations."
    )


class OpenFDAEventItem(BaseModel):
    safetyreportid: str
    receivedate: Optional[str] = None
    serious: Optional[str] = None
    seriousnessdeath: Optional[str] = None
    patient_age: Optional[str] = None
    patient_sex: Optional[str] = None
    drugs: List[str] = Field(default_factory=list)
    reactions: List[str] = Field(default_factory=list)


class OpenFDAEventSearchResponse(BaseModel):
    drug: Optional[str] = None
    event: Optional[str] = None
    total: int = 0
    results: List[OpenFDAEventItem] = Field(default_factory=list)
    source: str = "openFDA"
    is_auxiliary_lookup: bool = True
    disclaimer: str = (
        "Auxiliary openFDA adverse event lookup data. Does not represent SignalTrace-computed "
        "signal statistics, PRR/ROR calculations, or regulatory determinations."
    )
