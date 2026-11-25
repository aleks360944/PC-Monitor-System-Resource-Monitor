import unittest

from health_checker import check_cpu, check_ram, check_storage


class HealthCheckerTests(unittest.TestCase):
    def test_missing_cpu_and_ram_data_are_unknown(self):
        self.assertEqual("UNKNOWN", check_cpu({})[0]["level"])
        self.assertEqual("UNKNOWN", check_ram({})[0]["level"])

    def test_invalid_cpu_and_ram_percentages_are_unknown(self):
        for invalid in ("unknown", True, float("nan"), 101, -1, 10 ** 10000):
            with self.subTest(invalid=invalid):
                self.assertEqual("UNKNOWN", check_cpu({"usage": invalid})[0]["level"])
                self.assertEqual("UNKNOWN", check_ram({"usage": invalid})[0]["level"])

    def test_cpu_thresholds(self):
        self.assertEqual("OK", check_cpu({"usage": 79.9})[0]["level"])
        self.assertEqual("WARNING", check_cpu({"usage": 80})[0]["level"])
        self.assertEqual("CRITICAL", check_cpu({"usage": 95})[0]["level"])

    def test_missing_storage_data_is_unknown(self):
        self.assertEqual("UNKNOWN", check_storage([])[0]["level"])

    def test_invalid_disk_records_are_reported_as_unknown(self):
        results = check_storage([None, {"device": "D:", "mountpoint": "D:\\", "usage": "full"}])
        self.assertEqual(["UNKNOWN", "UNKNOWN"], [item["level"] for item in results])


if __name__ == "__main__":
    unittest.main()
