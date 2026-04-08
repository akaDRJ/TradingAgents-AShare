import tempfile
import unittest
from pathlib import Path

from cli.reporting import build_default_report_save_path, save_report_to_disk


class ReportSavePathTests(unittest.TestCase):
    def test_default_report_save_path_uses_results_report_dir(self):
        config = {"results_dir": "./results"}

        save_path = build_default_report_save_path(
            config=config,
            ticker="000960",
            analysis_date="2026-04-08",
        )

        self.assertEqual(
            save_path,
            Path("results") / "000960" / "2026-04-08" / "reports",
        )

    def test_save_report_to_disk_can_write_only_complete_report(self):
        final_state = {
            "market_report": "market",
            "sentiment_report": "sentiment",
            "news_report": "news",
            "fundamentals_report": "fundamentals",
            "investment_debate_state": {
                "bull_history": "bull",
                "bear_history": "bear",
                "judge_decision": "research manager",
            },
            "trader_investment_plan": "trade plan",
            "risk_debate_state": {
                "aggressive_history": "aggressive",
                "conservative_history": "conservative",
                "neutral_history": "neutral",
                "judge_decision": "portfolio decision",
            },
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = Path(tmpdir) / "reports"
            report_file = save_report_to_disk(
                final_state,
                "000960",
                save_path,
                include_subdirectories=False,
            )

            self.assertEqual(report_file, save_path / "complete_report.md")
            self.assertTrue(report_file.exists())
            self.assertFalse((save_path / "1_analysts").exists())
            self.assertFalse((save_path / "2_research").exists())
            self.assertFalse((save_path / "3_trading").exists())
            self.assertFalse((save_path / "4_risk").exists())
            self.assertFalse((save_path / "5_portfolio").exists())


if __name__ == "__main__":
    unittest.main()
