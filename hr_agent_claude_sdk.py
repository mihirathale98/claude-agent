#!/usr/bin/env python3
"""HR Agent using Claude Agent SDK.

This module provides an HR agent with comprehensive Langfuse tracing that can:
- Get employee assignment IDs
- Retrieve timeoff schedules
- Query direct reports
"""

from datetime import datetime
import json
import os
from typing import Any, Optional, Dict
import uuid

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

# Langfuse for observability (optional)
try:
    from langfuse import get_client, propagate_attributes
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize Langfuse client if keys are configured
    langfuse_enabled = bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and
        os.getenv("LANGFUSE_SECRET_KEY")
    )

    if langfuse_enabled:
        # Initialize Langfuse using get_client()
        langfuse_client = get_client()
        print("✅ Langfuse tracing enabled")
    else:
        langfuse_client = None
        print("ℹ️  Langfuse tracing disabled (keys not configured)")

except ImportError:
    langfuse_client = None
    langfuse_enabled = False
    propagate_attributes = None
    print("ℹ️  Langfuse not installed (tracing disabled)")


def validate_datetime(date_text: str) -> bool:
    """Validate that date is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_text, "%Y-%m-%d")
        return True
    except ValueError:
        return False


# Define HR tools using the @tool decorator

@tool("get_assignment_id_hr_usecase", "Get the assignment id from username", {"username": str})
async def get_assignment_id_hr_usecase(args: dict[str, Any]) -> dict[str, Any]:
    """Get the assignment id from username."""
    username = args.get("username", "")

    if username == "nwaters":
        result = "15778303"
    elif username == "johndoe":
        result = "15338303"
    else:
        result = "not found"

    return {
        "content": [{"type": "text", "text": result}]
    }


@tool(
    "get_timeoff_schedule_hr_usecase",
    "Get timeoff schedule for employee based on assignment id, start date and end date",
    {"assignment_id": str, "start_date": str, "end_date": str}
)
async def get_timeoff_schedule_hr_usecase(args: dict[str, Any]) -> dict[str, Any]:
    """Get timeoff schedule for employee."""
    assignment_id = args.get("assignment_id", "")
    start_date = args.get("start_date", "")
    end_date = args.get("end_date", "")

    # Validate dates
    if not validate_datetime(start_date):
        return {
            "content": [
                {"type": "text", "text": f"Incorrect date format {start_date}, should be YYYY-MM-DD"}
            ],
            "is_error": True,
        }

    if not validate_datetime(end_date):
        return {
            "content": [
                {"type": "text", "text": f"Incorrect date format {end_date}, should be YYYY-MM-DD"}
            ],
            "is_error": True,
        }

    # Return timeoff data
    if assignment_id == "15338303":
        result = json.dumps(["20250411", "20250311", "20250101"])
    elif assignment_id == "15778303":
        result = json.dumps(["20250105"])
    else:
        result = json.dumps([])

    return {
        "content": [{"type": "text", "text": result}]
    }


@tool("get_direct_reports_hr_usecase", "Get direct reports for a given username", {"username": str})
async def get_direct_reports_hr_usecase(args: dict[str, Any]) -> dict[str, Any]:
    """Get direct reports for a manager."""
    # Return the same direct reports for any manager (sample data)
    result = json.dumps(["nwaters", "johndoe"])

    return {
        "content": [{"type": "text", "text": result}]
    }


async def create_hr_agent():
    """Create and return an HR agent client."""
    # Create the HR tools server
    hr_tools = create_sdk_mcp_server(
        name="hr-tools",
        version="1.0.0",
        tools=[
            get_assignment_id_hr_usecase,
            get_timeoff_schedule_hr_usecase,
            get_direct_reports_hr_usecase,
        ],
    )

    # Configure Claude to use the HR tools server
    # Pre-approve all HR tools so they can be used without permission prompts
    options = ClaudeAgentOptions(
        mcp_servers={"hr": hr_tools},
        allowed_tools=[
            "mcp__hr__get_assignment_id_hr_usecase",
            "mcp__hr__get_timeoff_schedule_hr_usecase",
            "mcp__hr__get_direct_reports_hr_usecase",
        ],
        system_prompt="""You are an HR Agent that can answer questions related to employee information, timeoff schedules, and direct reports.
