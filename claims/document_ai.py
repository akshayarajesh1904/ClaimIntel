import os
import re
from collections import Counter
import shutil

import pymupdf
from docx import Document

from PIL import (
    Image,
    ImageOps,
    ImageEnhance,
    ImageFilter
)

import pytesseract


# ============================================================
# TESSERACT CONFIGURATION
# ============================================================

tesseract_executable = os.getenv('TESSERACT_PATH', shutil.which('tesseract') or r"C:\Program Files\Tesseract-OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_executable


# ============================================================
# IMAGE PREPROCESSING
# ============================================================

def preprocess_image(image):
    """
    Preprocess a printed document image before OCR.

    Steps:
    1. Convert to grayscale
    2. Automatically improve contrast
    3. Upscale smaller images
    4. Sharpen text
    5. Increase contrast
    """

    # Convert to grayscale
    image = image.convert("L")

    # Automatically improve contrast
    image = ImageOps.autocontrast(image)

    # Upscale small images
    width, height = image.size

    if width < 1600:

        scale = 1600 / width

        image = image.resize(
            (
                int(width * scale),
                int(height * scale)
            ),
            Image.Resampling.LANCZOS
        )

    # Sharpen text
    image = image.filter(
        ImageFilter.SHARPEN
    )

    # Increase contrast
    image = ImageEnhance.Contrast(
        image
    ).enhance(1.5)

    return image


# ============================================================
# OCR IMAGE
# ============================================================

def ocr_image(image):
    """
    Extract printed text from an image using Tesseract.

    Two page segmentation modes are tested and the
    strongest OCR result is selected.
    """

    processed_image = preprocess_image(
        image
    )

    results = []


    # --------------------------------------------------------
    # Try two OCR layouts
    # --------------------------------------------------------

    for psm in [6, 11]:

        config = (
            f"--oem 3 --psm {psm}"
        )

        try:

            data = pytesseract.image_to_data(
                processed_image,
                config=config,
                output_type=pytesseract.Output.DICT
            )

            words = []
            confidence_values = []


            for text, confidence in zip(
                data["text"],
                data["conf"]
            ):

                text = text.strip()

                if not text:
                    continue

                words.append(text)


                try:

                    confidence = float(
                        confidence
                    )

                    if confidence >= 0:

                        confidence_values.append(
                            confidence
                        )

                except ValueError:
                    pass


            extracted_text = " ".join(
                words
            ).strip()


            if confidence_values:

                average_confidence = (
                    sum(confidence_values)
                    / len(confidence_values)
                )

            else:

                average_confidence = 0


            results.append(
                (
                    extracted_text,
                    average_confidence
                )
            )


        except Exception as error:

            print(
                "OCR error:",
                error
            )


    # --------------------------------------------------------
    # No OCR result
    # --------------------------------------------------------

    if not results:
        return ""


    # --------------------------------------------------------
    # Select strongest result
    # --------------------------------------------------------

    results.sort(
        key=lambda item: (
            item[1],
            len(item[0])
        ),
        reverse=True
    )


    return results[0][0]


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text_from_file(file_path):
    """
    Extract readable text from:

    - Digital PDFs
    - Scanned / printed PDFs
    - DOCX
    - TXT
    - Printed image files
    """

    extension = os.path.splitext(
        file_path
    )[1].lower()


    # ========================================================
    # PDF
    # ========================================================

    if extension == ".pdf":

        text_parts = []


        document = pymupdf.open(
            file_path
        )


        # ----------------------------------------------------
        # First attempt: normal PDF text extraction
        # ----------------------------------------------------

        for page in document:

            page_text = page.get_text(
                "text"
            ).strip()

            if page_text:

                text_parts.append(
                    page_text
                )


        document.close()


        extracted_text = "\n".join(
            text_parts
        ).strip()


        # ----------------------------------------------------
        # Scanned / printed PDF fallback
        # ----------------------------------------------------

        if not extracted_text:

            document = pymupdf.open(
                file_path
            )

            ocr_parts = []


            for page in document:

                # Render page at higher resolution
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(
                        2.5,
                        2.5
                    ),
                    alpha=False
                )


                image = Image.frombytes(
                    "RGB",
                    [
                        pixmap.width,
                        pixmap.height
                    ],
                    pixmap.samples
                )


                page_text = ocr_image(
                    image
                )


                if page_text:

                    ocr_parts.append(
                        page_text
                    )


            document.close()


            extracted_text = "\n".join(
                ocr_parts
            ).strip()


        return extracted_text


    # ========================================================
    # DOCX
    # ========================================================

    if extension == ".docx":

        document = Document(
            file_path
        )


        paragraphs = []


        for paragraph in document.paragraphs:

            text = paragraph.text.strip()


            if text:

                paragraphs.append(
                    text
                )


        return "\n".join(
            paragraphs
        ).strip()


    # ========================================================
    # TXT
    # ========================================================

    if extension == ".txt":

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            return file.read().strip()


    # ========================================================
    # PRINTED IMAGE FILES
    # ========================================================

    if extension in (
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tiff",
        ".webp",
        ".jfif"
    ):

        image = Image.open(
            file_path
        )


        return ocr_image(
            image
        )


    # ========================================================
    # UNSUPPORTED FILE
    # ========================================================

    return ""


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:

        return ""


    # Replace multiple spaces/newlines
    text = re.sub(
        r"\s+",
        " ",
        text
    )


    return text.strip()


