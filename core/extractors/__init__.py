from .base import (
    BaseExtractor,
    DocumentMetadata,
    ExtractionResult,
    ExtractorFactory,
    extractor_factory,
)
from .docx_extractor import DOCXExtractor
from .markdown_extractor import MarkdownExtractor
from .pdf_extractor import PDFExtractor
from .xlsx_extractor import XLSXExtractor

extractor_factory.register("pdf", PDFExtractor)
extractor_factory.register("docx", DOCXExtractor)
extractor_factory.register("xlsx", XLSXExtractor)
extractor_factory.register("markdown", MarkdownExtractor)

__all__ = [
    "BaseExtractor",
    "ExtractorFactory",
    "ExtractionResult",
    "DocumentMetadata",
    "extractor_factory",
    "PDFExtractor",
    "DOCXExtractor",
    "XLSXExtractor",
    "MarkdownExtractor",
]
