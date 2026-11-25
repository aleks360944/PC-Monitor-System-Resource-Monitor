import csv
import io
import tempfile
import unittest
from pathlib import Path

from gpu_monitor import GPULogReader, parse_gpu_csv_line


def make_gpu_line(gpu_usage="42.5", vram="2048", temperature="65", core_clock="1500", memory_clock="7000"):
    row = [""] * 26
    row[0] = "2026-11-25 12:00:00.123456"
    row[18] = gpu_usage
    row[20] = vram
    row[21] = temperature
    row[24] = core_clock
    row[25] = memory_clock
    output = io.StringIO()
    csv.writer(output).writerow(row)
    return output.getvalue().encode("utf-8")


EXPECTED_RECORD = {
    "gpu_usage": 42.5,
    "vram_used_mb": 2048.0,
    "temperature": 65.0,
    "core_clock_mhz": 1500.0,
    "memory_clock_mhz": 7000.0,
}


class GPUMonitorTests(unittest.TestCase):
    def test_parse_valid_csv_record(self):
        self.assertEqual(EXPECTED_RECORD, parse_gpu_csv_line(make_gpu_line()))

    def test_unknown_metrics_are_returned_as_not_supported(self):
        result = parse_gpu_csv_line(make_gpu_line(gpu_usage="?"))
        self.assertEqual("N/S", result["gpu_usage"])
        self.assertEqual(2048.0, result["vram_used_mb"])

    def test_non_finite_metrics_are_returned_as_not_supported(self):
        result = parse_gpu_csv_line(make_gpu_line(gpu_usage="nan"))
        self.assertEqual("N/S", result["gpu_usage"])

    def test_malformed_or_incomplete_csv_is_ignored(self):
        self.assertIsNone(parse_gpu_csv_line(b""))
        self.assertIsNone(parse_gpu_csv_line(b"not,a,valid,record\n"))
        self.assertIsNone(parse_gpu_csv_line(make_gpu_line(gpu_usage="not-a-number")))

    def test_reader_keeps_last_valid_sample_after_bad_line(self):
        with tempfile.TemporaryDirectory() as folder:
            log_path = Path(folder) / "hw-smi-test.log"
            log_path.write_bytes(make_gpu_line())
            reader = GPULogReader(folder)
            self.assertEqual(EXPECTED_RECORD, reader.get_data())

            with log_path.open("ab") as file:
                file.write(b"invalid,csv,row\n")
            self.assertEqual(EXPECTED_RECORD, reader.get_data())

    def test_reader_returns_empty_record_for_missing_log(self):
        with tempfile.TemporaryDirectory() as folder:
            reader = GPULogReader(folder)
            self.assertEqual(GPULogReader._empty_record(), reader.get_data())


if __name__ == "__main__":
    unittest.main()
