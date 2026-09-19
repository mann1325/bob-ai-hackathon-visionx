from ml.trend_scorer import compute_trend_score
from services.signal_service import get_signal_metrics, get_signal_trend_data


def test_trend_data_aggregates_matching_reports_by_quarter(db_session):
    trend_data = get_signal_trend_data(db_session, "sig-001")

    assert trend_data == [{"quarter": "2024Q1", "count": 2}]


def test_trend_data_requires_event_inside_reactions(db_session):
    trend_data = get_signal_trend_data(db_session, "sig-002")

    assert trend_data == [{"quarter": "2024Q1", "count": 1}]


def test_one_quarter_trend_score_remains_unavailable(db_session):
    metrics = get_signal_metrics(db_session, "sig-002")

    assert metrics is not None
    assert metrics.trend_data == [{"quarter": "2024Q1", "count": 1}]
    assert compute_trend_score(metrics.trend_data) is None


def test_multi_quarter_trend_data_integrates_with_existing_scorer(db_session):
    trend_data = [
        {"quarter": "2023Q4", "count": 10},
        {"quarter": "2024Q1", "count": 20},
    ]

    score = compute_trend_score(trend_data)

    assert score is not None
    assert score > 0