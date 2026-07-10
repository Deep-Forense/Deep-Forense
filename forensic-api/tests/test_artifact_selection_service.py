"""Tests de FOR-99 (HU3.4) — ArtifactSelectionService (dominio puro, sin mocks)."""
from app.domain.services.artifact_selection_service import ArtifactSelectionService
from app.domain.value_objects.image_candidate import ImageCandidate


def _candidate(url, width=800, height=600, phash=0, section="unknown"):
    return ImageCandidate(url=url, width=width, height=height, perceptual_hash=phash, section=section)


def _distinct_hash(i: int) -> int:
    """Hashes con distancia de Hamming 20 entre sí (bloques de 10 bits sin
    solaparse), muy por encima del umbral de dedupe (8)."""
    return 0b1111111111 << (i * 10)


def test_discards_images_smaller_than_200x200():
    service = ArtifactSelectionService()
    candidates = [
        _candidate("icono", width=64, height=64, phash=_distinct_hash(0)),
        _candidate("banner-bajo", width=900, height=90, phash=_distinct_hash(1)),
        _candidate("foto", width=800, height=600, phash=_distinct_hash(2)),
    ]
    assert [c.url for c in service.select(candidates)] == ["foto"]


def test_deduplicates_by_perceptual_hash():
    service = ArtifactSelectionService()
    base_hash = 0b1111000011110000
    candidates = [
        _candidate("original", phash=base_hash),
        _candidate("misma-recomprimida", phash=base_hash ^ 0b11),  # 2 bits: duplicado
        _candidate("distinta", phash=base_hash ^ ((1 << 40) - 1)),  # 40 bits: otra imagen
    ]
    assert [c.url for c in service.select(candidates)] == ["original", "distinta"]


def test_prioritizes_main_content_over_header_footer_sidebar():
    service = ArtifactSelectionService(max_candidates=2)
    candidates = [
        _candidate("logo-header", section="header", phash=_distinct_hash(0)),
        _candidate("foto-articulo", section="main", phash=_distinct_hash(1)),
        _candidate("banner-footer", section="footer", phash=_distinct_hash(2)),
        _candidate("suelta", section="unknown", phash=_distinct_hash(3)),
    ]
    assert [c.url for c in service.select(candidates)] == ["foto-articulo", "suelta"]


def test_limits_to_max_candidates():
    service = ArtifactSelectionService(max_candidates=3)
    candidates = [_candidate(f"img-{i}", phash=_distinct_hash(i)) for i in range(7)]
    assert len(service.select(candidates)) == 3


def test_preserves_dom_order_within_same_priority():
    service = ArtifactSelectionService()
    candidates = [
        _candidate(f"main-{i}", section="main", phash=_distinct_hash(i)) for i in range(3)
    ]
    assert [c.url for c in service.select(candidates)] == ["main-0", "main-1", "main-2"]


def test_empty_input_returns_empty():
    assert ArtifactSelectionService().select([]) == []
