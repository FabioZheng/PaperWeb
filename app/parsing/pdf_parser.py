"""PDF parsing pipeline with section-aware chunking and basic table extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

from app.models import PaperMetadata, ParsedChunk

_SECTION_PATTERN = re.compile(r"^\s*(abstract|introduction|related work|method|approach|experiments?|results?|conclusion)\s*$", re.I)


@dataclass
class _Block:
    section: str
    text: str
    chunk_type: str
    page: int


class PDFParser:
    """Parses PDFs into text/table chunks with section + page provenance."""

    def parse(self, paper: PaperMetadata) -> list[ParsedChunk]:
        pdf_path = Path(paper.pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"Missing PDF for paper {paper.paper_id}: {paper.pdf_path}")

        if pdf_path.suffix.lower() == ".txt":
            text = pdf_path.read_text(errors="ignore")
            return [
                ParsedChunk(
                    chunk_id=f"{paper.paper_id}_c0",
                    paper_id=paper.paper_id,
                    section="full_text",
                    chunk_type="text",
                    text=text,
                    page_start=1,
                    page_end=1,
                )
            ]

        blocks = self._extract_blocks(pdf_path)
        chunks: list[ParsedChunk] = []
        for idx, block in enumerate(blocks):
            chunks.append(
                ParsedChunk(
                    chunk_id=f"{paper.paper_id}_c{idx}",
                    paper_id=paper.paper_id,
                    section=block.section,
                    chunk_type=block.chunk_type,
                    text=block.text,
                    page_start=block.page,
                    page_end=block.page,
                )
            )

        if not chunks:
            chunks.append(
                ParsedChunk(
                    chunk_id=f"{paper.paper_id}_c0",
                    paper_id=paper.paper_id,
                    section="full_text",
                    chunk_type="text",
                    text="",
                    page_start=1,
                    page_end=1,
                )
            )
        return chunks

    def _extract_blocks(self, pdf_path: Path) -> list[_Block]:
        blocks: list[_Block] = []
        active_section = "unknown"

        with pdfplumber.open(str(pdf_path)) as pdf:
            for pidx, page in enumerate(pdf.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                lines = [line.strip() for line in page_text.splitlines() if line.strip()]

                text_buffer: list[str] = []
                for line in lines:
                    if _SECTION_PATTERN.match(line):
                        if text_buffer:
                            blocks.append(_Block(section=active_section, text="\n".join(text_buffer), chunk_type="text", page=pidx))
                            text_buffer = []
                        active_section = line.lower()
                        continue
                    text_buffer.append(line)

                if text_buffer:
                    blocks.append(_Block(section=active_section, text="\n".join(text_buffer), chunk_type="text", page=pidx))

                for tidx, table in enumerate(page.extract_tables() or []):
                    rows = [" | ".join((cell or "").strip() for cell in row) for row in table if any((cell or "").strip() for cell in row)]
                    if rows:
                        blocks.append(
                            _Block(section=f"{active_section}_table_{tidx}", text="\n".join(rows), chunk_type="table", page=pidx)
                        )

        deduped: list[_Block] = []
        seen: set[tuple[str, str, int]] = set()
        for block in blocks:
            key = (block.section, block.text, block.page)
            if block.text and key not in seen:
                deduped.append(block)
                seen.add(key)
        return deduped
