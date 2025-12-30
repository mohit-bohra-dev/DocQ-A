# Document QA RAG Agent

A Document Question-Answering AI Agent using Retrieval-Augmented Generation (RAG) to provide accurate, grounded responses based on uploaded PDF documents.

## Project Structure

```
document-qa-rag-agent/
├── src/
│   ├── __init__.py
│   ├── app.py              # FastAPI application
│   ├── models.py           # Core data models
│   ├── interfaces.py       # Abstract interfaces
│   ├── config.py           # Configuration management
│   └── logging_config.py   # Logging setup
├── tests/
│   └── __init__.py
├── data/                   # Local data storage
├── pyproject.toml          # Project configuration
├── .env.example           # Environment variables template
└── README.md
```

## Setup

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create and activate virtual environment**:
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   uv pip install -e .
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Development

Install development dependencies:
```bash
uv pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Run the application:
```bash
python -m src.app
```

## Architecture

The system follows a modular architecture with clear separation of concerns:

- **FastAPI App**: HTTP API layer and request routing
- **Models**: Core data structures and types
- **Interfaces**: Abstract base classes for components
- **Configuration**: Centralized configuration management
- **Logging**: Structured logging throughout the system

## Next Steps

This is the initial project structure. The following components will be implemented in subsequent tasks:

1. Embedding service and provider abstraction
2. Vector store with FAISS
3. PDF ingestion service
4. Query engine and answer generation
5. Complete API implementation

## Requirements

- Python 3.9+
- uv package manager
- OpenAI API key (for LLM provider)