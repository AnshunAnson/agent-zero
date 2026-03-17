# Agent Zero - AI Agent Rules

> **CRITICAL CONSTRAINT**: Source code in `python/` directory is **READ-ONLY**. All user modifications must go through the `usr/` directory extension mechanism.

## Project Overview

Agent Zero is a personal, organic agentic framework that grows and learns with you. It uses the computer as a tool to accomplish tasks, with persistent memory and multi-agent cooperation capabilities.

## Quick Reference

| Command | Description |
|---------|-------------|
| `python run_ui.py --development=true` | Start development server (port 5000) |
| `python run_ui_cn.py` | Start Chinese version server (port 5001) |
| `pytest` | Run all tests |
| `pytest tests/test_file.py::test_name` | Run single test |
| `pip install -r requirements.txt` | Install dependencies |
| `pip install -r requirements.dev.txt` | Install dev dependencies |
| `playwright install chromium` | Install browser agent dependency |

## Environment Setup

### Prerequisites
- **Python 3.12+** (required)
- Node.js (for some frontend tooling)
- Playwright (for browser agent)

### Environment Variables
Configure via `.env` or `A0_SET_*` prefix:
```env
A0_SET_chat_model_provider=openai
A0_SET_chat_model_name=gpt-4
WEB_UI_PORT=5000
WEB_UI_HOST=0.0.0.0
```

### VS Code Debug
Use "Debug run_ui.py" configuration from `.vscode/launch.json`.

---

## ⛔ Source Code Modification Policy

### READ-ONLY Directories
The following directories contain source code and must **NOT** be modified directly:

- `python/` — Core framework code
- `prompts/` — Default prompt templates
- `agents/_example/` — Example agent profile (reference only)

### Why This Matters
1. **Upgradability**: Direct modifications prevent clean updates to newer versions
2. **Traceability**: Changes in `usr/` are clearly separated from upstream
3. **Maintainability**: Extension pattern ensures consistent override behavior

---

## ✅ User Modification Locations

All user customizations go in the `usr/` directory:

| Directory | Purpose |
|-----------|---------|
| `usr/prompts/` | Custom prompt overrides (same structure as `prompts/`) |
| `usr/extensions/` | Custom extensions (same structure as `python/extensions/`) |
| `usr/settings.json` | User settings configuration |
| `usr/secrets.env` | Sensitive credentials |
| `usr/skills/` | SKILL.md compatible skills |
| `usr/workdir/` | Working directory for agent file operations |
| `usr/projects/` | Project-specific contexts, memory, secrets |
| `usr/webui/components/` | Custom UI components |
| `usr/knowledge/` | Knowledge base files |

### Agent Profiles
Custom agent configurations go in `agents/<profile>/`:

| Directory | Purpose |
|-----------|---------|
| `agents/<profile>/tools/` | Custom tools for this agent |
| `agents/<profile>/extensions/` | Custom extensions for this agent |
| `agents/<profile>/prompts/` | Custom prompts for this agent |
| `agents/<profile>/agent.json` | Agent configuration override |

---

## Extension Development

### Extension Points

| Point | When It Runs | Use Case |
|-------|--------------|----------|
| `agent_init` | Agent initialization | Configure agent behavior |
| `tool_execute_before` | Before tool execution | Preprocess tool arguments |
| `tool_execute_after` | After tool execution | Post-process results, logging |
| `monologue_start` | Start of agent loop | Setup for new iteration |
| `monologue_end` | End of agent loop | Cleanup, background tasks |

### Creating Extensions

```python
# File: usr/extensions/tool_execute_after/_20_my_extension.py
# Naming: {priority}_{name}.py (lower number = earlier execution)

from python.helpers.extension import Extension

class MyExtension(Extension):
    async def execute(self, **kwargs):
        # Access context via kwargs
        response = kwargs.get("response")
        tool_name = kwargs.get("tool_name")
        
        # Your logic here
        pass
```

### Creating Tools

```python
# File: agents/my_agent/tools/my_tool.py
from python.helpers.tool import Tool, Response

class MyTool(Tool):
    async def execute(self, **kwargs):
        param = self.args.get("param_name", "default")
        
        return Response(
            message="Result message",
            break_loop=False  # Set True to stop agent loop
        )
```

### Creating Prompts

Create override prompts in `usr/prompts/` with the same relative path:

```
# Override agent system prompt
usr/prompts/agent.system.main.md

# Add extra prompts (loaded automatically)
usr/prompts/agent.extras.my_custom.md
```

---

## Code Style Guidelines

### Python Conventions
- Follow **PEP 8** standards
- Use **Python 3.12+** syntax features
- Include **type hints** for all function signatures

### Import Order
```python
# 1. Standard library
from abc import abstractmethod
from dataclasses import dataclass
from typing import Any

# 2. Third-party
import pytest

# 3. Local imports
from agent import Agent, LoopData
from python.helpers.print_style import PrintStyle
```

