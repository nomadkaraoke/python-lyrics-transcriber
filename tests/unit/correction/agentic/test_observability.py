from lyrics_transcriber.correction.agentic.observability.metrics import MetricsAggregator


def test_metrics_aggregator_records_sessions_and_feedback():
    m = MetricsAggregator()
    m.record_session("gpt-5", 120, False)
    m.record_session("gpt-5", 80, True)
    m.record_feedback()
    snap = m.snapshot()
    assert snap["totalSessions"] == 2
    assert snap["averageProcessingTime"] in (100, 99)  # integer division rounding
    assert m.total_feedback == 1


