#!/usr/bin/env python3
"""HR Tools for Claude Agent SDK.

This module contains the HR-specific tools for querying:
- Employee assignment IDs
- Timeoff schedules
- Direct reports
"""

from datetime import datetime
import json
from typing import Any

from claude_agent_sdk import tool


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