# ============================================================
# EXTRACTIVE SUMMARY
# ============================================================

def generate_summary(
    text,
    max_sentences=4
):
    """
    Lightweight extractive summary.

    Selects important sentences based on
    word-frequency scoring while preserving
    the original document wording.
    """

    text = clean_text(
        text
    )


    # --------------------------------------------------------
    # No text
    # --------------------------------------------------------

    if not text:

        return (
            "No readable text could be "
            "extracted from this document."
        )


    # --------------------------------------------------------
    # Split text into sentences
    # --------------------------------------------------------

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text
    )


    sentences = [
        sentence.strip()
        for sentence in sentences
        if len(sentence.strip()) > 20
    ]


    # --------------------------------------------------------
    # If no proper sentences found
    # --------------------------------------------------------

    if not sentences:

        return text[:800]


    # --------------------------------------------------------
    # Word frequency
    # --------------------------------------------------------

    words = re.findall(
        r"\b[a-zA-Z]{3,}\b",
        text.lower()
    )


    stop_words = {
        "the",
        "and",
        "that",
        "this",
        "with",
        "from",
        "have",
        "has",
        "for",
        "are",
        "was",
        "were",
        "been",
        "will",
        "shall",
        "into",
        "your",
        "their",
        "there",
        "which",
        "when",
        "where",
        "also",
        "than",
        "then"
    }


    words = [
        word
        for word in words
        if word not in stop_words
    ]


    frequencies = Counter(
        words
    )


    # --------------------------------------------------------
    # Score sentences
    # --------------------------------------------------------

    sentence_scores = []


    for index, sentence in enumerate(
        sentences
    ):

        sentence_words = re.findall(
            r"\b[a-zA-Z]{3,}\b",
            sentence.lower()
        )


        score = sum(
            frequencies.get(
                word,
                0
            )
            for word in sentence_words
        )


        # Small preference for earlier sentences
        position_bonus = max(
            0,
            10 - index
        )


        score += position_bonus


        sentence_scores.append(
            (
                score,
                index,
                sentence
            )
        )


    # --------------------------------------------------------
    # Select strongest sentences
    # --------------------------------------------------------

    selected = sorted(
        sentence_scores,
        key=lambda item: item[0],
        reverse=True
    )[:max_sentences]


    # --------------------------------------------------------
    # Restore original document order
    # --------------------------------------------------------

    selected = sorted(
        selected,
        key=lambda item: item[1]
    )


    # --------------------------------------------------------
    # Create final summary
    # --------------------------------------------------------

    summary = " ".join(
        item[2]
        for item in selected
    )


    return summary


# ============================================================
# DOCUMENT PROCESSING
# ============================================================

def process_document(file_path):
    """
    Complete document AI pipeline:

    File
      ↓
    Text extraction / OCR
      ↓
    Text cleaning
      ↓
    Extractive summary
    """

    text = extract_text_from_file(
        file_path
    )


    cleaned_text = clean_text(
        text
    )


    summary = generate_summary(
        cleaned_text
    )


    return (
        cleaned_text,
        summary
    )