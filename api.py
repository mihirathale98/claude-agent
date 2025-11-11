# Setup Claude-Agent tracer:
import base64
import os
from openinference.instrumentation import using_session
from opentelemetry import trace, context as otel_context
from opentelemetry.sdk.trace import TracerProvider, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

# Set environment variables for LangChain
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
os.environ["LANGSMITH_TRACING"] = "true"

lf_base_url = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com").rstrip("/")
OTEL_ENDPOINT = f"{lf_base_url}/api/public/otel/v1/traces"

lf_public = os.getenv("LANGFUSE_PUBLIC_KEY")
lf_secret = os.getenv("LANGFUSE_SECRET_KEY")
auth_b64 = base64.b64encode(f"{lf_public}:{lf_secret}".encode("utf-8")).decode("ascii")
HEADERS = {"Authorization": f"Basic {auth_b64}"}

# Custom span processor to map session id to langfuse
class LangsmithSessionToLangfuseProcessor(SpanProcessor):
    def on_start(self, span, parent_context=None):
        ctx = parent_context or otel_context.get_current()
        sess = ctx.get("session.id")
        if sess: span.set_attribute("session.id", sess)

# Configure the OTLP exporter for your custom endpoint
provider = TracerProvider()
otlp_exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, headers=HEADERS)
processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(LangsmithSessionToLangfuseProcessor())
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

from langsmith.integrations.claude_agent_sdk import configure_claude_agent_sdk
configure_claude_agent_sdk()
# ===

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timezone
from hr_agent_claude_sdk import get_claude_agent_response


# Initialize FastAPI app
app = FastAPI(
    title="HR Agent API",
    description="REST API for HR Agent powered by Claude Agent SDK",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage for conversation history tracking
# The SDK maintains its own session state, but we track history for the API
sessions: Dict[str, List[Dict[str, str]]] = {}
# Map our API session IDs to SDK session IDs
sdk_session_map: Dict[str, str] = {}


# Pydantic models
class Message(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "What is the timeoff schedule for nwaters?"
            }
        }
    )

    role: str = Field(..., description="Role of the message sender (user or assistant)")
    content: str = Field(..., description="Content of the message")


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "What is the timeoff schedule for nwaters?",
                "session_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    )

    message: str = Field(..., description="User message to send to the agent")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity. If not provided, a new session will be created by the SDK.")


class ChatResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": "claude-sdk-session-123",
                "content": "Based on the timeoff schedule, nwaters has the following timeoff date: 2025-01-05.",
                "timestamp": "2025-11-07T10:30:00",
                "is_new_session": False
            }
        }
    )

    session_id: str = Field(..., description="Session ID for this conversation (managed by Claude SDK)")
    content: str = Field(..., description="Agent's response")
    timestamp: str = Field(..., description="Timestamp of the response")
    is_new_session: bool = Field(..., description="Whether this is a new session or resumed")


class SessionResponse(BaseModel):
    session_id: str = Field(..., description="API Session ID")
    sdk_session_id: Optional[str] = Field(..., description="Claude SDK Session ID")
    conversation_history: List[Message] = Field(..., description="Full conversation history for this session")
    message_count: int = Field(..., description="Number of messages in the conversation")


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "HR Agent API (Claude Agent SDK)",
        "version": "1.0.0"
    }


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Send a message to the HR agent and get a response.

    The Claude Agent SDK manages session state automatically:
    - If session_id is provided, the SDK resumes that session (conversation context is maintained)
    - If no session_id, the SDK creates a new session and returns the session ID
    - The SDK maintains full conversation history internally
    """
    # Get SDK session ID (either from request or create new)
    sdk_session_id = request.session_id

    # Create API session for tracking
    api_session_id = request.session_id or str(uuid.uuid4())

    if api_session_id not in sessions:
        sessions[api_session_id] = []

    # Add user message to our tracking
    sessions[api_session_id].append({
        "role": "user",
        "content": request.message
    })

    try:
        # Get agent response with SDK session management
        with using_session(sdk_session_id):
            result = await get_claude_agent_response(
                message=request.message,
                session_id=sdk_session_id  # SDK handles resume if provided
            )

        # Update our SDK session mapping
        sdk_session_map[api_session_id] = result["session_id"]

        # Add assistant response to our tracking
        sessions[api_session_id].append({
            "role": "assistant",
            "content": result["content"]
        })

        return ChatResponse(
            session_id=result["session_id"],  # Return SDK session ID
            content=result["content"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            is_new_session=result["is_new_session"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/sessions/{session_id}", response_model=SessionResponse, tags=["Sessions"])
async def get_session(session_id: str):
    """
    Retrieve the conversation history for a specific API session.

    Note: This returns the conversation history tracked by the API.
    The Claude SDK maintains its own session state which cannot be directly accessed.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    conversation = sessions[session_id]
    sdk_session = sdk_session_map.get(session_id)

    return SessionResponse(
        session_id=session_id,
        sdk_session_id=sdk_session,
        conversation_history=[Message(**msg) for msg in conversation],
        message_count=len(conversation)
    )


@app.delete("/sessions/{session_id}", tags=["Sessions"])
async def delete_session(session_id: str):
    """
    Delete an API session and its conversation history.

    Note: This only deletes the API's tracking data.
    The Claude SDK session persists and can still be resumed using its session ID.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    sdk_session = sdk_session_map.get(session_id)
    del sessions[session_id]
    if session_id in sdk_session_map:
        del sdk_session_map[session_id]

    return {
        "message": f"API session {session_id} deleted successfully",
        "note": f"SDK session {sdk_session} can still be resumed"
    }


@app.get("/sessions", tags=["Sessions"])
async def list_sessions():
    """
    List all active API sessions.
    """
    session_list = [
        {
            "api_session_id": sid,
            "sdk_session_id": sdk_session_map.get(sid),
            "message_count": len(conversation),
            "last_message": conversation[-1] if conversation else None
        }
        for sid, conversation in sessions.items()
    ]

    return {
        "total_sessions": len(sessions),
        "sessions": session_list
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
