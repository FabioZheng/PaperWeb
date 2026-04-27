"""PDF/text parsing pipeline with chunking and table hooks."""

from __future__ import annotations

from pathlib import Path

from app.models import PaperMetadata, ParsedChunk


class PDFParser:
    """MVP parser uses plain text fixtures; production can swap extractor."""

    def parse(self, paper: PaperMetadata) -> list[ParsedChunk]:
        text = Path(paper.pdf_path).read_text()
        sections = [s.strip() for s in text.split("\n# ") if s.strip()]
        chunks: list[ParsedChunk] = []
        for idx, sec in enumerate(sections):
            lines = sec.splitlines()
            section_name = lines[0].replace("#", "").strip()
            body = "\n".join(lines[1:]).strip()
            chunk_type = "table" if "|" in body else "text"
            chunks.append(
                ParsedChunk(
                    chunk_id=f"{paper.paper_id}_c{idx}",
                    paper_id=paper.paper_id,
                    section=section_name or f"section_{idx}",
                    chunk_type=chunk_type,
                    text=body,
                    page_start=idx + 1,
                    page_end=idx + 1,
                )
            )
        return chunks
