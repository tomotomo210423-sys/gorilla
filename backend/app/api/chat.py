import uuid
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import ChatRequest, ChatResponse
from app.core.orchestrator import Orchestrator
from app.db.session import get_db
from app.db.dependencies import get_orchestrator

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> ChatResponse:
    if request.stream:
        raise HTTPException(
            status_code=400,
            detail="Use /stream endpoint for streaming responses",
        )

    from app.core.llm.base import GenerationConfig

    config = GenerationConfig(
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    result = await orchestrator.chat(
        conversation_id=request.conversation_id,
        user_id=request.user_id,
        user_message=request.message,
        config=config,
    )

    return ChatResponse(
        conversation_id=request.conversation_id,
        message_id=str(uuid.uuid4()),
        content=result.content,
        model=result.model,
        reasoning_trace=result.reasoning_trace,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    from app.core.llm.base import GenerationConfig

    config = GenerationConfig(
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    async def event_generator():
        try:
            async for chunk in orchestrator.chat_stream(
                conversation_id=request.conversation_id,
                user_id=request.user_id,
                user_message=request.message,
                config=config,
            ):
                data = json.dumps({"type": "content", "content": chunk}, ensure_ascii=False)
                yield f"data: {data}\n\n"

            done_data = json.dumps(
                {"type": "done", "conversation_id": request.conversation_id},
                ensure_ascii=False,
            )
            yield f"data: {done_data}\n\n"

        except Exception as e:
            error_data = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
