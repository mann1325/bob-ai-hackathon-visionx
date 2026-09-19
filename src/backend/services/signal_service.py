import math
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import and_, cast, distinct, func, literal, or_, select, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from database.models import (
    DrugEventPairModel,
    DuplicateCandidateModel,
    FAERSQuarterlyMetadataModel,
    ProcessedReportModel,
    SignalMetricsModel,
    SignalModel,
)
from shared.schemas.evidence import (
    DuplicateCandidate,
    EvidenceBundle,
)
from shared.schemas.signal import (
    NormalizedReport,
    SignalDetail,
    SignalMetrics,
    SignalSummary,
    SupportingReportList,
)
from ml.trend_scorer import compute_trend_score


def search_drugs(db: Session, query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search for drug names matching the query string."""
    q_str = f"%{query.strip().upper()}%"

    # Search in signals table first
    stmt_signals = (
        select(SignalModel.drug_name, func.count(SignalModel.signal_id).label("signal_count"))
        .where(func.upper(SignalModel.drug_name).like(q_str))
        .group_by(SignalModel.drug_name)
        .order_by(func.count(SignalModel.signal_id).desc())
        .limit(limit)
    )
    results = db.execute(stmt_signals).all()

    if results:
        return [
            {"drug_name": r[0], "candidate_signals_count": r[1]}
            for r in results
        ]

    # Fallback to processed reports or drug event pairs
    stmt_reports = (
        select(distinct(ProcessedReportModel.drug_name))
        .where(func.upper(ProcessedReportModel.drug_name).like(q_str))
        .limit(limit)
    )
    report_drugs = db.scalars(stmt_reports).all()

    return [
        {"drug_name": d, "candidate_signals_count": 0}
        for d in report_drugs
    ]


def _get_signal_trend_data_batch(
    db: Session,
    signals: List[Any],
) -> Dict[Tuple[str, str, Optional[str]], List[Dict[str, int | str]]]:
    """Aggregate fallback trend data for a page of signals in one query."""
    if not signals:
        return {}

    signal_keys = {
        (record.drug_name, record.event_name, record.dataset_version)
        for record in signals
    }
    trend_data: Dict[Tuple[str, str, Optional[str]], Dict[str, int]] = {
        key: {} for key in signal_keys
    }
    is_postgresql = db.get_bind().dialect.name == "postgresql"

    if is_postgresql:
        statements = []
        for drug_name, event_name, dataset_version in signal_keys:
            filters = [ProcessedReportModel.drug_name == drug_name]
            if dataset_version:
                filters.append(ProcessedReportModel.report_quarter == dataset_version)
            filters.append(
                cast(ProcessedReportModel.reactions, JSONB).contains(
                    [event_name.upper()]
                )
            )
            statements.append(
                select(
                    literal(drug_name).label("drug_name"),
                    literal(event_name).label("event_name"),
                    ProcessedReportModel.report_quarter,
                    func.count().label("count"),
                )
                .where(*filters)
                .group_by(ProcessedReportModel.report_quarter)
            )
        rows = db.execute(union_all(*statements)).all()
        for drug_name, event_name, report_quarter, count in rows:
            for signal_key in signal_keys:
                if (
                    signal_key[0] == drug_name
                    and signal_key[1] == event_name
                    and (not signal_key[2] or signal_key[2] == report_quarter)
                ):
                    trend_data[signal_key][report_quarter] = int(count)
        return {
            key: [
                {"quarter": quarter, "count": counts[quarter]}
                for quarter in sorted(counts)
            ]
            for key, counts in trend_data.items()
        }

    conditions = []
    for drug_name, event_name, dataset_version in signal_keys:
        filters = [ProcessedReportModel.drug_name == drug_name]
        if dataset_version:
            filters.append(ProcessedReportModel.report_quarter == dataset_version)
        conditions.append(and_(*filters))

    rows = db.execute(
        select(
            ProcessedReportModel.drug_name,
            ProcessedReportModel.report_quarter,
            ProcessedReportModel.reactions,
        ).where(or_(*conditions))
    ).all()

    for drug_name, report_quarter, reactions in rows:
        for signal_key in signal_keys:
            signal_drug, event_name, dataset_version = signal_key
            if signal_drug != drug_name:
                continue
            if dataset_version and dataset_version != report_quarter:
                continue
            if not isinstance(reactions, list) or not any(
                isinstance(reaction, str) and reaction.upper() == event_name.upper()
                for reaction in reactions
            ):
                continue
            counts = trend_data[signal_key]
            counts[report_quarter] = counts.get(report_quarter, 0) + 1

    return {
        key: [
            {"quarter": quarter, "count": counts[quarter]}
            for quarter in sorted(counts)
        ]
        for key, counts in trend_data.items()
    }


def list_signals(
    db: Session,
    drug: Optional[str] = None,
    event: Optional[str] = None,
    min_prr: Optional[float] = None,
    status: Optional[str] = None,
    release_id: Optional[str] = None,
    sort_by: str = "rank",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 20,
) -> Tuple[List[SignalSummary], int]:
    """List candidate signals with filtering, sorting, and pagination."""
    query = select(
        SignalModel.signal_id,
        SignalModel.drug_name,
        SignalModel.event_name,
        SignalModel.supporting_report_count,
        SignalModel.prr,
        SignalModel.ror,
        SignalModel.risk_score,
        SignalModel.priority_level,
        SignalModel.candidate_status,
        SignalModel.dataset_version,
        SignalModel.rank,
    )

    if drug:
        query = query.where(func.upper(SignalModel.drug_name).like(f"%{drug.strip().upper()}%"))
    if event:
        query = query.where(func.upper(SignalModel.event_name).like(f"%{event.strip().upper()}%"))
    if min_prr is not None:
        query = query.where(SignalModel.prr >= min_prr)
    if status:
        query = query.where(SignalModel.candidate_status == status)
    if release_id:
        query = query.where(SignalModel.dataset_version == release_id)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_stmt) or 0

    # Sorting
    sort_col = getattr(SignalModel, sort_by, SignalModel.rank)
    if sort_order.lower() == "desc":
        query = query.order_by(sort_col.desc().nulls_last())
    else:
        query = query.order_by(sort_col.asc().nulls_last())

    # Pagination
    offset = max(0, (page - 1) * page_size)
    query = query.offset(offset).limit(page_size)

    records = db.execute(query).all()

    signal_ids = [record.signal_id for record in records]
    metrics_by_id = {
        metric.signal_id: metric
        for metric in db.scalars(
            select(SignalMetricsModel).where(SignalMetricsModel.signal_id.in_(signal_ids))
        ).all()
    } if signal_ids else {}
    signals_needing_trend = [
        record
        for record in records
        if record.signal_id not in metrics_by_id
        or metrics_by_id[record.signal_id].trend_data is None
    ]
    trend_data_by_key = _get_signal_trend_data_batch(db, signals_needing_trend)

    items = []
    for record in records:
        metric = metrics_by_id.get(record.signal_id)
        trend_data = (
            metric.trend_data
            if metric is not None and metric.trend_data is not None
            else trend_data_by_key.get(
                (record.drug_name, record.event_name, record.dataset_version), []
            )
        )
        items.append(
            SignalSummary(
                signal_id=record.signal_id,
                drug_name=record.drug_name,
                event_name=record.event_name,
                supporting_report_count=record.supporting_report_count,
                prr=record.prr,
                ror=record.ror,
                trend_score=compute_trend_score(trend_data),
                risk_score=record.risk_score,
                priority_level=record.priority_level,
                candidate_status=record.candidate_status,
                dataset_version=record.dataset_version,
                rank=record.rank,
            )
        )

    return items, total


def get_signal_detail(db: Session, signal_id: str) -> Optional[SignalDetail]:
    """Retrieve full details for a candidate signal."""
    stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    r = db.scalars(stmt).first()
    if not r:
        return None

    metrics = get_signal_metrics(db, signal_id)
    dataset_metadata = None
    dataset_source = None
    if r.dataset_version:
        dataset_metadata = db.scalars(
            select(FAERSQuarterlyMetadataModel).where(
                FAERSQuarterlyMetadataModel.release_id == r.dataset_version
            )
        ).first()
        source = db.scalars(
            select(ProcessedReportModel.source)
            .where(ProcessedReportModel.report_quarter == r.dataset_version)
            .limit(1)
        ).first()
        if source:
            dataset_source = source.replace("_", " ")

    return SignalDetail(
        signal_id=r.signal_id,
        drug_name=r.drug_name,
        event_name=r.event_name,
        supporting_report_count=r.supporting_report_count,
        prr=r.prr,
        ror=r.ror,
        trend_score=r.trend_score,
        risk_score=r.risk_score,
        priority_level=r.priority_level,
        candidate_status=r.candidate_status,
        dataset_version=r.dataset_version,
        dataset_source=dataset_source,
        processing_version=(dataset_metadata.processing_version if dataset_metadata else None),
        import_date=(dataset_metadata.import_date if dataset_metadata else None),
        metrics=metrics,
        known_limitations=[
            limitation.replace(
                "Underreporting and reporting biasare inherent limitations",
                "Underreporting and reporting biases are inherent limitations",
            )
            for limitation in (r.known_limitations or [
            "FAERS reports represent spontaneous reports and do not prove causality.",
            "Underreporting and reporting bias are inherent limitations of spontaneous data.",
            ])
        ],
        human_review_required=True,
    )


def list_supporting_reports(
    db: Session,
    signal_id: str,
    page: int = 1,
    page_size: int = 50,
) -> Optional[SupportingReportList]:
    """List stored FAERS reports supporting a signal, with stable pagination."""
    signal = db.execute(
        select(
            SignalModel.drug_name,
            SignalModel.event_name,
            SignalModel.dataset_version,
        ).where(SignalModel.signal_id == signal_id)
    ).first()
    if signal is None:
        return None

    drug_name, event_name, dataset_version = signal
    report_columns = (
        ProcessedReportModel.report_id,
        ProcessedReportModel.drug_name,
        ProcessedReportModel.reactions,
        ProcessedReportModel.patient_age,
        ProcessedReportModel.patient_sex,
        ProcessedReportModel.event_date,
        ProcessedReportModel.seriousness,
        ProcessedReportModel.seriousness_codes,
        ProcessedReportModel.report_quarter,
        ProcessedReportModel.source,
    )
    filters = [ProcessedReportModel.drug_name == drug_name]
    if dataset_version:
        filters.append(ProcessedReportModel.report_quarter == dataset_version)

    if db.get_bind().dialect.name == "postgresql":
        filters.append(
            cast(ProcessedReportModel.reactions, JSONB).contains([event_name.upper()])
        )
        total = db.scalar(
            select(func.count()).select_from(ProcessedReportModel).where(*filters)
        ) or 0
        rows = db.execute(
            select(*report_columns)
            .where(*filters)
            .order_by(ProcessedReportModel.report_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    else:
        # Existing tests use SQLite, which does not support PostgreSQL JSONB operators.
        candidates = db.scalars(
            select(ProcessedReportModel)
            .where(*filters)
            .order_by(ProcessedReportModel.report_id)
        ).all()
        event = event_name.upper()
        matching = [
            report for report in candidates
            if isinstance(report.reactions, list)
            and any(isinstance(reaction, str) and reaction.upper() == event for reaction in report.reactions)
        ]
        total = len(matching)
        start = (page - 1) * page_size
        column_names = [column.key for column in report_columns]
        rows = [
            {
                name: getattr(report, name)
                for name in column_names
            }
            for report in matching[start : start + page_size]
        ]

    return SupportingReportList(
        reports=[
            NormalizedReport.model_validate(
                row._mapping if hasattr(row, "_mapping") else row
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def get_processed_report(
    db: Session, report_id: str
) -> Optional[NormalizedReport]:
    """Retrieve one stored processed report by its primary key."""
    report = db.get(ProcessedReportModel, report_id)
    if not report:
        return None
    return NormalizedReport.model_validate(report, from_attributes=True)


def get_signal_trend_data(
    db: Session, signal_id: str
) -> Optional[List[Dict[str, int | str]]]:
    """Aggregate supporting processed reports by quarter for a signal."""
    signal = db.execute(
        select(
            SignalModel.drug_name,
            SignalModel.event_name,
            SignalModel.dataset_version,
        ).where(SignalModel.signal_id == signal_id)
    ).first()
    if signal is None:
        return None

    drug_name, event_name, dataset_version = signal
    filters = [ProcessedReportModel.drug_name == drug_name]
    if dataset_version:
        filters.append(ProcessedReportModel.report_quarter == dataset_version)

    if db.get_bind().dialect.name == "postgresql":
        filters.append(
            cast(ProcessedReportModel.reactions, JSONB).contains([event_name.upper()])
        )
        rows = db.execute(
            select(
                ProcessedReportModel.report_quarter,
                func.count().label("count"),
            )
            .where(*filters)
            .group_by(ProcessedReportModel.report_quarter)
            .order_by(ProcessedReportModel.report_quarter)
        ).all()
        return [
            {"quarter": row.report_quarter, "count": int(row.count)}
            for row in rows
        ]

    # SQLite does not support PostgreSQL JSONB containment. Keep the same
    # drug/quarter scope, then apply the existing reaction-list semantics.
    candidates = db.scalars(
        select(ProcessedReportModel).where(*filters)
    ).all()
    event = event_name.upper()
    counts: Dict[str, int] = {}
    for report in candidates:
        if (
            isinstance(report.reactions, list)
            and any(
                isinstance(reaction, str) and reaction.upper() == event
                for reaction in report.reactions
            )
        ):
            counts[report.report_quarter] = counts.get(report.report_quarter, 0) + 1

    return [
        {"quarter": quarter, "count": counts[quarter]}
        for quarter in sorted(counts)
    ]


def get_signal_metrics(db: Session, signal_id: str) -> Optional[SignalMetrics]:
    """Retrieve supporting metrics for a candidate signal."""
    stmt = select(SignalMetricsModel).where(SignalMetricsModel.signal_id == signal_id)
    m = db.scalars(stmt).first()
    if m:
        trend_data = m.trend_data
        if trend_data is None:
            trend_data = get_signal_trend_data(db, signal_id)
        return SignalMetrics(
            signal_id=m.signal_id,
            prr=m.prr,
            ror=m.ror,
            report_count=m.report_count,
            contingency_table=m.contingency_table,
            trend_data=trend_data,
            chi_square=m.chi_square,
        )

    # Fallback to base signal if metrics row not separately materialized
    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    return SignalMetrics(
        signal_id=sig.signal_id,
        prr=sig.prr,
        ror=sig.ror,
        report_count=sig.supporting_report_count,
        trend_data=get_signal_trend_data(db, signal_id),
    )


def get_signal_evidence(db: Session, signal_id: str) -> Optional[EvidenceBundle]:
    """Construct a structured evidence bundle for a signal."""
    from rules.engine import evaluate_regulatory_impact

    sig_stmt = select(SignalModel).where(SignalModel.signal_id == signal_id)
    sig = db.scalars(sig_stmt).first()
    if not sig:
        return None

    # Retrieve metrics
    metrics = get_signal_metrics(db, signal_id)
    metrics_dict = (
        metrics.model_dump()
        if metrics
        else {
            "prr": sig.prr,
            "ror": sig.ror,
            "report_count": sig.supporting_report_count,
            "trend_score": sig.trend_score,
        }
    )

    # Reuse the canonical materialized-or-computed case-quality service.
    from services.investigation_service import get_case_quality_for_signal

    case_quality_report = get_case_quality_for_signal(db, signal_id)

    # Retrieve potential duplicate candidates
    dup_stmt = select(DuplicateCandidateModel).where(
        DuplicateCandidateModel.signal_id == signal_id
    )
    dups = db.scalars(dup_stmt).all()
    duplicate_candidates = [
        DuplicateCandidate(
            candidate_id=d.candidate_id,
            report_id_a=d.report_id_a,
            report_id_b=d.report_id_b,
            rationale=d.rationale,
            status=d.status,
            similarity_score=d.similarity_score,
            drug_similarity=d.drug_similarity,
            event_similarity=d.event_similarity,
            date_proximity_days=d.date_proximity_days,
            matched_fields=d.matched_fields or [],
        )
        for d in dups
    ]
    regulatory = evaluate_regulatory_impact(db, signal_id)

    return EvidenceBundle(
        signal_id=sig.signal_id,
        drug_name=sig.drug_name,
        event_name=sig.event_name,
        candidate_status=sig.candidate_status,
        priority_level=sig.priority_level,
        risk_score=sig.risk_score,
        dataset_version=sig.dataset_version,
        metrics=metrics_dict,
        case_quality=case_quality_report,
        potential_duplicates=duplicate_candidates,
        known_limitations=sig.known_limitations or [
            "FAERS reports represent spontaneous reports and do not prove causality.",
            "Underreporting and reporting bias are inherent limitations of spontaneous data.",
        ],
        regulatory_review_areas=(
            [area.model_dump() for area in regulatory.review_areas] if regulatory else []
        ),
        regulatory_rule_matches=(
            [match.model_dump() for match in regulatory.rule_matches] if regulatory else []
        ),
        human_review_required=True,
    )
