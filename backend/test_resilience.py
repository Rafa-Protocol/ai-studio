import unittest
from unittest.mock import patch, MagicMock
import time

class TestResilience(unittest.TestCase):

    def test_macro_engine_empty_data(self):
        import macro_engine
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"code": "0", "data": []}
            result = macro_engine.get_macro_health()
            self.assertEqual(result["sentiment"], "NEUTRAL")
            self.assertIn("⚠️ ETF Data Unavailable", result["details"])
            self.assertIn("⚠️ Funding Data Unavailable", result["details"])

    def test_macro_engine_valid_data(self):
        import macro_engine
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "code": "0",
                "data": [
                    {"timestamp": 1710000000000, "flow_usd": 50000000},
                    {"timestamp": 1709900000000, "flow_usd": 20000000}
                ]
            }
            result = macro_engine.get_macro_health()
            self.assertIn("+$70.0M", result["details"])

    def test_quant_engine_safe_handling(self):
        import quant_engine
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 500
            data = quant_engine.get_token_data("ETH")
            self.assertIsNone(data)

    def test_price_cache_initialization_and_update(self):
        import main
        # Keys must all exist initially to prevent KeyError in run_strategy context_injection
        for key in ["eth", "btc", "sol", "usdc", "link", "uni", "comp", "aave", "pepe"]:
            self.assertIn(key, main.PRICE_CACHE)

        # Successful update
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "ethereum": {"usd": 3500.0},
                "uniswap": {"usd": 11.5}
            }
            main.PRICE_CACHE["last_updated"] = 0
            main.update_price_cache()
            self.assertEqual(main.PRICE_CACHE["eth"], 3500.0)
            self.assertEqual(main.PRICE_CACHE["uni"], 11.5)

        # Rate-limited or failed update preserves existing prices
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 429
            mock_get.return_value.json.return_value = {"status": {"error_code": 429}}
            main.PRICE_CACHE["last_updated"] = 0
            main.update_price_cache()
            self.assertEqual(main.PRICE_CACHE["eth"], 3500.0)
            self.assertEqual(main.PRICE_CACHE["uni"], 11.5)
            self.assertGreater(main.PRICE_CACHE["last_updated"], 0)

    def test_agent_missing_tavily_key(self):
        import agent
        self.assertIsNone(agent.tavily_client)
        news_result = agent.get_news_sentiment.invoke({"query": "BTC"})
        self.assertIn("News intelligence unavailable", news_result)

if __name__ == "__main__":
    unittest.main()
