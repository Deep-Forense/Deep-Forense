// Mock temporal mientras el backend no expone "ela_heatmap_url" en ArtifactAnalysis
// (ver docs/openapi.yaml — GET /jobs/{job_id} aún no incluye ese campo).
// Misma forma que tendrá el dato real (una URL de imagen) para que, cuando el
// backend lo agregue, solo cambie la fuente de datos en AdvancedScanResult.jsx.

const MOCK_HEATMAP_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360">
  <defs>
    <radialGradient id="hot" cx="35%" cy="42%" r="55%">
      <stop offset="0%" stop-color="#ff3b30" stop-opacity="0.9"/>
      <stop offset="45%" stop-color="#ff9500" stop-opacity="0.5"/>
      <stop offset="100%" stop-color="#0b1f33" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="warm" cx="72%" cy="66%" r="40%">
      <stop offset="0%" stop-color="#ffd60a" stop-opacity="0.65"/>
      <stop offset="100%" stop-color="#0b1f33" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="640" height="360" fill="#0b1f33"/>
  <rect width="640" height="360" fill="url(#hot)"/>
  <rect width="640" height="360" fill="url(#warm)"/>
</svg>`.trim();

export const MOCK_ELA_HEATMAP_URL = `data:image/svg+xml;utf8,${encodeURIComponent(MOCK_HEATMAP_SVG)}`;
