import tempfile
from pathlib import Path

from core.extractors import (
    DOCXExtractor,
    MarkdownExtractor,
    PDFExtractor,
    XLSXExtractor,
    extractor_factory,
)


class TestExtractorFactory:
    def test_get_supported_extensions(self):
        extensions = extractor_factory.get_supported_extensions()
        expected_extensions = [
            ".pdf",
            ".docx",
            ".doc",
            ".xlsx",
            ".xls",
            ".md",
            ".markdown",
            ".mdown",
            ".mkd",
        ]

        for ext in expected_extensions:
            assert ext in extensions

    def test_create_extractor_pdf(self):
        pdf_file = Path("test.pdf")
        extractor = extractor_factory.create_extractor(pdf_file)
        assert isinstance(extractor, PDFExtractor)

    def test_create_extractor_docx(self):
        docx_file = Path("test.docx")
        extractor = extractor_factory.create_extractor(docx_file)
        assert isinstance(extractor, DOCXExtractor)

    def test_create_extractor_xlsx(self):
        xlsx_file = Path("test.xlsx")
        extractor = extractor_factory.create_extractor(xlsx_file)
        assert isinstance(extractor, XLSXExtractor)

    def test_create_extractor_markdown(self):
        md_file = Path("test.md")
        extractor = extractor_factory.create_extractor(md_file)
        assert isinstance(extractor, MarkdownExtractor)

    def test_create_extractor_unsupported(self):
        unsupported_file = Path("test.txt")
        extractor = extractor_factory.create_extractor(unsupported_file)
        assert extractor is None


class TestMarkdownExtractor:
    def test_can_extract_md_files(self):
        extractor = MarkdownExtractor()

        assert extractor.can_extract(Path("test.md"))
        assert extractor.can_extract(Path("test.markdown"))
        assert extractor.can_extract(Path("test.mdown"))
        assert extractor.can_extract(Path("test.mkd"))
        assert not extractor.can_extract(Path("test.txt"))

    def test_extract_sample_markdown(self):
        extractor = MarkdownExtractor()

        # Use the sample markdown file
        sample_file = Path("tests/test_files/sample.md")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)

            result = extractor.extract(sample_file, output_dir)

            assert result.success
            assert result.error is None
            assert len(result.text) > 0
            assert "Sample Markdown Document" in result.text
            assert "Test Author" in result.text

            # Check metadata
            assert result.metadata["title"] == "Sample Markdown Document"
            assert result.metadata["author"] == "Test Author"
            assert "test" in result.metadata["keywords"]

            # Check files were created
            assert (output_dir / "content.txt").exists()
            assert (output_dir / "meta.txt").exists()

            # Verify meta.txt content
            meta_content = (output_dir / "meta.txt").read_text()
            assert "Sample Markdown Document" in meta_content
            assert "Test Author" in meta_content

    def test_extract_front_matter(self):
        extractor = MarkdownExtractor()

        yaml_content = """---
title: Test Document
author: John Doe
tags: [test, demo]
---

# Content

This is the body."""

        front_matter, body = extractor.extract_front_matter(yaml_content)

        assert front_matter["title"] == "Test Document"
        assert front_matter["author"] == "John Doe"
        assert front_matter["tags"] == ["test", "demo"]
        assert "# Content" in body

    def test_extract_headers(self):
        extractor = MarkdownExtractor()

        content = """# Main Title
## Subtitle
### Sub-subtitle
Regular text
## Another Subtitle"""

        headers = extractor.extract_headers(content)

        assert len(headers) == 4
        assert "Main Title" in headers[0]
        assert "  Subtitle" in headers[1]
        assert "    Sub-subtitle" in headers[2]
        assert "  Another Subtitle" in headers[3]


class TestPDFExtractor:
    def test_can_extract_pdf_files(self):
        extractor = PDFExtractor()

        assert extractor.can_extract(Path("test.pdf"))
        assert not extractor.can_extract(Path("test.doc"))

    def test_supported_extensions(self):
        extractor = PDFExtractor()
        assert ".pdf" in extractor.supported_extensions


class TestDOCXExtractor:
    def test_can_extract_docx_files(self):
        extractor = DOCXExtractor()

        assert extractor.can_extract(Path("test.docx"))
        assert extractor.can_extract(Path("test.doc"))
        assert not extractor.can_extract(Path("test.pdf"))

    def test_supported_extensions(self):
        extractor = DOCXExtractor()
        assert ".docx" in extractor.supported_extensions
        assert ".doc" in extractor.supported_extensions


class TestXLSXExtractor:
    def test_can_extract_xlsx_files(self):
        extractor = XLSXExtractor()

        assert extractor.can_extract(Path("test.xlsx"))
        assert extractor.can_extract(Path("test.xls"))
        assert not extractor.can_extract(Path("test.pdf"))

    def test_supported_extensions(self):
        extractor = XLSXExtractor()
        assert ".xlsx" in extractor.supported_extensions
        assert ".xls" in extractor.supported_extensions
