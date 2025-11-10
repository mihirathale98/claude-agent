# HR Agent with Claude Agent SDK

This project implements an HR agent using the official Anthropic Claude Agent SDK that can answer questions about timeoff schedules, employee assignments, and direct reports.

## Features

The agent provides three main capabilities:
- Get assignment ID for an employee by username
- Get timeoff schedule for an employee by assignment ID and date range
- Get direct reports for a manager

## Prerequisites

1. Python 3.10+
2. Node.js (required by Claude Agent SDK)
3. Claude Code 2.0.0+: `npm install -g @anthropic-ai/claude-code`
4. (Optional) Google Cloud Project with Vertex AI if using Vertex AI backend

## Setup

### Installation Steps

1. Install Claude Code globally:
```bash
npm install -g @anthropic-ai/claude-code
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file:
```bash
cp .env.example .env
# Edit .env and configure your authentication method (see below)
```

### Authentication Options

#### Option 1: Direct Claude API (Default)
Set your Anthropic API key in `.env`:
```env
ANTHROPIC_API_KEY=your-api-key-here
```

#### Option 2: Google Vertex AI
To use Claude through Vertex AI, set the following in `.env`:
```env
CLAUDE_CODE_USE_VERTEX=1
VERTEX_PROJECT_ID=your-gcp-project-id
VERTEX_REGION=us-east5
```

Then authenticate with Google Cloud:
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

#### Option 3: Amazon Bedrock
```env
CLAUDE_CODE_USE_BEDROCK=1
AWS_REGION=us-east-1
```

### Langfuse Observability (Optional)

Optional LLM observability for tracing agent interactions, tool calls, and performance metrics.

**Setup:**
1. Sign up at https://cloud.langfuse.com
2. Get your API keys from project settings
3. Add to `.env`:
   ```env
   LANGFUSE_PUBLIC_KEY=pk-lf-your-key
   LANGFUSE_SECRET_KEY=sk-lf-your-secret
   LANGFUSE_HOST=your-langfuse-server-url
   ```
4. Restart the server - traces appear automatically at https://cloud.langfuse.com

**What's traced:**
- User messages and agent responses
- Tool calls (get_assignment_id, get_timeoff_schedule, etc.) with inputs/outputs
- Session tracking for conversation continuity
- Metadata: tools available, MCP servers, costs, token usage

The app runs normally without Langfuse configured - tracing is completely optional.

## Usage

### REST API

Start the FastAPI server:
```bash
python api.py
```

The API will be available at `http://localhost:8080`

Access the interactive API documentation:
- Swagger UI: `http://localhost:8080/docs`
- ReDoc: `http://localhost:8080/redoc`

#### API Endpoints

**GET /** - Health check
```bash
curl http://localhost:8080/
```

**POST /chat** - Send a message to the agent
```bash
curl -X POST "http://localhost:8080/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the timeoff schedule for nwaters?",
    "session_id": "my-session-123"
  }'
```

Response:
```json
{
  "session_id": "my-session-123",
  "content": "Based on the timeoff schedule, nwaters has the following timeoff date: 2025-01-05.",
  "timestamp": "2025-11-08T10:30:00",
  "is_new_session": false
}
```

**GET /sessions/{session_id}** - Retrieve session history
```bash
curl http://localhost:8080/sessions/my-session-123
```

**GET /sessions** - List all sessions
```bash
curl http://localhost:8080/sessions
```

**DELETE /sessions/{session_id}** - Delete a session
```bash
curl -X DELETE http://localhost:8080/sessions/my-session-123
```

### Testing

Run the test suite:
```bash
python test_chat_api.py
```

This will test:
- Health check endpoint
- Chat functionality with various queries
- Session management
- Error handling

## Architecture

### Claude Agent SDK Implementation

This implementation uses the official Claude Agent SDK with integrated Langfuse observability:

**Core Components:**

1. **Custom HR Tools** (`hr_agent_claude_sdk.py`):
   - `get_assignment_id_hr_usecase` - Get employee assignment ID by username
   - `get_timeoff_schedule_hr_usecase` - Get timeoff schedule by assignment ID and date range
   - `get_direct_reports_hr_usecase` - Get direct reports for a manager
   - Tools defined using `@tool` decorator and registered with MCP server

2. **Agent Function** (`get_claude_agent_response`):
   - Accepts: message, session_id (optional), user_id (optional)
   - Returns: session_id, content, is_new_session
   - Includes comprehensive Langfuse tracing (optional)
   - Handles all Claude SDK interactions

3. **REST API** (`api.py`):
   - FastAPI server exposing `/chat` endpoint
   - Session management with in-memory storage
   - Clean separation: NO Langfuse dependencies in API layer

4. **Langfuse Observability** (optional):
   - Traces user messages, agent responses, tool calls, tool results
   - Captures metadata: tools available, MCP servers, costs, session IDs
   - Standard Langfuse format: trace → span → generation hierarchy
   - All tracing logic isolated in agent module

### Key Features

1. **Official SDK**: Uses Anthropic's official Claude Agent SDK
2. **MCP Integration**: Tools follow Model Context Protocol standard
3. **Multi-Backend Support**: Works with Direct API, Vertex AI, or Bedrock
4. **Automatic Management**: SDK handles context, caching, and session state
5. **Async-First**: Built on async/await for better performance
6. **Optional Observability**: Langfuse tracing can be enabled/disabled via environment variables

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

### Important Notes

- **SDK Session Persistence**: Sessions persist in `~/.claude/projects/` directory
- **Resume Anytime**: You can resume a session even after restarting your application
- **Context Limits**: SDK automatically handles context window limits with smart truncation
- **Session Cleanup**: Deleting API session data doesn't delete SDK sessions

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

## Vertex AI Configuration

### Supported Regions

- `us-east5` (recommended)
- `us-central1`
- `europe-west1`
- `europe-west4`

### IAM Permissions Required

Your service account or user needs:
- `roles/aiplatform.user` - Vertex AI User

Grant permissions:
```bash
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="user:YOUR_EMAIL" \
    --role="roles/aiplatform.user"
```

### Enable Vertex AI API

```bash
gcloud services enable aiplatform.googleapis.com
```

## Troubleshooting

### Claude Code Not Found
```bash
# Install Claude Code globally
npm install -g @anthropic-ai/claude-code

# Verify installation
claude-code --version
```

### Authentication Issues (Vertex AI)
```bash
# Re-authenticate
gcloud auth application-default login

# Verify credentials
gcloud auth application-default print-access-token
```

### Project Not Set
```bash
# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Verify
gcloud config get-value project
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Production Considerations

1. **Session Storage**: Replace in-memory sessions with Redis or a database
2. **CORS**: Configure `allow_origins` in `api.py` for your specific domains
3. **Rate Limiting**: Add rate limiting middleware
4. **Authentication**: Implement API key or OAuth authentication
5. **Error Handling**: Implement retry logic and circuit breakers
6. **Observability**: Consider self-hosting Langfuse for production use

## License

MIT License - see LICENSE file for details
