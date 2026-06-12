from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.knowledge import DocumentIngestRequest
from app.core.rag.pipeline import RAGPipeline
from app.db.session import get_db
from app.db.dependencies import get_rag_pipeline

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.post("/ingest")
async def ingest_document(
    request: DocumentIngestRequest,
    rag: RAGPipeline = Depends(get_rag_pipeline),
) -> dict:
    point_ids = await rag.ingest_document(
        text=request.content,
        user_id=request.user_id,
        source=request.source,
        metadata=request.metadata,
    )
    return {"status": "ingested", "chunks": len(point_ids), "point_ids": point_ids}


@router.post("/upload")
async def upload_file(
    user_id: str = Form(...),
    file: UploadFile = File(...),
    rag: RAGPipeline = Depends(get_rag_pipeline),
) -> dict:
    if file.content_type not in ("text/plain", "text/markdown", "application/pdf"):
        raise HTTPException(status_code=400, detail="Only .txt, .md, .pdf files are supported")

    content = await file.read()

    if file.content_type == "application/pdf":
        try:
            import pypdf
            import io

            reader = pypdf.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() for page in reader.pages)
        except ImportError:
            raise HTTPException(status_code=500, detail="pypdf not installed for PDF support")
    else:
        text = content.decode("utf-8", errors="replace")

    point_ids = await rag.ingest_document(
        text=text,
        user_id=user_id,
        source=file.filename or "uploaded_file",
    )
    return {"status": "ingested", "filename": file.filename, "chunks": len(point_ids)}


@router.post("/search")
async def search_knowledge(
    query: str,
    user_id: str,
    top_k: int = 5,
    rag: RAGPipeline = Depends(get_rag_pipeline),
) -> dict:
    results = await rag.retrieve(query=query, user_id=user_id, top_k=top_k)
    return {
        "query": query,
        "results": [
            {"content": r.content, "source": r.source, "score": r.score}
            for r in results
        ],
    }
