import os

import fitz  # PyMuPDF

from PIL import Image
from loguru import logger


def pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 200,          # 🚀 Increased back to 200 for better text clarity
    max_width: int = 1400,   # 🚀 Increased to prevent blurring dense tables
    jpeg_quality: int = 90   # 🚀 Increased quality
):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)

    image_paths = []

    for page_no in range(len(doc)):
        page = doc[page_no]

        # Render PDF page → pixmap
        pix = page.get_pixmap(dpi=dpi, alpha=False)

        # Convert pixmap → PIL Image (KEEP AS RGB!)
        mode = "RGB"
        img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)

        # ❌ REMOVED: img = img.convert("L")  <-- DO NOT use grayscale for Vision LLMs

        # Resize if too large
        if img.width > max_width:
            ratio = max_width / img.width
            new_size = (max_width, int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS) # 🚀 Changed to LANCZOS (better for text)

        img_path = os.path.join(output_dir, f"page_{page_no + 1}.jpg")

        # Save optimized JPEG
        img.save(
            img_path,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True,
            subsampling=0  # 🚀 CRITICAL: 0 means 4:4:4 (No chroma blurring on text edges)
        )

        image_paths.append(img_path)

    logger.success(
        f"Converted {len(image_paths)} pages to optimized images "
        f"(dpi={dpi}, max_width={max_width})"
    )

    return image_paths
