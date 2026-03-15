"""
OCR Service — integrates with Google Cloud Vision AI to extract receipt data.
Falls back to a mock response during local development when no API key is set.
"""
import base64
import json
import re
from datetime import datetime
from typing import Any

from app.core.config import get_settings

settings = get_settings()


async def extract_receipt_data(file_bytes: bytes, content_type: str) -> dict[str, Any]:
    """
    Send image/PDF bytes to Cloud Vision AI and return structured receipt data:
    {
        "vendor": str | None,
        "total_amount": float | None,
        "date": datetime | None,
        "raw_text": str,
        "items": [{"name": str, "quantity": int | None, "price": float | None}]
    }
    """
    if not settings.GOOGLE_API_KEY and not settings.GCP_PROJECT_ID and not settings.GOOGLE_APPLICATION_CREDENTIALS:
        return _mock_ocr_response()

    try:
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=file_bytes)
        response = client.document_text_detection(image=image)

        if response.error.message:
            raise RuntimeError(f"Vision API error: {response.error.message}")

        raw_text = response.full_text_annotation.text
        return _parse_ocr_text(raw_text)

    except ImportError:
        # google-cloud-vision not installed — use mock for local dev
        return _mock_ocr_response()
    except Exception as exc:
        if (
            settings.ENABLE_DEV_AUTH
            and not settings.GOOGLE_APPLICATION_CREDENTIALS
            and not settings.GOOGLE_API_KEY
            and not settings.GCP_PROJECT_ID
        ):
            # In local dev mode we prefer resilient behavior over hard failure.
            return _mock_ocr_response()
        raise RuntimeError(f"OCR processing unavailable: {exc}") from exc


def _parse_ocr_text(raw_text: str) -> dict[str, Any]:
    """
    Use simple heuristics to extract vendor, total, date, and line items
    from raw OCR text. Gemini further refines this in the parsing agent.
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]

    vendor = lines[0] if lines else None

    total_amount = None
    total_pattern = re.compile(r"\b(?:grand\s*total|amount\s*due|total)\b[^\d]*\$?([\d,]+\.?\d*)", re.IGNORECASE)
    for line in lines:
        normalized_line = line.lower().replace(" ", "")
        if "subtotal" in normalized_line:
            continue
        m = total_pattern.search(line)
        if m:
            total_amount = float(m.group(1).replace(",", ""))
            break

    # Fallback: last price-like value
    if total_amount is None:
        price_lines = [l for l in lines if re.search(r"\d+\.\d{2}", l)]
        if price_lines:
            m = re.search(r"([\d,]+\.\d{2})", price_lines[-1])
            if m:
                total_amount = float(m.group(1).replace(",", ""))

    date = None
    date_pattern = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})")
    for line in lines:
        m = date_pattern.search(line)
        if m:
            try:
                date = datetime.strptime(m.group(1), "%m/%d/%Y")
            except ValueError:
                try:
                    date = datetime.strptime(m.group(1), "%d/%m/%Y")
                except ValueError:
                    pass
            if date:
                break

    # Extract line items from common OCR variants:
    # - "Apple 2 $1.00"
    # - "Milk $2.99"
    # - split lines: "Apple" then next line "$1.00"
    items = []
    item_with_qty_pattern = re.compile(r"^(.+?)\s+(?:x\s*)?(\d+)\s+\$?([\d,]+\.\d{2})$", re.IGNORECASE)
    item_simple_pattern = re.compile(r"^(.+?)\s+\$?([\d,]+\.\d{2})$")
    price_only_pattern = re.compile(r"^\$?\s*([\d,]+\.\d{2})$")
    ignore_keywords = {
        "total",
        "subtotal",
        "tax",
        "amount due",
        "payment",
        "cashier",
        "date",
        "time",
        "tel",
        "thank you",
        "pre-approved receipt item",
        "item",
        "qty",
        "price",
    }

    i = 0
    while i < len(lines):
        line = lines[i]
        lowered = line.lower().strip()

        if any(keyword in lowered for keyword in ignore_keywords):
            i += 1
            continue

        # Ignore isolated price-only lines unless paired with a previous name line.
        if price_only_pattern.match(line):
            i += 1
            continue

        m_qty = item_with_qty_pattern.match(line)
        if m_qty:
            name = m_qty.group(1).strip(" -:\t")
            quantity = int(m_qty.group(2))
            price = float(m_qty.group(3).replace(",", ""))
            if name:
                items.append({"name": name, "quantity": quantity, "price": price})
            i += 1
            continue

        m_simple = item_simple_pattern.match(line)
        if m_simple:
            name = m_simple.group(1).strip(" -:\t")
            price = float(m_simple.group(2).replace(",", ""))
            if name:
                items.append({"name": name, "quantity": 1, "price": price})
            i += 1
            continue

        # Handle OCR where item name and price are split across adjacent lines.
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            next_lowered = next_line.lower().strip()
            next_price = price_only_pattern.match(next_line)
            is_header_like = lowered in {"name", "item", "description", "price"}
            if (
                next_price
                and not is_header_like
                and not any(keyword in next_lowered for keyword in ignore_keywords)
                and ":" not in line
            ):
                name = line.strip(" -:\t")
                price = float(next_price.group(1).replace(",", ""))
                if name:
                    items.append({"name": name, "quantity": 1, "price": price})
                    i += 2
                    continue

        i += 1

    return {
        "vendor": vendor,
        "total_amount": total_amount,
        "date": date,
        "raw_text": raw_text,
        "items": items,
    }


def _mock_ocr_response() -> dict[str, Any]:
    """Deterministic mock used when Vision AI is unavailable (local dev)."""
    return {
        "vendor": "Sample Vendor",
        "total_amount": 45.50,
        "date": datetime(2026, 3, 14),
        "raw_text": "Sample Vendor\nItem A  30.00\nItem B  15.50\nTOTAL  45.50",
        "items": [
            {"name": "Item A", "quantity": 1, "price": 30.00},
            {"name": "Item B", "quantity": 1, "price": 15.50},
        ],
    }
