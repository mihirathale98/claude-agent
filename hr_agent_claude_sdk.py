#!/usr/bin/env python3
"""HR Agent using Claude Agent SDK.

This module provides an HR agent that can:
- Get employee assignment IDs
- Retrieve timeoff schedules
- Query direct reports
"""

from typing import Optional, Dict, Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    create_sdk_mcp_server,
    AssistantMessage,
    TextBlock,
)

from tools import (
    get_assignment_id_hr_usecase,
    get_timeoff_schedule_hr_usecase,
    get_direct_reports_hr_usecase,
)


def create_hr_agent_options(session_id: Optional[str] = None):
    """Create and return HR agent options."""
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
If you need more information, ask follow up questions.""",
        resume=session_id if session_id else None,
    )

    return options



async def get_claude_agent_response(
    message: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get a response from the Claude HR agent

    Args:
        message: The user message to send
        session_id: Optional session ID for conversation continuity
                   - If None: creates a new session
                   - If provided: resumes the existing session with full conversation history

    Returns:
        Dict with session_id, content, and is_new_session
    """
    # Create agent options with optional session resumption
    options = create_hr_agent_options(session_id=session_id)

    # Track session info
    is_new_session = session_id is None
    response_text = ""

    # Use ClaudeSDKClient to interact with Claude
    # The client automatically maintains conversation history within the session
    async with ClaudeSDKClient(options=options) as client:
        # Send the user message
        await client.query(message)

        # Collect text from assistant messages
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
            elif isinstance(msg, ResultMessage):
                actual_session_id = msg.session_id

    return {
        "session_id": actual_session_id,
        "content": response_text,
        "is_new_session": is_new_session
    }
