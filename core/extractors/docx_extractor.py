import io
import logging
from pathlib import Path

from docx import Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class DOCXExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.supported_extensions = [".docx", ".doc"]
        self.supported_mime_types = [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]

    def extract(self, file_path: Path, output_dir: Path) -> ExtractionResult:
        try:
            images_dir = output_dir / "images"
            images_dir.mkdir(exist_ok=True)

            doc = Document(file_path)
            extracted_images = []
            text_content = []

            metadata = self.get_file_metadata(file_path)

            core_props = doc.core_properties
            metadata.title = core_props.title
            metadata.author = core_props.author
            metadata.subject = core_props.subject

            if core_props.keywords:
                metadata.keywords = [k.strip() for k in core_props.keywords.split(",")]

            metadata.document_properties = {
                "category": core_props.category,
                "comments": core_props.comments,
                "content_status": core_props.content_status,
                "created": core_props.created.isoformat() if core_props.created else None,
                "identifier": core_props.identifier,
                "language": core_props.language,
                "last_modified_by": core_props.last_modified_by,
                "modified": core_props.modified.isoformat() if core_props.modified else None,
                "revision": core_props.revision,
                "version": core_props.version,
                "word_count": len(doc.paragraphs),
            }

            img_counter = 1

            for element in doc.element.body:
                if isinstance(element, CT_P):
                    paragraph = Paragraph(element, doc)
                    para_text = paragraph.text.strip()
                    if para_text:
                        text_content.append(para_text)

                    for run in paragraph.runs:
                        if hasattr(run.element, "xpath"):
                            try:
                                # Try with namespaces parameter (older python-docx versions)
                                images = run.element.xpath(
                                    ".//a:blip/@r:embed",
                                    namespaces={
                                        "a": (
                                            "http://schemas.openxmlformats.org/drawingml/2006/main"
                                        ),
                                        "r": (
                                            "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                                        ),
                                    },
                                )
                            except TypeError:
                                # Fallback for newer python-docx versions without namespaces parameter
                                try:
                                    images = run.element.xpath(".//a:blip/@r:embed")
                                except Exception:
                                    # If xpath fails completely, skip image extraction for this run
                                    images = []
                            for image_id in images:
                                try:
                                    image_part = doc.part.related_parts[image_id]
                                    image_filename = f"docx_img_{img_counter}.png"
                                    image_path = images_dir / image_filename

                                    image = Image.open(io.BytesIO(image_part.blob))
                                    image.save(image_path, "PNG")

                                    extracted_images.append(str(image_path))
                                    img_counter += 1
                                except Exception as e:
                                    logger.warning(f"Failed to extract image {image_id}: {e}")
                                    continue

                elif isinstance(element, CT_Tbl):
                    table = Table(element, doc)
                    table_text = []
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            cell_text = cell.text.strip().replace("\n", " ")
                            row_text.append(cell_text)
                        table_text.append(" | ".join(row_text))

                    if table_text:
                        text_content.append("Table:")
                        text_content.extend(table_text)
                        text_content.append("")

            full_text = "\n".join(text_content)

            content_file = output_dir / "content.txt"
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(full_text)

            self.save_metadata(metadata, output_dir)

            return ExtractionResult(
                text=full_text, images=extracted_images, metadata=metadata.to_dict(), success=True
            )

        except Exception as e:
            logger.error(f"DOCX extraction failed for {file_path}: {e}")
            return ExtractionResult(text="", images=[], metadata={}, success=False, error=str(e))
