import logging
import re
from pathlib import Path
from typing import Any

import markdown2
import yaml
from bs4 import BeautifulSoup

from .base import BaseExtractor, ExtractionResult

logger = logging.getLogger(__name__)


class MarkdownExtractor(BaseExtractor):
    def __init__(self):
        super().__init__()
        self.supported_extensions = [".md", ".markdown", ".mdown", ".mkd"]
        self.supported_mime_types = ["text/markdown", "text/x-markdown"]

    def extract_front_matter(self, content: str) -> tuple[dict[str, Any], str]:
        front_matter = {}
        body = content

        if content.startswith("---\n"):
            try:
                end_index = content.find("\n---\n", 4)
                if end_index != -1:
                    yaml_content = content[4:end_index]
                    front_matter = yaml.safe_load(yaml_content) or {}
                    body = content[end_index + 5 :]
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML front matter: {e}")

        elif content.startswith("+++\n"):
            try:
                end_index = content.find("\n+++\n", 4)
                if end_index != -1:
                    toml_content = content[4:end_index]
                    try:
                        import tomli

                        front_matter = tomli.loads(toml_content) or {}
                    except ImportError:
                        logger.warning("TOML front matter found but tomli not installed")
                    body = content[end_index + 5 :]
            except Exception as e:
                logger.warning(f"Failed to parse TOML front matter: {e}")

        return front_matter, body

    def extract_headers(self, content: str) -> list[str]:
        headers = []
        for line in content.split("\n"):
            if line.strip().startswith("#"):
                match = re.match(r"^(#+)\s+(.+)", line.strip())
                if match:
                    level = len(match.group(1))
                    title = match.group(2)
                    headers.append(f"{'  ' * (level - 1)}{title}")
        return headers

    def extract(self, file_path: Path, output_dir: Path) -> ExtractionResult:
        try:
            with open(file_path, encoding="utf-8") as f:
                raw_content = f.read()

            metadata = self.get_file_metadata(file_path)

            front_matter, markdown_content = self.extract_front_matter(raw_content)

            if front_matter:
                metadata.title = front_matter.get("title")
                metadata.author = front_matter.get("author")
                metadata.subject = front_matter.get("subject") or front_matter.get("description")

                keywords = front_matter.get("keywords") or front_matter.get("tags")
                if keywords:
                    if isinstance(keywords, list):
                        metadata.keywords = keywords
                    elif isinstance(keywords, str):
                        metadata.keywords = [k.strip() for k in keywords.split(",")]

                metadata.document_properties = {
                    "front_matter": front_matter,
                    "has_front_matter": True,
                }
            else:
                metadata.document_properties = {"has_front_matter": False}

            headers = self.extract_headers(markdown_content)
            if headers:
                metadata.document_properties["heading_structure"] = headers

            html = markdown2.markdown(
                markdown_content, extras=["fenced-code-blocks", "tables", "metadata", "footnotes"]
            )

            soup = BeautifulSoup(html, "html.parser")
            plain_text = soup.get_text(separator="\n", strip=True)

            text_lines = []
            text_lines.append("=== Markdown Document ===\n")

            if front_matter:
                text_lines.append("Front Matter:")
                for key, value in front_matter.items():
                    text_lines.append(f"{key}: {value}")
                text_lines.append("")

            if headers:
                text_lines.append("Document Structure:")
                text_lines.extend(headers)
                text_lines.append("")

            text_lines.append("Content:")
            text_lines.append(plain_text)

            full_text = "\n".join(text_lines)

            content_file = output_dir / "content.txt"
            with open(content_file, "w", encoding="utf-8") as f:
                f.write(full_text)

            self.save_metadata(metadata, output_dir)

            return ExtractionResult(
                text=full_text,
                images=[],  # Markdown images are typically references, not embedded
                metadata=metadata.to_dict(),
                success=True,
            )

        except Exception as e:
            logger.error(f"Markdown extraction failed for {file_path}: {e}")
            return ExtractionResult(text="", images=[], metadata={}, success=False, error=str(e))
