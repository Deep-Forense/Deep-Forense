"""Adaptador de entrada: analysis_controller (REST).

Traduce HTTP <-> Command/DTO de aplicación. No contiene reglas de negocio:
solo valida forma de entrada y delega en los casos de uso inyectados.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.application.dto.submit_analysis_command import SubmitAnalysisCommand
from app.application.dto.submit_url_analysis_command import SubmitUrlAnalysisCommand
from app.application.ports.get_job_input_port import GetJobInputPort
from app.application.ports.submit_analysis_input_port import SubmitAnalysisInputPort
from app.application.ports.submit_url_analysis_input_port import SubmitUrlAnalysisInputPort
from app.domain.exceptions import UnsupportedUrlContentError, UrlDownloadError
from app.infrastructure.adapter.input.rest.security import optional_user_id, require_user_id

router = APIRouter(prefix="/api/forensic")


def _resolve_artifact_type(file: Optional[UploadFile]) -> str:
    """Heurística mínima de Sprint 1: por content-type. Se refina en Sprint 2/3
    (OCR + clasificación real de documento vs imagen)."""
    if file is not None and file.content_type and file.content_type.startswith("image/"):
        return "IMAGE"
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
        # FOR-97 (HU3.2): URL directa a imagen/PDF -> 1 artifact.
        # FOR-98 (HU3.3): página HTML -> scraping (1 TEXT + hasta N IMAGE).
        try:
            job = await url_use_case.execute(SubmitUrlAnalysisCommand(user_id=user_id, url=url))
        except (UnsupportedUrlContentError, UrlDownloadError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"job_id": job.job_id, "status": "PENDING", "artifacts_count": len(job.artifacts)}

    content = await file.read()
    command = SubmitAnalysisCommand(
        user_id=user_id,
        file_bytes=content,
        file_name=file.filename,
        artifact_type=_resolve_artifact_type(file),
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


def _artifact_view(artifact, full: bool) -> dict:
    view = {"artifact_id": artifact.artifact_id, "type": str(artifact.type), "status": artifact.status}
    if full:
        view["origin"] = artifact.origin
        view["analysis"] = artifact.analysis
    return view


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
        "artifacts": [_artifact_view(a, full) for a in job.artifacts],
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }
