"""Adaptador de entrada: analysis_controller (REST).

Traduce HTTP <-> Command/DTO de aplicación. No contiene reglas de negocio:
solo valida forma de entrada y delega en los casos de uso inyectados.
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.application.dto.submit_analysis_command import SubmitAnalysisCommand
from app.application.ports.get_job_input_port import GetJobInputPort
from app.application.ports.submit_analysis_input_port import SubmitAnalysisInputPort

router = APIRouter(prefix="/api/forensic")


def _resolve_artifact_type(file: Optional[UploadFile]) -> str:
    """Heurística mínima de Sprint 1: por content-type. Se refina en Sprint 2/3
    (OCR + clasificación real de documento vs imagen)."""
    if file is not None and file.content_type and file.content_type.startswith("image/"):
        return "IMAGE"
    return "TEXT"


@router.post("/demo/analyze", status_code=202)
async def demo_analyze(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    use_case: SubmitAnalysisInputPort = Depends(),
):
    if (file is None) == (url is None):
        raise HTTPException(
            status_code=400,
            detail="Debe proveerse 'file' o 'url', no ambos ni ninguno.",
        )

    if url is not None:
        # T3.M1/T3.M3 (Sprint 3): scraping vía Scrapfly + ArtifactSelectionService.
        # Sprint 1 no implementa scraping todavía.
        raise HTTPException(status_code=400, detail="Análisis por URL disponible a partir de Sprint 3.")

    content = await file.read()
    command = SubmitAnalysisCommand(
        user_id=None,
        file_bytes=content,
        file_name=file.filename,
        artifact_type=_resolve_artifact_type(file),
    )
    job_id = await use_case.execute(command)
    return {"job_id": job_id, "status": "PENDING", "artifacts_count": 1}


@router.post("/analyze", status_code=202)
async def analyze(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    use_case: SubmitAnalysisInputPort = Depends(),
):
    """Igual que /demo/analyze pero requiere JWT (T1.P3 valida el token en Kong/
    middleware; aquí se asumiría el user_id ya resuelto del token)."""
    if (file is None) == (url is None):
        raise HTTPException(status_code=400, detail="Debe proveerse 'file' o 'url', no ambos ni ninguno.")

    content = await file.read()
    command = SubmitAnalysisCommand(
        user_id=None,  # TODO Sprint 1: extraer del JWT validado
        file_bytes=content,
        file_name=file.filename,
        artifact_type=_resolve_artifact_type(file),
    )
    job_id = await use_case.execute(command)
    return {"job_id": job_id, "status": "PENDING", "artifacts_count": 1}


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
