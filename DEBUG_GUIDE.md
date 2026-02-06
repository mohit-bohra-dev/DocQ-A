# Debugging Guide for Document QA RAG Agent

This guide explains how to debug the Streamlit UI and FastAPI backend of the Document QA RAG Agent.

## Quick Start

### 1. Enable Debug Mode
```bash
# Set environment variable
export DEBUG_STREAMLIT=true  # Linux/Mac
set DEBUG_STREAMLIT=true     # Windows CMD
$env:DEBUG_STREAMLIT="true"  # Windows PowerShell
```

### 2. Start Debug Session
```bash
# Option 1: Use the debug script
python debug_streamlit.py

# Option 2: Manual start with debug
DEBUG_STREAMLIT=true uv run streamlit run streamlit_app.py --server.headless true
```

### 3. Attach Debugger
- **VS Code**: Use F5 or "Run and Debug" → "Debug Streamlit App"
- **PyCharm**: Create remote debug configuration for localhost:5678
- **Command line**: Any Python debugger that supports remote attachment

## Debug Features

### 1. Debug Logging
When `DEBUG_STREAMLIT=true`, the app will print detailed logs:
- Function entry/exit with timing
- API calls and responses
- Session state changes
- Exception details with full tracebacks

### 2. Breakpoint Debugging
Set breakpoints in:
- `streamlit_app.py` - UI logic and event handlers
- `src/ui_utils.py` - API communication
- `src/debug_utils.py` - Debug utilities

### 3. Session State Inspection
Debug mode automatically prints session state changes, showing:
- Conversation history
- Uploaded documents
- Processing status
- Current question

## VS Code Setup

### 1. Create `.vscode/launch.json`
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug Streamlit App",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "."
                }
            ],
            "justMyCode": false,
            "console": "integratedTerminal"
        }
    ]
}
```

### 2. Debug Workflow
1. Start debug session: `python debug_streamlit.py`
2. Wait for "Waiting for debugger to attach..." message
3. In VS Code: Press F5 or use "Run and Debug"
4. Set breakpoints in your code
5. Use the Streamlit UI to trigger breakpoints

## Common Debug Scenarios

### 1. Document Upload Issues
Set breakpoints in:
- `handle_document_upload()` - File validation
- `handle_upload_processing()` - API communication
- `APIClient.upload_document()` - HTTP request details

### 2. Query Processing Issues
Set breakpoints in:
- `handle_question_submission()` - Question processing
- `APIClient.query_documents()` - API calls
- `format_source_references()` - Response formatting

### 3. UI State Issues
Set breakpoints in:
- `initialize_session_state()` - State initialization
- Any function that modifies `st.session_state`
- `display_*()` functions for UI rendering

### 4. API Communication Issues
Set breakpoints in:
- `src/ui_utils.py` - All API client methods
- `HealthChecker.get_health_status()` - Backend connectivity
- Error handling in API methods

## Debug Utilities

### 1. Debug Context Manager
```python
with DebugContext("my_operation"):
    # Your code here
    pass
# Automatically logs timing and exceptions
```

### 2. Debug Logging Functions
```python
debug_print("Custom message")
debug_exception(exception, "context")
debug_session_state(st.session_state)
debug_api_call("endpoint", payload, response)
```

### 3. Function Decorator
```python
@debug_function
def my_function():
    # Automatically logged
    pass
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG_STREAMLIT` | Enable debug mode | `false` |
| `PYTHONPATH` | Python module search path | Current directory |

## Troubleshooting

### Debug Server Won't Start
- **Port in use**: Change port in debug setup
- **Permission denied**: Run with appropriate permissions
- **Module not found**: Check PYTHONPATH

### Debugger Won't Attach
- **Firewall**: Allow connections to port 5678
- **Wrong host**: Ensure using localhost/127.0.0.1
- **Timing**: Wait for "Waiting for debugger" message

### Breakpoints Not Hit
- **Wrong file**: Ensure breakpoint is in executed code path
- **Just My Code**: Disable in debugger settings
- **Path mapping**: Check localRoot/remoteRoot in launch.json

### Performance Issues
- **Too much logging**: Disable debug mode for production
- **Large session state**: Clear history regularly
- **Network timeouts**: Increase timeout values

## Advanced Debugging

### 1. Remote Debugging
For debugging on remote servers:
```python
debugpy.listen(("0.0.0.0", 5678))  # Listen on all interfaces
```

### 2. Conditional Breakpoints
Set breakpoints that only trigger under specific conditions:
```python
# In VS Code, right-click breakpoint → Edit Breakpoint → Add condition
# Example: len(st.session_state.conversation_history) > 5
```

### 3. Log Analysis
Debug logs include timestamps for performance analysis:
```
[15:30:45.123] [INFO] 🚀 Starting: handle_upload_processing
[15:30:47.456] [INFO] ✅ Completed: handle_upload_processing (2.333s)
```

## Production Considerations

### 1. Disable Debug Mode
```bash
unset DEBUG_STREAMLIT  # Linux/Mac
set DEBUG_STREAMLIT=   # Windows
```

### 2. Remove Debug Code
For production deployment, consider removing or commenting out:
- `debugpy` imports and setup
- Debug logging calls
- Development-only features

### 3. Security
- Never expose debug ports in production
- Remove debug credentials from version control
- Use environment-specific configurations

## Files Reference

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Main UI with debug integration |
| `debug_streamlit.py` | Debug startup script |
| `src/debug_utils.py` | Debug utility functions |
| `debug_config.json` | VS Code configuration templates |
| `.vscode/launch.json` | VS Code debug configurations |

## Getting Help

If you encounter issues:
1. Check the debug logs for error messages
2. Verify environment variables are set correctly
3. Ensure all dependencies are installed: `uv sync`
4. Test with a minimal example first
5. Check network connectivity to FastAPI backend