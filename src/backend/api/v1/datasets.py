from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.dataset_service import get_dataset, list_datasets
from shared.schemas.signal import DatasetRelease

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=List[DatasetRelease])
def get_all_datasets(db: Session = Depends(get_db)) -> List[DatasetRelease]:
    """List available FAERS quarterly dataset releases with processing metadata."""
    return list_datasets(db)


@router.get("/{release_id}", response_model=DatasetRelease)
def get_dataset_by_id(
    release_id: str,
    db: Session = Depends(get_db),
) -> DatasetRelease:
    """Retrieve details for a specific FAERS quarterly dataset release."""
    dataset = get_dataset(db, release_id)
    if not dataset:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset release '{release_id}' not found.",
        )
    return dataset
