"""Adaptador de entrada: analysis_controller (REST).

Traduce HTTP <-> Command/DTO de aplicación. No contiene reglas de negocio:
solo valida forma de entrada y delega en los casos de uso inyectados.
"""
from typing import Optional

import fitz
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile

from app.application.dto.submit_analysis_command import SubmitAnalysisCommand
from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.ports.get_artifact_heatmap_input_port import GetArtifactHeatmapInputPort
from app.application.ports.get_job_input_port import GetJobInputPort
from app.application.ports.list_jobs_input_port import ListJobsInputPort
from app.application.ports.submit_analysis_input_port import SubmitAnalysisInputPort
from app.application.ports.submit_url_analysis_input_port import SubmitUrlAnalysisInputPort
from app.domain.exceptions import UnsupportedUrlContentError, UrlDownloadError
from app.infrastructure.adapter.input.rest.security import optional_user_id, require_user_id

router = APIRouter(prefix="/api/forensic")


_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
_IMAGE_MAGICS = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"RIFF")


def _resolve_and_validate_artifact(content: bytes) -> str:
    """Valida los bytes reales; el nombre y MIME enviados por el cliente no son confiables."""
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el límite de 50 MB.")
    if any(content.startswith(magic) for magic in _IMAGE_MAGICS):
        if content.startswith(b"RIFF") and (len(content) < 12 or content[8:12] != b"WEBP"):
            raise HTTPException(status_code=400, detail="El archivo no es una imagen compatible.")
        return "IMAGE"
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400,
            detail="Formato no compatible. Solo se admiten PDF, JPEG, PNG o WEBP.",
        )
    try:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise HTTPException(
                    status_code=400,
                    detail="El PDF está protegido con contraseña y no puede analizarse.",
                )
            if pdf.page_count < 1:
                raise HTTPException(status_code=400, detail="El PDF no contiene páginas.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="El archivo no es un PDF válido o está dañado.") from exc
    return "TEXT"


async def _submit(
    user_id: Optional[str],
    file: Optional[UploadFile],
    url: Optional[str],
    file_use_case: SubmitAnalysisInputPort,
    url_use_case: SubmitUrlAnalysisInputPort,
) -> dict:
    if (file is None) == (url is None):
        raise HTTPException(
            status_code=400,
            detail="Debe proveerse 'file' o 'url', no ambos ni ninguno.",
        )

    if url is not None:
        # Únicamente una URL directa a imagen JPEG, PNG o WEBP.
        try:
            job = await url_use_case.execute(SubmitUrlAnalysisCommand(user_id=user_id, url=url))
        except (UnsupportedUrlContentError, UrlDownloadError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"job_id": job.job_id, "status": "PENDING", "artifacts_count": len(job.artifacts)}

    content = await file.read()
    artifact_type = _resolve_and_validate_artifact(content)
    command = SubmitAnalysisCommand(
        user_id=user_id,
        file_bytes=content,
        file_name=file.filename,
        artifact_type=artifact_type,
    )
    job_id = await file_use_case.execute(command)
    return {"job_id": job_id, "status": "PENDING", "artifacts_count": 1}


@router.post("/demo/analyze", status_code=202)
async def demo_analyze(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    use_case: SubmitAnalysisInputPort = Depends(),
    url_use_case: SubmitUrlAnalysisInputPort = Depends(),
):
    return await _submit(None, file, url, use_case, url_use_case)


@router.post("/analyze", status_code=202)
async def analyze(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    use_case: SubmitAnalysisInputPort = Depends(),
    url_use_case: SubmitUrlAnalysisInputPort = Depends(),
    user_id: str = Depends(require_user_id),
):
    """Igual que /demo/analyze pero requiere JWT: el job queda asociado al
    userId del token (emitido por auth-service), lo que habilita
    detail_level=full en GET /jobs/{job_id}."""
    return await _submit(user_id, file, url, use_case, url_use_case)


def _consolidated_view(consolidated: Optional[dict], full: bool) -> Optional[dict]:
    if consolidated is None or full:
        return consolidated
    # dominant_artifact y policy_applied solo se exponen en detail_level=full
    # (contrato JobResult de docs/openapi.yaml).
    return {k: v for k, v in consolidated.items() if k not in ("dominant_artifact", "policy_applied")}


def _artifact_view(artifact, full: bool, job_id: str) -> dict:
    view = {"artifact_id": artifact.artifact_id, "type": str(artifact.type), "status": artifact.status}
    if full:
        view["origin"] = artifact.origin
        analysis = dict(artifact.analysis) if artifact.analysis else artifact.analysis
        if analysis and analysis.get("ela_heatmap_ref"):
            analysis["ela_heatmap_url"] = (
                f"/api/forensic/jobs/{job_id}/artifacts/{artifact.artifact_id}/ela-heatmap"
            )
        if analysis and analysis.get("document_visual_heatmap_ref"):
            analysis["document_visual_heatmap_url"] = (
                f"/api/forensic/jobs/{job_id}/artifacts/{artifact.artifact_id}/ela-heatmap"
            )
        view["analysis"] = analysis
    return view


def _job_summary(job) -> dict:
    """Vista resumida; DIRECT_URL identifica imágenes obtenidas por enlace."""
    consolidated = job.consolidated or {}
    from_url = any(a.origin == "DIRECT_URL" or a.origin.startswith("SCRAPED") for a in job.artifacts)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "verdict": consolidated.get("verdict"),
        "fraud_score": consolidated.get("fraud_score"),
        "input_source": "URL" if from_url else "UPLOAD",
        "created_at": job.created_at,
    }


@router.get("/jobs")
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    verdict: Optional[str] = Query(default=None, pattern="^(APPROVED|SUSPICIOUS|REJECTED|INCONCLUSIVE)$"),
    use_case: ListJobsInputPort = Depends(),
    user_id: str = Depends(require_user_id),
):
    """FOR-100/RF-29: historial paginado del usuario autenticado (JWT
    obligatorio; jamás lista jobs de otros usuarios ni jobs demo)."""
    jobs_page = await use_case.execute(
        user_id=user_id, page=page, page_size=page_size, verdict=verdict
    )
    return {
        "page": jobs_page.page,
        "page_size": jobs_page.page_size,
        "total": jobs_page.total,
        "items": [_job_summary(job) for job in jobs_page.items],
    }


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    use_case: GetJobInputPort = Depends(),
    user_id: Optional[str] = Depends(optional_user_id),
):
    job = await use_case.execute(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado.")

    # full solo si el JWT corresponde al dueño del job (jobs de demo no tienen dueño).
    full = user_id is not None and job.user_id == user_id
    detail_level = "full" if full else "basic"
    return {
        "job_id": job.job_id,
        "status": job.status,
        "detail_level": detail_level,
        "consolidated": _consolidated_view(job.consolidated, full),
        "artifacts": [_artifact_view(a, full, job.job_id) for a in job.artifacts],
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }


@router.get("/jobs/{job_id}/artifacts/{artifact_id}/ela-heatmap")
async def get_artifact_ela_heatmap(
    job_id: str,
    artifact_id: str,
    use_case: GetArtifactHeatmapInputPort = Depends(),
    user_id: Optional[str] = Depends(optional_user_id),
):
    """Imagen PNG del heatmap ELA (T2.M2). Mismo control de acceso que
    detail_level=full: solo el dueño del job puede verla."""
    heatmap_png = await use_case.execute(job_id, artifact_id, user_id)
    if heatmap_png is None:
        raise HTTPException(status_code=404, detail="Heatmap no encontrado.")
    return Response(content=heatmap_png, media_type="image/png")
