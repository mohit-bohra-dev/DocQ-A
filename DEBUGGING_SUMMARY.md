# Streamlit App Debugging - Setup Complete ✅

Your Streamlit app is now fully debuggable! Here's what has been implemented:

## 🎯 Quick Start Commands

### Start Debug Session
```bash
# Method 1: Use the debug script (Recommended)
python debug_streamlit.py

# Method 2: Manual with environment variable
$env:DEBUG_STREAMLIT="true"  # Windows PowerShell
uv run streamlit run streamlit_app.py --server.headless true
```

### Attach Debugger (VS Code)
1. Start the debug session above
2. Wait for "Waiting for debugger to attach..." message
3. Press **F5** or use **Run and Debug** → **"Debug Streamlit App"**
4. Set breakpoints and debug!

## 🔧 What's Been Added

### 1. Debug Infrastructure
- ✅ `debugpy` integration with conditional loading
- ✅ Environment-based debug mode (`DEBUG_STREAMLIT=true`)
- ✅ Comprehensive debug utilities in `src/debug_utils.py`
- ✅ Debug startup script (`debug_streamlit.py`)

### 2. Debug Features
- ✅ **Breakpoint debugging** - Set breakpoints anywhere in the code
- ✅ **Debug logging** - Detailed logs with timestamps
- ✅ **Session state inspection** - Automatic session state dumps
- ✅ **API call tracing** - Log all API requests/responses
- ✅ **Exception handling** - Full tracebacks with context
- ✅ **Performance timing** - Function execution timing

### 3. Enhanced Error Handling
- ✅ Try-catch blocks around critical operations
- ✅ Detailed error messages with context
- ✅ Graceful fallbacks for debug failures

## 📁 Files Created/Modified

| File | Purpose |
|------|---------|
| `streamlit_app.py` | ✅ Enhanced with debug integration |
| `debug_streamlit.py` | ✅ Debug startup script |
| `src/debug_utils.py` | ✅ Debug utility functions |
| `debug_config.json` | ✅ VS Code configuration templates |
| `DEBUG_GUIDE.md` | ✅ Comprehensive debugging guide |

## 🚀 Usage Examples

### Set Breakpoints
```python
# In streamlit_app.py - Set breakpoint on any line
def handle_question_submission(question: str, top_k: int):
    # Breakpoint here ← Click in VS Code gutter
    with DebugContext("handle_question_submission"):
        # Your debugging session starts here
```

### Debug Logging
```python
# Automatic debug logs when DEBUG_STREAMLIT=true
debug_print("Custom debug message")
debug_api_call("upload", {"file": "test.pdf"}, response)
```

### Session State Inspection
```python
# Automatically logged in debug mode
debug_session_state(st.session_state)
```

## 🎯 Common Debug Scenarios

### 1. Document Upload Issues
- Set breakpoint in `handle_upload_processing()`
- Check API response in `APIClient.upload_document()`
- Inspect file validation in `validate_pdf_file()`

### 2. Query Processing Issues
- Set breakpoint in `handle_question_submission()`
- Check API communication in `query_documents()`
- Inspect response formatting

### 3. UI State Issues
- Set breakpoint in `initialize_session_state()`
- Check session state changes
- Debug UI rendering functions

## 🔍 VS Code Integration

### Launch Configuration (add to `.vscode/launch.json`)
```json
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
    "justMyCode": false
}
```

## 🛠️ Troubleshooting

### Debug Server Won't Start
- Check if port 5678 is available
- Ensure `debugpy` is installed: `uv add debugpy` ✅

### Breakpoints Not Hit
- Ensure debug mode is enabled: `DEBUG_STREAMLIT=true`
- Wait for "Waiting for debugger" message before attaching
- Check that breakpoints are in executed code paths

### Performance Issues
- Debug mode adds overhead - disable for production
- Use `unset DEBUG_STREAMLIT` to disable

## 🎉 You're Ready to Debug!

Your Streamlit app now has professional-grade debugging capabilities:

1. **Start**: `python debug_streamlit.py`
2. **Attach**: Press F5 in VS Code
3. **Debug**: Set breakpoints and step through code
4. **Inspect**: View variables, session state, and API calls
5. **Fix**: Make changes and restart the debug session

The app will be available at **http://localhost:8501** (or 8502 if 8501 is busy) with full debugging support!