Use the tools provided to answer the user's questions.
If you do not have enough information to answer the question, say so.
If you need more information, ask follow up questions."""
    )

    return ClaudeSDKClient(options=options)


async def get_claude_agent_response(
    message: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a response from the Claude HR agent with optional Langfuse tracing.

    Args:
        message: The user message to send
        session_id: Optional session ID for conversation continuity and tracing
        user_id: Optional user ID for tracing attribution

    Returns:
        Dict with session_id, content, and is_new_session
    """
    is_new_session = session_id is None
    actual_session_id = session_id or str(uuid.uuid4())

    # Metadata about available tools and MCP servers
    tools_metadata = {
        "tools_available": [
            "get_assignment_id_hr_usecase",
            "get_timeoff_schedule_hr_usecase",
            "get_direct_reports_hr_usecase"
        ],
        "mcp_servers": ["hr-tools"],
        "agent_version": "1.0.0"
    }

    # Metadata for propagation (must be strings)
    propagated_metadata = {
        "tools_available": json.dumps(tools_metadata["tools_available"]),
        "mcp_servers": json.dumps(tools_metadata["mcp_servers"]),
        "agent_version": "1.0.0"
    }

    # If Langfuse is enabled, trace the interaction
    if langfuse_enabled and langfuse_client and propagate_attributes:
        try:
            # Use propagate_attributes to set trace-level attributes
            with propagate_attributes(
                session_id=actual_session_id,
                user_id=user_id or "anonymous",
                metadata=propagated_metadata,
                tags=["hr-agent", "claude-sdk"]
            ):
                # Create root span for the query
                with langfuse_client.start_as_current_span(
                    name="hr-agent-query",
                    input={"message": message}
                ) as root_span:

                    # Trace user message
                    with langfuse_client.start_as_current_span(
                        name="user-message"
                    ) as user_span:
                        user_span.update(
                            input={"message": message},
                            metadata={"message_type": "user_query"}
                        )

                    # Create agent and process query
                    async with await create_hr_agent() as client:
                        await client.query(message)

                        response_text = ""
                        tool_calls = []
                        tool_results = []
                        message_count = 0

                        async for msg in client.receive_response():
                            message_count += 1

                            # Trace assistant messages
                            if isinstance(msg, AssistantMessage):
                                for block in msg.content:
                                    if isinstance(block, TextBlock):
                                        response_text += block.text

                                    elif isinstance(block, ToolUseBlock):
                                        # Log tool call
                                        tool_call_info = {
                                            "name": block.name,
                                            "input": block.input,
                                            "id": block.id
                                        }
                                        tool_calls.append(tool_call_info)

                                        with langfuse_client.start_as_current_span(
                                            name=f"tool-call-{block.name}"
                                        ) as tool_span:
                                            tool_span.update(
                                                input=block.input,
                                                metadata={
                                                    "tool_name": block.name,
                                                    "tool_id": block.id,
                                                    "tool_type": "mcp_hr_tool"
                                                }
                                            )

                            # Trace tool results
                            elif isinstance(msg, UserMessage):
                                for block in msg.content:
                                    if isinstance(block, ToolResultBlock):
                                        tool_result_info = {
                                            "tool_use_id": block.tool_use_id,
                                            "content": block.content[:200] if block.content else None,
                                            "is_error": block.is_error
                                        }
                                        tool_results.append(tool_result_info)

                                        with langfuse_client.start_as_current_span(
                                            name="tool-result"
                                        ) as result_span:
                                            result_span.update(
                                                output={"content": block.content[:500] if block.content else None},
                                                metadata={
                                                    "tool_use_id": block.tool_use_id,
                                                    "is_error": block.is_error
                                                },
                                                level="ERROR" if block.is_error else "DEFAULT"
                                            )

                            # Trace result message (completion info)
                            elif isinstance(msg, ResultMessage):
                                usage_metadata = {
                                    "is_error": msg.is_error,
                                    "total_cost_usd": msg.total_cost_usd,
                                    "tool_calls_count": len(tool_calls),
                                    "message_count": message_count
                                }

                                # Create generation for the Claude API call
                                with langfuse_client.start_as_current_generation(
                                    name="claude-agent-processing",
                                    model="claude-sonnet-4.5"
                                ) as generation:
                                    generation.update(
                                        input=[{"role": "user", "content": message}],
                                        output=response_text,
                                        metadata={**tools_metadata, **usage_metadata}
                                    )

                        # Trace final assistant response
                        with langfuse_client.start_as_current_span(
                            name="assistant-response"
                        ) as assistant_span:
                            assistant_span.update(
                                output={"response": response_text},
                                metadata={
                                    "message_type": "assistant_response",
                                    "response_length": len(response_text),
                                    "tool_calls": tool_calls,
                                    "tool_results": tool_results
                                }
                            )

                        # Update root span with final output
                        root_span.update(output={"response": response_text})

                    # Flush traces to Langfuse
                    langfuse_client.flush()

                    return {
                        "session_id": actual_session_id,
                        "content": response_text,
                        "is_new_session": is_new_session
                    }

        except Exception as e:
            # Log error to trace
            if langfuse_enabled and langfuse_client:
                try:
                    with langfuse_client.start_as_current_span(name="error") as error_span:
                        error_span.update(
                            metadata={"error": str(e), "error_type": type(e).__name__},
                            level="ERROR"
                        )
                except:
                    pass  # Ignore errors in error logging
                langfuse_client.flush()
            raise

    else:
        # No tracing - execute normally
        async with await create_hr_agent() as client:
            await client.query(message)

            response_text = ""
            async for msg in client.receive_response():
                if isinstance(msg, AssistantMessage):
                    for block in msg.content:
                        if isinstance(block, TextBlock):
                            response_text += block.text

            return {
                "session_id": actual_session_id,
                "content": response_text,
                "is_new_session": is_new_session
            }
