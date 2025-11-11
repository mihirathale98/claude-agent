# HR Agent with Claude Agent SDK

This project implements an HR agent using the official Anthropic Claude Agent SDK that can answer questions about timeoff schedules, employee assignments, and direct reports.

## Getting Started

1. Setup:
  ```bash
  uv venv -p 3.12
  source .venv/bin/activate
  uv pip install -r requirements.txt
  ```

2. Setting up Tracing. Add to `.env`:
   ```.env
   LANGFUSE_PUBLIC_KEY=pk-lf-your-key
   LANGFUSE_SECRET_KEY=sk-lf-your-secret
   LANGFUSE_HOST=your-langfuse-server-url
   ```

3. Starting API Server:
  ```bash
  python api.py
  ```

4. Start Chatting:
  ```bash
  curl -X POST "http://localhost:8080/chat" \
    -H "Content-Type: application/json" \
    -d '{
      "message": "What is the timeoff schedule for nwaters?",
      "session_id": "my-session-123"
    }'
  ```

## Session Management

### How Sessions Work

The Claude Agent SDK manages conversation state automatically:

1. **New Session Creation**: When you call the agent without a `session_id`, the SDK creates a new session and returns its ID
2. **Session Resume**: Pass the `session_id` to continue a previous conversation - the SDK maintains full context
3. **Context Preservation**: The SDK automatically remembers:
   - Previous messages
   - Tool calls and results
   - Conversation flow

### Session Flow Example

**Via API:**

```bash
# 1. Start conversation (new session)
curl -X POST "http://localhost:8080/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Who are my direct reports?"}'

# Response includes session_id
# {"session_id": "abc123", "content": "...", "is_new_session": true}

# 2. Continue conversation (resume session)
curl -X POST "http://localhost:8080/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is nwaters timeoff schedule?",
    "session_id": "abc123"
  }'

# Claude remembers the context from step 1!
```

**Direct Python Usage:**

```python
from hr_agent_claude_sdk import get_claude_agent_response

# First message - creates new session
result1 = await get_claude_agent_response(
    message="What is the timeoff schedule for nwaters?"
)

session_id = result1['session_id']

# Resume session - context is maintained
result2 = await get_claude_agent_response(
    message="What about between January and March?",
    session_id=session_id
)
# Claude remembers we're talking about nwaters' timeoff
```

## Tool Definitions

### get_assignment_id_hr_usecase
- Input: `username` (string)
- Output: Assignment ID or "not found"
- Example: `nwaters` → `15778303`

### get_timeoff_schedule_hr_usecase
- Input: `assignment_id` (string), `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD)
- Output: JSON array of timeoff dates
- Example: `15778303`, `2025-01-01`, `2025-12-31` → `["20250105"]`

### get_direct_reports_hr_usecase
- Input: `username` (string)
- Output: JSON array of direct report usernames
- Example: Any username → `["nwaters", "johndoe"]`

