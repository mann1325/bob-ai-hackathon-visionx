from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import FAERSQuarterlyMetadataModel
from shared.schemas.signal import DatasetRelease


def list_datasets(db: Session) -> List[DatasetRelease]:
    """Retrieve all quarterly dataset releases ordered by import date descending."""
    stmt = select(FAERSQuarterlyMetadataModel).order_by(
        FAERSQuarterlyMetadataModel.import_date.desc()
    )
    records = db.scalars(stmt).all()
    return [
        DatasetRelease(
            release_id=r.release_id,
            quarter=r.quarter,
            dataset_release=r.dataset_release,
            import_date=r.import_date,
            processing_version=r.processing_version,
            total_reports=r.total_reports,
            processed_at=r.processed_at.isoformat() if r.processed_at else None,
        )
        for r in records
    ]


def get_dataset(db: Session, release_id: str) -> Optional[DatasetRelease]:
    """Retrieve a single dataset release by its release_id."""
    stmt = select(FAERSQuarterlyMetadataModel).where(
        FAERSQuarterlyMetadataModel.release_id == release_id
    )
    r = db.scalars(stmt).first()
    if not r:
        return None

    return DatasetRelease(
        release_id=r.release_id,
        quarter=r.quarter,
        dataset_release=r.dataset_release,
        import_date=r.import_date,
        processing_version=r.processing_version,
        total_reports=r.total_reports,
        processed_at=r.processed_at.isoformat() if r.processed_at else None,
    )
