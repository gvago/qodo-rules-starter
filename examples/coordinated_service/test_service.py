import unittest
from service import dispatch


class ServiceTest(unittest.TestCase):
    def test_config_defaults(self):
        self.assertEqual(dispatch("POST", "/v2/offers", {}, {"offers_v2": {"default_nights": 7, "search_type": "semantic"}}), (200, {"nights": 7, "search_type": "semantic"}))

    def test_explicit_value(self):
        self.assertEqual(dispatch("POST", "/v2/offers", {"nights": 3}, {"offers_v2": {"default_nights": 7}})[1]["nights"], 3)

    def test_missing_config(self):
        self.assertEqual(dispatch("POST", "/v2/offers", {}, {})[0], 503)

    def test_invalid_value(self):
        self.assertEqual(dispatch("POST", "/v2/offers", {"nights": True}, {"offers_v2": {}})[0], 400)

    def test_unknown_route(self):
        self.assertEqual(dispatch("GET", "/unknown", {}, {})[0], 404)


if __name__ == "__main__":
    unittest.main()
