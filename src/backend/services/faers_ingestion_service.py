"""
FDA FAERS quarterly ASCII ingestion service.

Parses the three key files from an official FDA FAERS quarterly ASCII ZIP:
  ASCII/DEMO*.txt  — demographics (primaryid, age, sex, event_dt)
  ASCII/DRUG*.txt  — drugs per report (primaryid, drugname, role_cod)
  ASCII/REAC*.txt  — reactions per report (primaryid, pt)

Delimiter : $ (dollar sign) — verified against FDA ASC_NTS documentation
Encoding  : UTF-8 (FAERS post-2014 Q3); Latin-1 fallback for older files
Header row: present (row 0 = column names)

Age normalization (age_cod values from FDA spec):
  800 = decades → multiply by 10
  801 = years   → as-is
  802 = months  → divide by 12
  803 = weeks   → divide by 52.18
  804 = days    → divide by 365.25
  805 = hours   → divide by 8766

Sex mapping (patientsex / sex field):
  1 or M → "M"
  2 or F → "F"
  anything else → None

Drug role_cod — only Primary Suspect (PS / "1") is used as the canonical drug
for a report; if no PS row exists the first drug row is used as fallback.

Idempotency: if a quarter has already been imported (release_id exists in
faers_quarterly_metadata) the function raises FAERSAlreadyImportedError so the
caller can return 409 Conflict.
"""

