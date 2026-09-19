"""
FDA FAERS quarterly ASCII ingestion service.

Parses the three key files from an official FDA FAERS quarterly ASCII ZIP:
  ASCII/DEMO*.txt  — demographics (primaryid, age, sex, event_dt)
  ASCII/DRUG*.txt  — drugs per report (primaryid, drugname, role_cod)
  ASCII/REAC*.txt  — reactions per report (primaryid, pt)
    ASCII/OUTC*.txt  — patient outcomes (primaryid, outc_cod)

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
from sqlalchemy.orm import Session, sessionmaker

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
_OutcomeRow = Dict[str, str]

SERIOUS_OUTCOME_CODES = {"DE", "LT", "HO", "DS", "CA", "RI", "OT"}
INGESTION_BATCH_SIZE = 5_000


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
    The prefix is one of 'DEMO', 'DRUG', 'REAC', or 'OUTC' (case-insensitive).
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


def parse_outc_file(content: str) -> Dict[str, List[str]]:
    """Parse OUTC*.txt into outcome codes grouped by FAERS primaryid."""
    outcomes: Dict[str, List[str]] = defaultdict(list)
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
        code = row.get("outc_cod", "").strip().upper()
        if not pid or not code or code in seen[pid]:
            continue
        outcomes[pid].append(code)
        seen[pid].add(code)

    return dict(outcomes)


def _seriousness_for_outcomes(codes: List[str]) -> tuple[str, List[str]]:
    """Classify only from official FAERS OUTC codes."""
    serious_codes = sorted({code for code in codes if code in SERIOUS_OUTCOME_CODES})
    return ("Serious", serious_codes) if serious_codes else ("Non-serious", [])


# ---------------------------------------------------------------------------
# Core ingestion function
# ---------------------------------------------------------------------------

def _commit_report_batch(
    session_factory: sessionmaker,
    reports: List[ProcessedReportModel],
    pair_counts: Dict[Tuple[str, str], int],
    release_id: str,
) -> int:
    """Persist one bounded report/pair batch and commit it independently."""
    if not reports:
        return 0

    with session_factory() as db:
        try:
            db.bulk_save_objects(reports)
            existing_pairs = {
                (pair.drug_name, pair.event_name): pair
                for pair in db.scalars(
                    select(DrugEventPairModel).where(
                        DrugEventPairModel.quarter == release_id
                    )
                ).all()
            }
            for (drug, event), count in pair_counts.items():
                existing_pair = existing_pairs.get((drug, event))
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
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "Committed ingestion batch: quarter=%s reports=%d pairs=%d",
        release_id,
        len(reports),
        len(pair_counts),
    )
    return len(pair_counts)

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
    db               : SQLAlchemy session used for bounded batch commits
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
        outc_name = _find_file_in_zip(zf, "OUTC")

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

        outc_map: Dict[str, List[str]] = {}
        if outc_name:
            logger.info("Parsing OUTC file: %s", outc_name)
            outc_map = parse_outc_file(_read(outc_name))

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
    bind = db.get_bind()
    session_factory = sessionmaker(
        bind=bind,
        autoflush=False,
        expire_on_commit=False,
    )
    # Release the caller's read-only transaction before opening batch sessions.
    db.rollback()

    reports_to_insert: List[ProcessedReportModel] = []
    pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)
    reports_inserted = 0
    pairs_upserted = 0

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
        seriousness, seriousness_codes = _seriousness_for_outcomes(outc_map.get(pid, [])) if pid in outc_map else ("Unknown", [])

        reports_to_insert.append(
            ProcessedReportModel(
                report_id=pid,
                drug_name=drug,
                reactions=reactions,
                patient_age=patient_age,
                patient_sex=patient_sex,
                event_date=event_date,
                seriousness=seriousness,
                seriousness_codes=seriousness_codes,
                report_quarter=release_id,
                source="FDA_FAERS",
            )
        )

        # Tally drug-event pairs
        for reaction in reactions:
            pair_counts[(drug, reaction)] += 1

        if len(reports_to_insert) >= INGESTION_BATCH_SIZE:
            pairs_upserted += _commit_report_batch(
                session_factory, reports_to_insert, pair_counts, release_id
            )
            reports_inserted += len(reports_to_insert)
            existing_ids.update(report.report_id for report in reports_to_insert)
            reports_to_insert = []
            pair_counts = defaultdict(int)

    # -- Commit the final bounded report/pair batch --------------------------
    if reports_to_insert:
        pairs_upserted += _commit_report_batch(
            session_factory, reports_to_insert, pair_counts, release_id
        )
        reports_inserted += len(reports_to_insert)

    # Metadata is written last and marks a complete import. A rerun after a
    # mid-import failure skips the already committed report IDs.
    with session_factory() as metadata_db:
        try:
            metadata_db.add(
                FAERSQuarterlyMetadataModel(
                    release_id=release_id,
                    quarter=release_id,
                    dataset_release=f"FDA FAERS {release_id}",
                    import_date=date.today(),
                    processing_version=processing_version,
                    total_reports=reports_inserted,
                    processed_at=datetime.now(timezone.utc),
                )
            )
            metadata_db.commit()
        except Exception:
            metadata_db.rollback()
            raise

    logger.info(
        "Ingestion complete: quarter=%s reports=%d pairs=%d",
        release_id,
        reports_inserted,
        pairs_upserted,
    )
    return reports_inserted, pairs_upserted
