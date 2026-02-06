# Streamlit UI for Document QA RAG Agent

This is the web-based user interface for the Document QA RAG Agent, built with Streamlit.

## Features

- 📄 **Document Upload**: Upload PDF documents with drag-and-drop interface
- 🔍 **Question Answering**: Ask natural language questions about your documents
- 💬 **Conversation History**: Keep track of all your questions and answers
- 📚 **Source References**: See exactly which parts of your documents were used to generate answers
- 🔧 **System Monitoring**: Real-time status of the backend services
- ⚙️ **Processing Feedback**: Visual indicators for upload and query processing

## Quick Start

### Option 1: Use the Startup Script (Recommended)

```bash
python run_app.py
```

This will start both the FastAPI backend and Streamlit UI automatically.

### Option 2: Manual Startup

1. **Start the FastAPI backend** (in one terminal):
```bash
python -m uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

2. **Start the Streamlit UI** (in another terminal):
```bash
streamlit run streamlit_app.py
```

## Usage

1. **Upload Documents**: 
   - Click "Choose a PDF file" to select your document
   - Maximum file size: 50MB
   - Click "Upload & Process" to process the document

2. **Ask Questions**:
   - Type your question in the text area
   - Adjust the number of sources to retrieve (3-10)
   - Click "Ask Question" to get your answer

3. **View Results**:
   - See the generated answer with confidence score
   - Check source references to verify information
   - Browse conversation history for previous Q&As

4. **Manage Documents**:
   - View uploaded documents in the right panel
   - See processing status and document count

## Configuration

The UI can be configured through the `.streamlit/config.toml` file:

- **Port**: Default is 8501
- **Theme**: Colors and styling
- **Upload limits**: File size restrictions
- **Caching**: Performance settings

## Troubleshooting

### Backend Connection Issues

If you see "Backend Unavailable" in the system status:

1. **Check if FastAPI is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Start the backend**:
   ```bash
   python -m uvicorn src.app:app --reload
   ```

3. **Check for port conflicts**:
   ```bash
   lsof -i :8000  # Check what's using port 8000
   ```

### Upload Issues

- **File too large**: Maximum size is 50MB
- **Invalid PDF**: Make sure the file is a valid PDF
- **Processing timeout**: Large files may take longer to process

### Performance Tips

- **Smaller chunks**: Reduce chunk size for faster processing
- **Fewer sources**: Use 3-5 sources for faster queries
- **Clear history**: Regularly clear conversation history to improve performance

## API Integration

The Streamlit UI communicates with the FastAPI backend through these endpoints:

- `GET /health` - System health check
- `POST /upload` - Document upload and processing
- `POST /query` - Question answering

## Development

### File Structure

```
streamlit_app.py          # Main Streamlit application
src/ui_utils.py          # Utility functions for API communication
.streamlit/config.toml   # Streamlit configuration
run_app.py              # Startup script for both services
```

### Key Components

- **APIClient**: Handles communication with FastAPI backend
- **HealthChecker**: Monitors system status with caching
- **Session State**: Manages conversation history and UI state
- **Error Handling**: User-friendly error messages and recovery

### Adding Features

To add new features to the UI:

1. **Add UI components** in `streamlit_app.py`
2. **Add API methods** in `src/ui_utils.py`
3. **Update session state** management as needed
4. **Test with the backend** API endpoints

## Dependencies

The UI requires these additional packages:
- `streamlit>=1.28.0`
- `requests>=2.31.0`

Install with:
```bash
pip install streamlit requests
```

Or use the full project dependencies:
```bash
pip install -e .
```