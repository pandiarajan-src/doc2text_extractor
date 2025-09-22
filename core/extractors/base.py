import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ExtractionResult:
    text: str
    images: list[str]  # List of image file paths
    metadata: dict[str, Any]
    success: bool
    error: str | None = None


@dataclass
class DocumentMetadata:
    filename: str
    file_size: int
    file_type: str
    mime_type: str
    creation_date: datetime | None
    modification_date: datetime | None
    author: str | None = None
    title: str | None = None
    subject: str | None = None
    keywords: list[str] | None = None
    pages: int | None = None
    document_properties: dict[str, Any] = None
    extraction_timestamp: datetime = None
    extraction_method: str = None

    def __post_init__(self):
        if self.extraction_timestamp is None:
            self.extraction_timestamp = datetime.now()
        if self.document_properties is None:
            self.document_properties = {}
        if self.keywords is None:
            self.keywords = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "mime_type": self.mime_type,
            "creation_date": self.creation_date.isoformat() if self.creation_date else None,
            "modification_date": (
                self.modification_date.isoformat() if self.modification_date else None
            ),
            "author": self.author,
            "title": self.title,
            "subject": self.subject,
            "keywords": self.keywords,
            "pages": self.pages,
            "document_properties": self.document_properties,
            "extraction_timestamp": self.extraction_timestamp.isoformat(),
            "extraction_method": self.extraction_method,
        }

    def to_text(self) -> str:
        lines = [
            "Document Metadata",
            "================",
            "",
            f"Filename: {self.filename}",
            f"File Size: {self.file_size:,} bytes",
            f"File Type: {self.file_type}",
            f"MIME Type: {self.mime_type}",
            f"Creation Date: {self.creation_date.isoformat() if self.creation_date else 'N/A'}",
            f"Modification Date: {self.modification_date.isoformat() if self.modification_date else 'N/A'}",
            f"Author: {self.author or 'N/A'}",
            f"Title: {self.title or 'N/A'}",
            f"Subject: {self.subject or 'N/A'}",
            f"Keywords: {', '.join(self.keywords) if self.keywords else 'N/A'}",
            f"Pages: {self.pages if self.pages else 'N/A'}",
            f"Extraction Timestamp: {self.extraction_timestamp.isoformat()}",
            f"Extraction Method: {self.extraction_method}",
            "",
        ]

        if self.document_properties:
            lines.append("Document Properties:")
            lines.append("-------------------")
            for key, value in self.document_properties.items():
                lines.append(f"{key}: {value}")
            lines.append("")

        return "\n".join(lines)


class BaseExtractor(ABC):
    def __init__(self):
        self.supported_extensions: list[str] = []
        self.supported_mime_types: list[str] = []

    def get_file_metadata(self, file_path: Path) -> DocumentMetadata:
        stat_info = file_path.stat()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return DocumentMetadata(
            filename=file_path.name,
            file_size=stat_info.st_size,
            file_type=file_path.suffix.lower(),
            mime_type=mime_type or "application/octet-stream",
            creation_date=datetime.fromtimestamp(stat_info.st_ctime),
            modification_date=datetime.fromtimestamp(stat_info.st_mtime),
            extraction_method=self.__class__.__name__,
        )

    def can_extract(self, file_path: Path) -> bool:
        extension = file_path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(file_path))

        return extension in self.supported_extensions or mime_type in self.supported_mime_types

    @abstractmethod
    def extract(self, file_path: Path, output_dir: Path) -> ExtractionResult:
        pass

    def save_metadata(self, metadata: DocumentMetadata, output_dir: Path) -> None:
        meta_file = output_dir / "meta.txt"
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(metadata.to_text())


class ExtractorFactory:
    def __init__(self):
        self._extractors = {}

    def register(self, name: str, extractor_class):
        self._extractors[name] = extractor_class

    def create_extractor(self, file_path: Path) -> BaseExtractor | None:
        for _name, extractor_class in self._extractors.items():
            extractor = extractor_class()
            if extractor.can_extract(file_path):
                return extractor
        return None

    def get_supported_extensions(self) -> list[str]:
        extensions = set()
        for extractor_class in self._extractors.values():
            extractor = extractor_class()
            extensions.update(extractor.supported_extensions)
        return list(extensions)


extractor_factory = ExtractorFactory()