### Naming Conventions
- **Classes**: PascalCase (`ResponseTool`, `ExampleExtension`)
- **Functions/Methods**: snake_case (`execute`, `before_execution`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_RETRIES`)
- **Private Methods**: prefix with underscore (`_get_extensions`)

### Type Hints
```python
from typing import Any

async def execute(self, **kwargs) -> Response:
    pass

def get_variables(self, file: str, backup_dirs: list[str] | None = None) -> dict[str, Any]:
    pass
```

### Async Patterns
- All tool execution is async
- Use `asyncio` for concurrent operations
- Background tasks use `DeferredTask` from `python.helpers.defer`

### Error Handling
- Use `PrintStyle` for logging (not `print()`)
- Let exceptions propagate with context
- Tools return `Response` objects

---

## Testing

### Run Tests
```bash
# Install dev dependencies first
pip install -r requirements.dev.txt

# Run all tests
pytest

# Run specific test file
pytest tests/test_websocket_handlers.py

# Run single test
pytest tests/test_websocket_handlers.py::test_websocket_result_ok_clones_payload

# Run with verbose output
pytest -v
```

### Test Structure
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_my_feature():
    # Arrange
    mock_agent = AsyncMock()
    
    # Act
    result = await my_function(mock_agent)
    
    # Assert
    assert result is not None
```

---

## Key Architecture Files

| File | Purpose |
|------|---------|
| `run_ui.py` | Web server entry point |
| `initialize.py` | Agent initialization and configuration |
| `agent.py` | Main agent loop (root level) |
| `python/helpers/tool.py` | Base Tool class |
| `python/helpers/extension.py` | Base Extension class |
| `python/helpers/files.py` | File utilities and prompt loading |
| `prompts/agent.system.main.md` | Main system prompt template |

---

## VCP Integration (Custom)

This instance includes VCP (Variable & Command Protocol) integration:

### VCP Knowledge System
- **Location**: `E:\VCP\VCPToolBox\dailynote\` (148 markdown files)
- **Symlink**: `usr/knowledge/vcp_all/main/dailynote` → VCP dailynote directory
- **Settings**: `agent_knowledge_subdir: vcp_all`
- **Content**: All VCP notes, habits, development docs, forum posts

### VCP Habits (Writable)
- **Location**: `E:\VCP\VCPToolBox\dailynote\个人习惯库\记录\`
- **Symlink**: `usr/knowledge/vcp_habits/` → VCP habits directory
- **Prompt**: `usr/prompts/agent.extras.vcp_memory.md`

### Shared Memory (FAISS)
- **Location**: `E:\VCP\VCPToolBox\shared_memory\agent-zero\`
- **Symlink**: `usr/memory/default` → Shared memory
- **Purpose**: Cross-agent vector database sharing

### Emergence Detection
- **Extension**: `usr/extensions/tool_execute_after/_20_emergence_detection.py`
- **Tracking**: `usr/vcp_emergence_tracking.json`
- **Semantic Groups**: `usr/vcp_semantic_groups.json`
- **Threshold**: Tags appearing 3+ times trigger new group creation

### Tag Format
```
Tag: [来源:公共], TypeScript, 前端开发, 类型安全
```

---

## Common Tasks

### Adding a New Tool
1. Create `agents/<profile>/tools/my_tool.py`
2. Inherit from `Tool` class
3. Implement `async def execute(self, **kwargs)`
4. Return `Response(message="...", break_loop=False)`

### Adding a New Extension
1. Create `usr/extensions/<extension_point>/_XX_name.py`
2. Inherit from `Extension` class
3. Implement `async def execute(self, **kwargs)`
4. Use appropriate kwargs for the extension point

### Overriding Prompts
1. Identify the prompt to override (check `prompts/` structure)
2. Create same relative path in `usr/prompts/`
3. Content in `usr/` takes precedence

### Adding UI Components
1. Create component in `usr/webui/components/`
2. Follow existing component patterns in `python/webui/components/`

---

## Troubleshooting

### Common Issues
1. **Port already in use**: Change `WEB_UI_PORT` environment variable
2. **Import errors**: Ensure Python 3.12+ and all dependencies installed
3. **Browser agent fails**: Run `playwright install chromium`
4. **Memory issues**: Check `usr/knowledge/` directory permissions

### Debug Mode
Run with development flag for verbose logging:
```bash
python run_ui.py --development=true
```

---

## Reference Links

- [Installation Guide](./docs/setup/installation.md)
- [Development Setup](./docs/setup/dev-setup.md)
- [Extensions Documentation](./docs/developer/extensions.md)
- [Contribution Guidelines](./docs/guides/contribution.md)
- [WebSocket Infrastructure](./docs/developer/websockets.md)
- [Architecture Overview](./docs/developer/architecture.md)
