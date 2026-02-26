from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


DISPATCHER_PATH = Path(__file__).resolve().parents[1] / "dispatcher.py"
spec = importlib.util.spec_from_file_location("issue_dispatcher", DISPATCHER_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FailedDeliveryReplayTests(unittest.TestCase):
    def test_select_failed_deliveries_filters_success_redelivery_old_and_irrelevant_events(self) -> None:
        original_lookback = module.FAILED_DELIVERY_LOOKBACK_HOURS
        original_max = module.MAX_FAILED_DELIVERY_REPLAYS
        try:
            module.FAILED_DELIVERY_LOOKBACK_HOURS = 24
            module.MAX_FAILED_DELIVERY_REPLAYS = 25
            deliveries = [
                {
                    "id": 1,
                    "event": "issue_comment",
                    "status_code": 503,
                    "redelivery": False,
                    "delivered_at": "2026-02-26T00:17:54.410Z",
                },
                {
                    "id": 2,
                    "event": "issue_comment",
                    "status_code": 200,
                    "redelivery": False,
                    "delivered_at": "2026-02-26T00:18:54.410Z",
                },
                {
                    "id": 3,
                    "event": "ping",
                    "status_code": 503,
                    "redelivery": False,
                    "delivered_at": "2026-02-26T00:18:54.410Z",
                },
                {
                    "id": 4,
                    "event": "pull_request_review",
                    "status_code": 503,
                    "redelivery": True,
                    "delivered_at": "2026-02-26T00:18:54.410Z",
                },
                {
                    "id": 5,
                    "event": "issues",
                    "status_code": 503,
                    "redelivery": False,
                    "delivered_at": "2000-01-01T00:00:00.000Z",
                },
            ]
            selected = module._select_failed_deliveries_for_replay(deliveries)
            self.assertEqual(selected, [1])
        finally:
            module.FAILED_DELIVERY_LOOKBACK_HOURS = original_lookback
            module.MAX_FAILED_DELIVERY_REPLAYS = original_max

    def test_select_failed_deliveries_applies_max_limit(self) -> None:
        original_lookback = module.FAILED_DELIVERY_LOOKBACK_HOURS
        original_max = module.MAX_FAILED_DELIVERY_REPLAYS
        try:
            module.FAILED_DELIVERY_LOOKBACK_HOURS = 24 * 365 * 10
            module.MAX_FAILED_DELIVERY_REPLAYS = 2
            deliveries = [
                {
                    "id": 10,
                    "event": "issue_comment",
                    "status_code": 503,
                    "redelivery": False,
                    "delivered_at": "2026-02-26T00:10:00.000Z",
                },
                {
                    "id": 11,
                    "event": "issue_comment",
                    "status_code": 503,
                    "redelivery": False,
                    "delivered_at": "2026-02-26T00:11:00.000Z",
                },
                {
                    "id": 12,
                    "event": "issue_comment",
                    "status_code": 503,
                    "redelivery": False,
                    "delivered_at": "2026-02-26T00:12:00.000Z",
                },
            ]
            selected = module._select_failed_deliveries_for_replay(deliveries)
            self.assertEqual(selected, [11, 12])
        finally:
            module.FAILED_DELIVERY_LOOKBACK_HOURS = original_lookback
            module.MAX_FAILED_DELIVERY_REPLAYS = original_max


if __name__ == "__main__":
    unittest.main()
