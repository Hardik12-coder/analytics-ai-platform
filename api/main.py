"""FastAPI backend for deterministic analysis.

This API intentionally does not call any LLM yet. It returns computed stats,
sales metrics, and chart JSON only.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from api.analysis_pipeline import run_deterministic_analysis_file

app = FastAPI(title="Analytics AI Platform API")
_RESULTS: dict[str, dict] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_upload(
    file: UploadFile = File(...),
    value_column: str = Form(...),
    date_column: str | None = Form(None),
    category_column: str | None = Form(None),
    profit_column: str | None = Form(None),
    units_column: str | None = Form(None),
    z_score_threshold: float = Form(3.0),
) -> dict:
    suffix = Path(file.filename or "upload.csv").suffix or ".csv"

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_path = Path(tmpdir) / f"upload{suffix}"
            upload_path.write_bytes(await file.read())
            result = run_deterministic_analysis_file(
                upload_path,
                value_column=value_column,
                date_column=_blank_to_none(date_column),
                category_column=_blank_to_none(category_column),
                profit_column=_blank_to_none(profit_column),
                units_column=_blank_to_none(units_column),
                z_score_threshold=z_score_threshold,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result_id = str(uuid4())
    result["result_id"] = result_id
    result["filename"] = file.filename
    _RESULTS[result_id] = result
    return result


@app.get("/results/{result_id}")
def get_result(result_id: str) -> dict:
    result = _RESULTS.get(result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found.")
    return result


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
