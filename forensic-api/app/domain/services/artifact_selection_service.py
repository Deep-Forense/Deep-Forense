"""Servicio de DOMINIO: ArtifactSelectionService (FOR-99 / HU3.4).

Filtro de relevancia sobre las imágenes candidatas del scraping (FOR-98).
Lógica pura sobre ImageCandidate ya medidos — no conoce Scrapfly, Pillow ni
HTTP (por eso NO vive en el adaptador de Scrapfly).

Reglas:
  1. Descarta imágenes pequeñas (< min_width x min_height, default 200x200:
     iconos, spacers, botones).
  2. Prioriza contenido principal: main > unknown > header/footer/sidebar/nav.
     Dentro de la misma prioridad conserva el orden de aparición en el DOM.
  3. Deduplica por hash perceptual (distancia de Hamming <= umbral: misma
     imagen en distintas resoluciones/recortes leves).
  4. Limita a max_candidates (default 5, cableado a MAX_IMAGES_PER_JOB).
"""

DEFAULT_MAX_CANDIDATES = 5
DEFAULT_MIN_WIDTH = 200
DEFAULT_MIN_HEIGHT = 200
# Bits distintos (de 64) por debajo de los cuales dos aHash se consideran
# la misma imagen. 8/64 tolera recompresión y resize sin unir imágenes distintas.
DEFAULT_HAMMING_THRESHOLD = 8

_SECTION_PRIORITY = {
    "main": 0,
    "unknown": 1,
    "header": 2,
    "footer": 2,
    "sidebar": 2,
    "nav": 2,
}


def _hamming_distance(hash_a: int, hash_b: int) -> int:
    return bin(hash_a ^ hash_b).count("1")


class ArtifactSelectionService:
    def __init__(
        self,
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
        min_width: int = DEFAULT_MIN_WIDTH,
        min_height: int = DEFAULT_MIN_HEIGHT,
        hamming_threshold: int = DEFAULT_HAMMING_THRESHOLD,
    ) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates debe ser >= 1")
        self._max_candidates = max_candidates
        self._min_width = min_width
        self._min_height = min_height
        self._hamming_threshold = hamming_threshold

    def select(self, candidates: list) -> list:
        """Devuelve las candidatas relevantes (list[ImageCandidate]), en orden
        de prioridad, ya deduplicadas y limitadas a max_candidates."""
        relevant = [
            c for c in candidates if c.width >= self._min_width and c.height >= self._min_height
        ]
        # sort estable: dentro de la misma sección se respeta el orden del DOM.
        relevant.sort(key=lambda c: _SECTION_PRIORITY.get(c.section, 1))

        selected = []
        for candidate in relevant:
            if any(
                _hamming_distance(candidate.perceptual_hash, kept.perceptual_hash)
                <= self._hamming_threshold
                for kept in selected
            ):
                continue
            selected.append(candidate)
            if len(selected) >= self._max_candidates:
                break
        return selected
