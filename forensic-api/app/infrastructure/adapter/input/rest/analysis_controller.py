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
        # FOR-97 (HU3.2): URL directa a imagen/PDF. El caso HTML (scraping
        # vía Scrapfly + ArtifactSelectionService) es Sprint 3 (FOR-98/T3.M1).
        try:
            job_id = await url_use_case.execute(SubmitUrlAnalysisCommand(user_id=user_id, url=url))
        except (UnsupportedUrlContentError, UrlDownloadError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"job_id": job_id, "status": "PENDING", "artifacts_count": 1}

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
):
    """Igual que /demo/analyze pero requiere JWT (T1.P3 valida el token en Kong/
    middleware; aquí se asumiría el user_id ya resuelto del token)."""
    # TODO Sprint 1: extraer user_id del JWT validado
    return await _submit(None, file, url, use_case, url_use_case)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, use_case: GetJobInputPort = Depends()):
    job = await use_case.execute(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado.")

    detail_level = "basic"  # TODO Sprint 1: "full" si el JWT corresponde al dueño del job
    artifacts = [
        {"artifact_id": a.artifact_id, "type": str(a.type), "status": a.status} for a in job.artifacts
    ]
    return {
        "job_id": job.job_id,
        "status": job.status,
        "detail_level": detail_level,
        "consolidated": job.consolidated,
        "artifacts": artifacts,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }
