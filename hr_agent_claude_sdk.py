#!/usr/bin/env python3
"""HR Agent using Claude Agent SDK.

This module provides an HR agent that can:
- Get employee assignment IDs
- Retrieve timeoff schedules
- Query direct reports
"""

from typing import Optional, Dict, Any
import uuid

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
)

from tools import (
    get_assignment_id_hr_usecase,
    get_timeoff_schedule_hr_usecase,
    get_direct_reports_hr_usecase,
)


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
    Get a response from the Claude HR agent

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
