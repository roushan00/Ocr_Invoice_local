import base64
import asyncio

from io import BytesIO
from pathlib import Path

from PyPDF2 import PdfReader, PdfWriter

# from rapidfuzz import fuzz

# def build_page_confidence_model(page_data: Invoice, page_ocr_text: str) -> InvoiceWithConfidence:
#     wrapped = wrap_with_confidence(page_data.model_dump(mode='json'), page_ocr_text)
#     return InvoiceWithConfidence.model_validate(wrapped)
def get_pdf_metadata(pdf_path: Path):
    """Synchronous function to get PDF metadata (runs in thread)."""
    file_size = pdf_path.stat().st_size
    reader = PdfReader(str(pdf_path))
    return file_size, len(reader.pages)



def get_pdf_segment_base64(original_pdf_path: str, page_indices: list[int]) -> str:
    reader = PdfReader(original_pdf_path)
    writer = PdfWriter()
    for idx in page_indices:
        writer.add_page(reader.pages[idx])
    output_stream = BytesIO()
    writer.write(output_stream)
    return base64.b64encode(output_stream.getvalue()).decode('utf-8')


# def compute_confidence(val, source_text):
#     if val is None or str(val).lower() == 'null' or val == '':
#         return None
#     score = fuzz.partial_ratio(str(val).lower(), source_text)
#     return round(score / 100.0, 3)


# def wrap_with_confidence(data, source_text):
#     if isinstance(data, dict):
#         return {k: wrap_with_confidence(v, source_text) for k, v in data.items()}
#     if isinstance(data, list):
#         return [wrap_with_confidence(item, source_text) for item in data]
#     return {'value': data, 'confidence': compute_confidence(data, source_text)}


# def wrap_line_item_with_confidence(item_dict: dict, source_text: str) -> dict:
#     """
#     Wraps only the top-level fields of a line item with confidence scores.
#     Does NOT recursively wrap nested structures.

#     Input:  {"product_code": "ABC123", "unit_price": 10.99}
#     Output: {"product_code": {"value": "ABC123", "confidence": 0.85}, ...}
#     """
#     result = {}
#     for key, value in item_dict.items():
#         result[key] = {
#             'value': value,
#             'confidence': compute_confidence(value, source_text),
#         }
#     return result


# def extract_confidences(obj) -> list[float]:
#     confidences = []
#     if isinstance(obj, dict):
#         if 'confidence' in obj and isinstance(obj['confidence'], (int, float)):
#             confidences.append(obj['confidence'])
#         for v in obj.values():
#             confidences.extend(extract_confidences(v))
#     elif isinstance(obj, list):
#         for item in obj:
#             confidences.extend(extract_confidences(item))
#     return confidences


# def get_overall_confidence(confidence_model: InvoiceWithConfidence) -> float:
#     dumped = confidence_model.model_dump(mode='json')
#     all_scores = extract_confidences(dumped)
#     if not all_scores:
#         return 0.0
#     return round(sum(all_scores) / len(all_scores), 3)


# def get_file_size_str(file_path: str) -> str:
#     try:
#         size_bytes = os.path.getsize(file_path)
#         if size_bytes < 1024:
#             return f'{size_bytes} B'
#         elif size_bytes < 1024 * 1024:
#             return f'{size_bytes / 1024:.2f} KB'
#         else:
#             return f'{size_bytes / (1024 * 1024):.2f} MB'
#     except Exception:
#         return 'Unknown'


processing_queues: dict[str, asyncio.Queue] = {}


# --- HELPER: Send Update to Queue ---
async def send_progress_update(unique_id: str, data: dict):
    """Pushes an update to the specific unique_id queue if it exists."""
    if unique_id in processing_queues:
        await processing_queues[unique_id].put(data)
