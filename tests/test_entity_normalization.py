from app.models import Entity
from app.normalization.entity_normalizer import EntityNormalizer


def test_entity_normalization_aliases() -> None:
    norm = EntityNormalizer()
    e = Entity(entity_id="e1", canonical_name="kilt benchmark", aliases=[" KILT ", ""], entity_type="Dataset")
    out = norm.normalize_entity(e)
    assert out.canonical_name == "KILT"
    assert out.aliases == ["KILT"]
