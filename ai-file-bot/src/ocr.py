from __future__ import annotations

import base64
import io
import logging
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from openai import OpenAI


LOGGER = logging.getLogger("ai-file-bot.ocr")

OCR_BASE_URL = os.getenv(
    "OCR_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
OCR_API_KEY = os.getenv("OCR_API_KEY", "")
OCR_MODEL = os.getenv("OCR_MODEL", "qwen3.5-ocr")
OCR_MAX_TOKENS = int(os.getenv("OCR_MAX_TOKENS", "4096"))
OCR_TIMEOUT_SECONDS = float(os.getenv("OCR_TIMEOUT_SECONDS", "90"))
OCR_MAX_WORKERS = int(os.getenv("OCR_MAX_WORKERS", "5"))
OCR_PDF_DPI = int(os.getenv("OCR_PDF_DPI", "200"))
OCR_MAX_PDF_PAGES = int(os.getenv("OCR_MAX_PDF_PAGES", "20"))
OCR_MIN_CHARS = int(os.getenv("OCR_MIN_CHARS", "2"))
PADDLE_OCR_LANG = os.getenv("PADDLE_OCR_LANG", "ch")
PADDLE_OCR_DEVICE = os.getenv("PADDLE_OCR_DEVICE", "cpu")

IMAGE_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

OCR_PROMPT = """请识别图片中的全部文字，并按原有阅读顺序输出。
保留标题、段落、列表和表格结构，表格使用 Markdown 格式。
只输出识别结果，不要解释，不要总结，不要补充图片中不存在的内容。
无法辨认的单个字符使用 ? 表示。"""


class OCRError(Exception):
    pass


def extract_ocr_text(file_path: Path, original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    if suffix in IMAGE_MIME_TYPES:
        pages = [(1, file_path.read_bytes(), IMAGE_MIME_TYPES[suffix])]
        return _recognize_pages(pages, "图片")
    if suffix == ".pdf":
        return _recognize_pages(_pdf_to_images(file_path), "PDF")
    raise OCRError(f"不支持 OCR 文件类型：{suffix or '未知'}")


def _pdf_to_images(file_path: Path) -> list[tuple[int, bytes, str]]:
    from pdf2image import convert_from_path, pdfinfo_from_path

    page_count = int(pdfinfo_from_path(str(file_path)).get("Pages", 0))
    if page_count < 1:
        raise OCRError("无法读取 PDF 页数")
    if page_count > OCR_MAX_PDF_PAGES:
        raise OCRError(
            f"PDF 共 {page_count} 页，超过 OCR 上限 {OCR_MAX_PDF_PAGES} 页"
        )

    images = convert_from_path(
        str(file_path),
        dpi=OCR_PDF_DPI,
        fmt="jpeg",
        first_page=1,
        last_page=page_count,
        thread_count=min(OCR_MAX_WORKERS, page_count),
    )
    pages: list[tuple[int, bytes, str]] = []
    for page_number, image in enumerate(images, start=1):
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        pages.append((page_number, buffer.getvalue(), "image/jpeg"))
    return pages


def _recognize_pages(
    pages: list[tuple[int, bytes, str]], document_type: str
) -> str:
    cloud_results: dict[int, str] = {}
    cloud_errors: dict[int, Exception] = {}

    if OCR_API_KEY:
        worker_count = max(1, min(OCR_MAX_WORKERS, len(pages)))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(_cloud_ocr, image_bytes, mime_type): page_number
                for page_number, image_bytes, mime_type in pages
            }
            for future in as_completed(futures):
                page_number = futures[future]
                try:
                    text = future.result().strip()
                    if not _has_enough_text(text):
                        raise OCRError("云端 OCR 未返回有效文字")
                    cloud_results[page_number] = text
                except Exception as exc:
                    cloud_errors[page_number] = exc
                    LOGGER.warning(
                        "%s page %s cloud OCR failed, using PaddleOCR: %s",
                        document_type,
                        page_number,
                        exc,
                    )
    else:
        LOGGER.warning("OCR_API_KEY is not configured, using PaddleOCR directly")
        cloud_errors = {
            page_number: OCRError("未配置云端 OCR 密钥")
            for page_number, _, _ in pages
        }

    results: list[str] = []
    for page_number, image_bytes, _ in pages:
        text = cloud_results.get(page_number)
        if text is None:
            try:
                text = _paddle_ocr(image_bytes).strip()
                if not _has_enough_text(text):
                    raise OCRError("PaddleOCR 未返回有效文字")
                LOGGER.info("%s page %s recognized by PaddleOCR", document_type, page_number)
            except Exception as exc:
                LOGGER.error(
                    "%s page %s OCR failed; cloud=%s; paddle=%s",
                    document_type,
                    page_number,
                    cloud_errors.get(page_number),
                    exc,
                )
                raise OCRError(
                    f"{document_type}第 {page_number} 页未识别到有效文字，请上传更清晰的文件"
                ) from exc
        else:
            LOGGER.info("%s page %s recognized by cloud OCR", document_type, page_number)
        results.append(f"--- Page {page_number} (OCR) ---\n{text}")

    return "\n\n".join(results)


def _cloud_ocr(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    client = OpenAI(
        api_key=OCR_API_KEY,
        base_url=OCR_BASE_URL,
        timeout=OCR_TIMEOUT_SECONDS,
    )
    response = client.chat.completions.create(
        model=OCR_MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{encoded}",
                        },
                    },
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ],
        max_tokens=OCR_MAX_TOKENS,
        temperature=0,
    )
    return response.choices[0].message.content or ""


_PADDLE_OCR = None
_PADDLE_LOCK = threading.Lock()


def _paddle_ocr(image_bytes: bytes) -> str:
    global _PADDLE_OCR

    from paddleocr import PaddleOCR

    with _PADDLE_LOCK:
        if _PADDLE_OCR is None:
            LOGGER.info("initializing PaddleOCR fallback on %s", PADDLE_OCR_DEVICE)
            _PADDLE_OCR = PaddleOCR(
                lang=PADDLE_OCR_LANG,
                ocr_version="PP-OCRv5",
                device=PADDLE_OCR_DEVICE,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            image_file.write(image_bytes)
            image_file.flush()
            predictions = _PADDLE_OCR.predict(
                image_file.name,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
            )

        texts: list[str] = []
        for prediction in predictions:
            payload = prediction.json
            if callable(payload):
                payload = payload()
            result = payload.get("res", payload)
            texts.extend(result.get("rec_texts") or [])
        return "\n".join(texts)


def _has_enough_text(text: str) -> bool:
    return len("".join(text.split())) >= OCR_MIN_CHARS
