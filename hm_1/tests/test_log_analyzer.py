import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)  # noqa: E402
from src.log_analyzer import generate_report, iter_log_records


def test_iter_log_records():
    log_data = (
        "1.196.116.32 - - [29/Jun/2017:03:50:22 +0300] "
        '"GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "User-Agent" "-" "ID" "-" 0.390'
    )
    records = list(iter_log_records(log_data))
    # We expect one record (and its URL is '/api/v2/banner/25019354')
    assert len(records) == 1
    rec = records[0]
    assert rec is not None
    assert rec["url"] == "/api/v2/banner/25019354"
    assert abs(rec["time"] - 0.390) < 0.0001


def test_generate_report():
    # Create dummy stats for two URLs
    dummy_stats = {
        "/url1": {
            "url": "/url1",
            "time_sum": 1.0,
            "count": 2,
            "count_perc": 50,
            "time_perc": 25,
            "time_avg": 0.5,
            "time_max": 0.6,
            "time_med": 0.5,
        },
        "/url2": {
            "url": "/url2",
            "time_sum": 2.0,
            "count": 3,
            "count_perc": 75,
            "time_perc": 50,
            "time_avg": 0.67,
            "time_max": 0.8,
            "time_med": 0.7,
        },
    }
    report_json = generate_report(dummy_stats, report_size=1)
    import json

    parsed = json.loads(report_json)
    # Since sorting is by time_sum descending, /url2 should be the only record returned.
    assert len(parsed) == 1
    assert parsed[0]["url"] == "/url2"
