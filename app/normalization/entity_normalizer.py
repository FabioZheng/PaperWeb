"""Entity normalization helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Entity


@dataclass
class EntityNormalizer:
    alias_map: dict[str, str] = field(
        default_factory=lambda: {
            "kilt benchmark": "KILT",
            "kilt": "KILT",
            "sparsebase": "SparseBase",
        }
    )

    def normalize_name(self, text: str) -> str:
        key = text.strip().lower()
        return self.alias_map.get(key, text.strip())

    def normalize_entity(self, entity: Entity) -> Entity:
        canonical = self.normalize_name(entity.canonical_name)
        aliases = sorted({a.strip() for a in entity.aliases if a.strip()})
        return Entity(
            entity_id=entity.entity_id,
            canonical_name=canonical,
            aliases=aliases,
            entity_type=entity.entity_type,
        )
