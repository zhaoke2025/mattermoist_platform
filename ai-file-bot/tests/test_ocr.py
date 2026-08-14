from __future__ import annotations

import unittest
from unittest.mock import patch

from src import ocr


class RecognizePagesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = [(1, b"image", "image/jpeg")]

    @patch.object(ocr, "OCR_API_KEY", "cloud-key")
    @patch.object(ocr, "_paddle_ocr")
    @patch.object(ocr, "_cloud_ocr", return_value="云端识别结果")
    def test_cloud_is_primary(self, cloud_ocr, paddle_ocr) -> None:
        result = ocr._recognize_pages(self.pages, "图片")

        self.assertIn("云端识别结果", result)
        cloud_ocr.assert_called_once()
        paddle_ocr.assert_not_called()

    @patch.object(ocr, "OCR_API_KEY", "cloud-key")
    @patch.object(ocr, "_paddle_ocr", return_value="本地识别结果")
    @patch.object(ocr, "_cloud_ocr", side_effect=TimeoutError("cloud timeout"))
    def test_paddle_falls_back_when_cloud_fails(self, cloud_ocr, paddle_ocr) -> None:
        result = ocr._recognize_pages(self.pages, "图片")

        self.assertIn("本地识别结果", result)
        cloud_ocr.assert_called_once()
        paddle_ocr.assert_called_once_with(b"image")

    @patch.object(ocr, "OCR_API_KEY", "cloud-key")
    @patch.object(ocr, "_paddle_ocr", return_value="")
    @patch.object(ocr, "_cloud_ocr", return_value="")
    def test_clear_error_when_both_engines_find_no_text(
        self, cloud_ocr, paddle_ocr
    ) -> None:
        with self.assertRaisesRegex(ocr.OCRError, "未识别到有效文字"):
            ocr._recognize_pages(self.pages, "图片")


if __name__ == "__main__":
    unittest.main()
