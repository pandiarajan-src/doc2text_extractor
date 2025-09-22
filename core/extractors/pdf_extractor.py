import logging
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class PDFExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.supported_extensions = [".pdf"]
        self.supported_mime_types = ["application/pdf"]

    def extract(self, file_path: Path, output_dir: Path) -> ExtractionResult:
        try:
            images_dir = output_dir / "images"
            images_dir.mkdir(exist_ok=True)

            text_content = []
            extracted_images = []

            metadata = self.get_file_metadata(file_path)

            with pdfplumber.open(file_path) as pdf:
                pdf_metadata = pdf.metadata or {}

                metadata.title = pdf_metadata.get("Title")
                metadata.author = pdf_metadata.get("Author")
                metadata.subject = pdf_metadata.get("Subject")
                metadata.pages = len(pdf.pages)

                creator = pdf_metadata.get("Creator")
                producer = pdf_metadata.get("Producer")
                created = pdf_metadata.get("CreationDate")
                modified = pdf_metadata.get("ModDate")

                metadata.document_properties = {
                    "creator": creator,
                    "producer": producer,
                    "creation_date_pdf": str(created) if created else None,
                    "modification_date_pdf": str(modified) if modified else None,
                    "encrypted": pdf.metadata.get("Encrypted", False) if pdf.metadata else False,
                    "pdf_version": getattr(pdf, "pdf_version", None),
                }

                if pdf_metadata.get("Keywords"):
                    metadata.keywords = [
                        k.strip() for k in pdf_metadata.get("Keywords", "").split(",")
                    ]

                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text() or ""

                    tables = page.extract_tables()
                    if tables:
                        page_text += "\n\n"
                        for table in tables:
                            if table:
                                table_text = "\n".join(
                                    [
                                        " | ".join([str(cell) if cell else "" for cell in row])
                                        for row in table
                                    ]
                                )
                                page_text += f"\nTable on page {page_num}:\n{table_text}\n"

                    text_content.append(f"--- Page {page_num} ---\n{page_text}\n")

            doc = fitz.open(file_path)
            for page_num in range(doc.page_count):
                page = doc[page_num]
                image_list = page.get_images()

                for img_index, img in enumerate(image_list):
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)

                        if pix.n - pix.alpha < 4:
                            image_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                            image_path = images_dir / image_filename
                            pix.save(str(image_path))
                            extracted_images.append(str(image_path))

                        pix = None
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract image {img_index} from page {page_num}: {e}"
                        )
                        continue

            doc.close()

            full_text = "\n".join(text_content)

            content_file = output_dir / "content.txt"
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(full_text)

            self.save_metadata(metadata, output_dir)

            return ExtractionResult(
                text=full_text, images=extracted_images, metadata=metadata.to_dict(), success=True
            )

        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            return ExtractionResult(text="", images=[], metadata={}, success=False, error=str(e))
