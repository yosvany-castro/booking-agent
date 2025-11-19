"""Dating Agent API endpoints for handling chat interactions.

This module provides endpoints for dating agent interactions without traditional
authentication. Users are identified via session_id and org_id headers.
"""

import json
from typing import Optional

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Request,
)
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.limiter import limiter
from app.core.logging import (
    bind_context,
    logger,
)
from app.core.metrics import llm_stream_duration_seconds
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    StreamResponse,
)

router = APIRouter()
agent = LangGraphAgent()


def validate_headers(session_id: str, org_id: str) -> None:
    """Validate required headers are present and not empty.

    Args:
        session_id: The session identifier
        org_id: The organization identifier

    Raises:
        HTTPException: If headers are missing or invalid
    """
    if not session_id or not session_id.strip():
        raise HTTPException(
            status_code=400,
            detail="X-Session-ID header is required and cannot be empty",
        )
    if not org_id or not org_id.strip():
        raise HTTPException(
            status_code=400,
            detail="X-Org-ID header is required and cannot be empty",
        )


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])
async def chat(
    request: Request,
    chat_request: ChatRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
):
    """Process a chat request for the dating agent.

    Users are identified via session_id and org_id headers instead of JWT tokens.
    The session_id is used as the thread_id for LangGraph state persistence.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        x_session_id: Session identifier from X-Session-ID header.
        x_org_id: Organization identifier from X-Org-ID header.

    Returns:
        ChatResponse: The processed chat response.

    Raises:
        HTTPException: If there's an error processing the request or headers are invalid.
    """
    try:
        # Validate headers
        validate_headers(x_session_id, x_org_id)

        # Bind context for logging
        bind_context(session_id=x_session_id, org_id=x_org_id)

        logger.info(
            "dating_agent_chat_request_received",
            session_id=x_session_id,
            org_id=x_org_id,
            message_count=len(chat_request.messages),
        )

        # Use session_id as thread_id for LangGraph
        # Use combination of org_id + session_id as user_id for memory isolation
        user_id = f"{x_org_id}:{x_session_id}"

        result = await agent.get_response(
            chat_request.messages,
            session_id=x_session_id,
            user_id=user_id,
        )

        logger.info(
            "dating_agent_chat_request_processed",
            session_id=x_session_id,
            org_id=x_org_id,
        )

        return ChatResponse(messages=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "dating_agent_chat_request_failed",
            session_id=x_session_id,
            org_id=x_org_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
):
    """Process a chat request for the dating agent with streaming response.

    Users are identified via session_id and org_id headers instead of JWT tokens.
    The session_id is used as the thread_id for LangGraph state persistence.

    Args:
        request: The FastAPI request object for rate limiting.
        chat_request: The chat request containing messages.
        x_session_id: Session identifier from X-Session-ID header.
        x_org_id: Organization identifier from X-Org-ID header.

    Returns:
        StreamingResponse: A streaming response of the chat completion.

    Raises:
        HTTPException: If there's an error processing the request or headers are invalid.
    """
    try:
        # Validate headers
        validate_headers(x_session_id, x_org_id)

        # Bind context for logging
        bind_context(session_id=x_session_id, org_id=x_org_id)

        logger.info(
            "dating_agent_stream_chat_request_received",
            session_id=x_session_id,
            org_id=x_org_id,
            message_count=len(chat_request.messages),
        )

        async def event_generator():
            """Generate streaming events.

            Yields:
                str: Server-sent events in JSON format.

            Raises:
                Exception: If there's an error during streaming.
            """
            try:
                full_response = ""
                user_id = f"{x_org_id}:{x_session_id}"

                with llm_stream_duration_seconds.labels(
                    model=agent.llm_service.get_llm().get_name()
                ).time():
                    async for chunk in agent.get_stream_response(
                        chat_request.messages,
                        session_id=x_session_id,
                        user_id=user_id,
                    ):
                        full_response += chunk
                        response = StreamResponse(content=chunk, done=False)
                        yield f"data: {json.dumps(response.model_dump())}\n\n"

                # Send final message indicating completion
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump())}\n\n"

            except Exception as e:
                logger.error(
                    "dating_agent_stream_chat_request_failed",
                    session_id=x_session_id,
                    org_id=x_org_id,
                    error=str(e),
                    exc_info=True,
                )
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "dating_agent_stream_chat_request_failed",
            session_id=x_session_id,
            org_id=x_org_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def get_session_messages(
    request: Request,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
):
    """Get all messages for a dating agent session.

    Args:
        request: The FastAPI request object for rate limiting.
        x_session_id: Session identifier from X-Session-ID header.
        x_org_id: Organization identifier from X-Org-ID header.

    Returns:
        ChatResponse: All messages in the session.

    Raises:
        HTTPException: If there's an error retrieving the messages or headers are invalid.
    """
    try:
        # Validate headers
        validate_headers(x_session_id, x_org_id)

        # Bind context for logging
        bind_context(session_id=x_session_id, org_id=x_org_id)

        messages = await agent.get_chat_history(x_session_id)

        logger.info(
            "dating_agent_messages_retrieved",
            session_id=x_session_id,
            org_id=x_org_id,
            message_count=len(messages),
        )

        return ChatResponse(messages=messages)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "dating_agent_get_messages_failed",
            session_id=x_session_id,
            org_id=x_org_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])
async def clear_chat_history(
    request: Request,
    x_session_id: str = Header(..., alias="X-Session-ID"),
    x_org_id: str = Header(..., alias="X-Org-ID"),
):
    """Clear all messages for a dating agent session.

    Args:
        request: The FastAPI request object for rate limiting.
        x_session_id: Session identifier from X-Session-ID header.
        x_org_id: Organization identifier from X-Org-ID header.

    Returns:
        dict: A message indicating the chat history was cleared.

    Raises:
        HTTPException: If there's an error clearing the history or headers are invalid.
    """
    try:
        # Validate headers
        validate_headers(x_session_id, x_org_id)

        # Bind context for logging
        bind_context(session_id=x_session_id, org_id=x_org_id)

        await agent.clear_chat_history(x_session_id)

        logger.info(
            "dating_agent_chat_history_cleared",
            session_id=x_session_id,
            org_id=x_org_id,
        )

        return {"message": "Chat history cleared successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "dating_agent_clear_chat_history_failed",
            session_id=x_session_id,
            org_id=x_org_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
