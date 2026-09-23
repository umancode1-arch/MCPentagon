from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.orchestrator import apply_edit_flow, finalize_document, generate_document_flow

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "app" / "templates"
GENERATED_DIR = BASE_DIR / "generated"

app = FastAPI(title="MCP SmartComms Document Automation Demo")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


class GenerateRequest(BaseModel):
    template_name: str
    client_id: str


class ApplyEditRequest(BaseModel):
    docx_path: str
    instruction: str


class FinalizeRequest(BaseModel):
    docx_path: str


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {})


@app.post("/generate-document")
async def generate_document_endpoint(payload: GenerateRequest):
    result = await generate_document_flow(payload.template_name, payload.client_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Could not generate document."))
    return JSONResponse(result)


@app.post("/apply-edit")
async def apply_edit_endpoint(payload: ApplyEditRequest):
    result = await apply_edit_flow(payload.docx_path, payload.instruction)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Could not apply the requested edit."))
    return JSONResponse(result)


@app.post("/finalize")
async def finalize_endpoint(payload: FinalizeRequest):
    result = await finalize_document(payload.docx_path)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Could not finalize the document."))
    return JSONResponse(result)


@app.get("/download")
async def download_document(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path, filename=file_path.name)