import csv
import io
import logging
import zipfile
from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import (
    DrugEventPairModel,
    FAERSQuarterlyMetadataModel,
    ProcessedReportModel,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------

class FAERSAlreadyImportedError(Exception):
    """Raised when the requested quarter has already been imported."""


# ---------------------------------------------------------------------------
# Internal type aliases
# ---------------------------------------------------------------------------

_DemoRow = Dict[str, str]
_DrugRow = Dict[str, str]
_ReacRow = Dict[str, str]


# ---------------------------------------------------------------------------
# Age normalization
# ---------------------------------------------------------------------------

_AGE_COD_TO_YEARS: Dict[str, float] = {
    "800": 10.0,    # decades
    "801": 1.0,     # years
    "802": 1 / 12,  # months
    "803": 1 / 52.18,  # weeks
    "804": 1 / 365.25,  # days
    "805": 1 / 8766,    # hours
}


def _normalize_age(age_str: str, age_cod: str) -> Optional[float]:
    """Return age in years, or None if conversion is not possible."""
    age_str = age_str.strip()
    age_cod = age_cod.strip()
    if not age_str:
        return None
    try:
        raw = float(age_str)
    except ValueError:
        return None
    factor = _AGE_COD_TO_YEARS.get(age_cod, None)
    if factor is None:
        # Unknown code — assume years if value looks plausible
        if 0 < raw <= 130:
            return round(raw, 2)
        return None
    result = raw * factor
    if result < 0 or result > 130:
        return None
    return round(result, 2)


# ---------------------------------------------------------------------------
# Sex normalization
# ---------------------------------------------------------------------------

def _normalize_sex(sex_str: str) -> Optional[str]:
    """Return 'M', 'F', or None."""
    s = sex_str.strip().upper()
    if s in ("1", "M", "MALE"):
        return "M"
    if s in ("2", "F", "FEMALE"):
        return "F"
    return None


# ---------------------------------------------------------------------------
# File name detection helpers
# ---------------------------------------------------------------------------

def _find_file_in_zip(zf: zipfile.ZipFile, prefix: str) -> Optional[str]:
    """
    Return the ZipFile member name for a FAERS ASCII data file.

    FDA naming convention: ASCII/DEMO24Q1.txt, ASCII/drug24q1.TXT, etc.
    The prefix is one of 'DEMO', 'DRUG', 'REAC' (case-insensitive).
    """
    prefix_upper = prefix.upper()
    for name in zf.namelist():
        basename = name.split("/")[-1].upper()
        if basename.startswith(prefix_upper) and basename.endswith(".TXT"):
            return name
    return None


# ---------------------------------------------------------------------------
# Individual file parsers
# ---------------------------------------------------------------------------

def parse_demo_file(content: str) -> Dict[str, _DemoRow]:
    """
    Parse DEMO*.txt content.

    Returns a dict keyed by primaryid with fields: age, age_cod, sex, event_dt.
    Only the first row per primaryid is kept (in case of duplicate caseversions).
    """
    demo: Dict[str, _DemoRow] = {}
    reader = csv.DictReader(
        io.StringIO(content),
        delimiter="$",
        quoting=csv.QUOTE_NONE,
    )
    # Normalise header keys to lowercase and strip whitespace
    reader.fieldnames = (
        [f.strip().lower() for f in reader.fieldnames]
        if reader.fieldnames
        else []
    )
    for row in reader:
        pid = row.get("primaryid", "").strip()
        if not pid or pid in demo:
            continue
        demo[pid] = {
            "age": row.get("age", "").strip(),
            "age_cod": row.get("age_cod", "").strip(),
            "sex": row.get("sex", "").strip(),
            "event_dt": row.get("event_dt", "").strip(),
        }
    return demo


def parse_drug_file(content: str) -> Dict[str, str]:
    """
    Parse DRUG*.txt content.

    Returns a dict keyed by primaryid → canonical drug name.
    Preference order: role_cod == '1' (Primary Suspect / PS) first;
    fallback to the first drug row for the primaryid if no PS exists.
    """
    ps_drug: Dict[str, str] = {}    # Primary Suspect rows
    first_drug: Dict[str, str] = {} # First row seen per primaryid (fallback)

    reader = csv.DictReader(
        io.StringIO(content),
        delimiter="$",
        quoting=csv.QUOTE_NONE,
    )
    reader.fieldnames = (
        [f.strip().lower() for f in reader.fieldnames]
        if reader.fieldnames
        else []
    )
    for row in reader:
        pid = row.get("primaryid", "").strip()
        if not pid:
            continue
        drug_name = row.get("drugname", "").strip().upper()
        if not drug_name:
            continue
        role = row.get("role_cod", "").strip().upper()
        if pid not in first_drug:
            first_drug[pid] = drug_name
        if role in ("PS", "1") and pid not in ps_drug:
            ps_drug[pid] = drug_name

    # Merge: prefer PS, fall back to first
    result: Dict[str, str] = {**first_drug, **ps_drug}
    return result


def parse_reac_file(content: str) -> Dict[str, List[str]]:
    """
    Parse REAC*.txt content.

    Returns a dict keyed by primaryid → list of MedDRA Preferred Terms (pt).
    Duplicates within the same primaryid are deduplicated while preserving order.
    """
    reactions: Dict[str, List[str]] = defaultdict(list)
    seen: Dict[str, set] = defaultdict(set)

    reader = csv.DictReader(
        io.StringIO(content),
        delimiter="$",
        quoting=csv.QUOTE_NONE,
    )
    reader.fieldnames = (
        [f.strip().lower() for f in reader.fieldnames]
        if reader.fieldnames
        else []
    )
    for row in reader:
        pid = row.get("primaryid", "").strip()
        pt = row.get("pt", "").strip().upper()
        if not pid or not pt:
            continue
        if pt not in seen[pid]:
            reactions[pid].append(pt)
            seen[pid].add(pt)

    return dict(reactions)


# ---------------------------------------------------------------------------
# Core ingestion function
# ---------------------------------------------------------------------------

def ingest_faers_zip(
    db: Session,
    quarter: str,
    zip_path: str,
    processing_version: str = "v1.0.0",
) -> Tuple[int, int]:
    """
    Ingest a single FAERS quarterly ASCII ZIP into the database.

    Parameters
    ----------
    db               : SQLAlchemy session (caller manages commit/rollback)
    quarter          : Quarter identifier, e.g. "2024Q1"
    zip_path         : Filesystem path to the official FDA ASCII ZIP file
    processing_version : Version tag stored in metadata (default "v1.0.0")

    Returns
    -------
    (reports_inserted, pairs_upserted) counts

    Raises
    ------
    FAERSAlreadyImportedError : if the quarter already exists in metadata
    FileNotFoundError         : if zip_path does not exist
    KeyError                  : if expected files are not found in the ZIP
    """
    release_id = quarter.upper()

    # -- Idempotency check ---------------------------------------------------
    existing = db.scalar(
        select(FAERSQuarterlyMetadataModel).where(
            FAERSQuarterlyMetadataModel.release_id == release_id
        )
    )
    if existing is not None:
        raise FAERSAlreadyImportedError(
            f"Quarter '{release_id}' has already been imported "
            f"(imported on {existing.import_date})."
        )

    # -- Open ZIP ------------------------------------------------------------
    with zipfile.ZipFile(zip_path, "r") as zf:
        demo_name = _find_file_in_zip(zf, "DEMO")
        drug_name = _find_file_in_zip(zf, "DRUG")
        reac_name = _find_file_in_zip(zf, "REAC")

        if not demo_name:
            raise KeyError(f"DEMO*.txt not found in ZIP '{zip_path}'")
        if not drug_name:
            raise KeyError(f"DRUG*.txt not found in ZIP '{zip_path}'")
        if not reac_name:
            raise KeyError(f"REAC*.txt not found in ZIP '{zip_path}'")

        def _read(member: str) -> str:
            raw = zf.read(member)
            try:
                return raw.decode("utf-8")
            except UnicodeDecodeError:
                return raw.decode("latin-1")

        logger.info("Parsing DEMO file: %s", demo_name)
        demo_map = parse_demo_file(_read(demo_name))

        logger.info("Parsing DRUG file: %s", drug_name)
        drug_map = parse_drug_file(_read(drug_name))

        logger.info("Parsing REAC file: %s", reac_name)
        reac_map = parse_reac_file(_read(reac_name))

    # -- Build normalised reports --------------------------------------------
    all_pids = set(demo_map) | set(drug_map)
    logger.info("Building normalised reports for %d primaryids", len(all_pids))

    # Fetch already-existing report_ids for this quarter to avoid PK conflicts
    existing_ids: set = set(
        db.scalars(
            select(ProcessedReportModel.report_id).where(
                ProcessedReportModel.report_quarter == release_id
            )
        ).all()
    )

    reports_to_insert: List[ProcessedReportModel] = []
    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)

    for pid in all_pids:
        if pid in existing_ids:
            continue

        drug = drug_map.get(pid)
        reactions = reac_map.get(pid, [])
        demo = demo_map.get(pid, {})

        # Skip reports with no usable drug or no reactions
        if not drug or not reactions:
            continue

        patient_age = _normalize_age(
            demo.get("age", ""), demo.get("age_cod", "")
        )
        patient_sex = _normalize_sex(demo.get("sex", ""))
        event_dt_raw = demo.get("event_dt", "").strip()
        event_date = event_dt_raw if event_dt_raw else None

        reports_to_insert.append(
            ProcessedReportModel(
                report_id=pid,
                drug_name=drug,
                reactions=reactions,
                patient_age=patient_age,
                patient_sex=patient_sex,
                event_date=event_date,
                report_quarter=release_id,
                source="FDA_FAERS",
            )
        )

        # Tally drug-event pairs
        for reaction in reactions:
            pair_counts[(drug, reaction)] += 1

    # -- Bulk insert processed reports ---------------------------------------
    if reports_to_insert:
        db.bulk_save_objects(reports_to_insert)
        logger.info("Inserted %d processed reports", len(reports_to_insert))

    # -- Upsert drug-event pairs ---------------------------------------------
    pairs_upserted = 0
    for (drug, event), count in pair_counts.items():
        existing_pair = db.scalar(
            select(DrugEventPairModel).where(
                DrugEventPairModel.drug_name == drug,
                DrugEventPairModel.event_name == event,
                DrugEventPairModel.quarter == release_id,
            )
        )
        if existing_pair:
            existing_pair.count += count
        else:
            db.add(
                DrugEventPairModel(
                    drug_name=drug,
                    event_name=event,
                    count=count,
                    quarter=release_id,
                )
            )
        pairs_upserted += 1

    # -- Write metadata row --------------------------------------------------
    db.add(
        FAERSQuarterlyMetadataModel(
            release_id=release_id,
            quarter=release_id,
            dataset_release=f"FDA FAERS {release_id}",
            import_date=date.today(),
            processing_version=processing_version,
            total_reports=len(reports_to_insert),
            processed_at=datetime.now(timezone.utc),
        )
    )

    db.flush()
    logger.info(
        "Ingestion complete: quarter=%s reports=%d pairs=%d",
        release_id,
        len(reports_to_insert),
        pairs_upserted,
    )
    return len(reports_to_insert), pairs_upserted
