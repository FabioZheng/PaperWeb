import pytest

from app.models import ExtractedMemory


def test_extracted_memory_requires_any_record() -> None:
    with pytest.raises(ValueError):
        ExtractedMemory(facts=[], claims=[], interpretations=[], results=[])
