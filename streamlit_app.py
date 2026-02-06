"""Streamlit UI for the Document QA RAG Agent."""

import streamlit as st
import time
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

# Import our utility functions
from src.ui_utils import APIClient, HealthChecker, format_file_size, format_timestamp, clean_document_name, validate_pdf_file
from src.models import ProcessingStatus
from src.debug_utils import debug_print, debug_exception, debug_session_state, debug_api_call, setup_debug_environment, DebugContext

# Debug configuration
DEBUG_MODE = setup_debug_environment()

if DEBUG_MODE:
    try:
        import debugpy
        if not debugpy.is_client_connected():
            debug_print("Starting debug server on port 5678...")
            debugpy.listen(("localhost", 5678))
            debug_print("Waiting for debugger to attach...")
            debugpy.wait_for_client()
            debug_print("Debugger attached successfully!")
    except ImportError:
        print("⚠️ debugpy not installed. Install with: pip install debugpy")
    except Exception as e:
        debug_exception(e, "Debug setup")

# Configure Streamlit page
st.set_page_config(
    page_title="Document QA RAG Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration
MAX_FILE_SIZE_MB = 50
MAX_QUESTION_LENGTH = 1000


@dataclass
class ConversationEntry:
    """Represents a conversation entry."""
    question: str
    answer: str
    source_references: List[Dict]
    timestamp: datetime
    confidence_score: float


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    with DebugContext("initialize_session_state"):
        if "conversation_history" not in st.session_state:
            st.session_state.conversation_history = []
        
        if "uploaded_documents" not in st.session_state:
            st.session_state.uploaded_documents = []
        
        if "processing_status" not in st.session_state:
            st.session_state.processing_status = ProcessingStatus.IDLE
        
        if "current_question" not in st.session_state:
            st.session_state.current_question = ""
        
        if "api_client" not in st.session_state:
            st.session_state.api_client = APIClient()
        
        if "health_checker" not in st.session_state:
            st.session_state.health_checker = HealthChecker()
        
        if DEBUG_MODE:
            debug_session_state(st.session_state)


def format_source_references(source_references: List[Dict]) -> str:
    """Format source references for display."""
    if not source_references:
        return "No sources available"
    
    formatted_refs = []
    for ref in source_references:
        doc_name = ref.get("document_name", "Unknown document")
        page_num = ref.get("page_number", "Unknown page")
        clean_doc_name = clean_document_name(doc_name)
        formatted_refs.append(f"📄 **{clean_doc_name}** (Page {page_num})")
    
    return "\n".join(formatted_refs)


def display_conversation_history():
    """Display the conversation history."""
    if not st.session_state.conversation_history:
        st.info("💬 No conversation history yet. Upload a document and ask a question to get started!")
        return
    
    st.subheader("💬 Conversation History")
    
    # Display conversations in reverse chronological order (newest first)
    for i, entry in enumerate(reversed(st.session_state.conversation_history)):
        with st.expander(
            f"Q: {entry.question[:80]}{'...' if len(entry.question) > 80 else ''}", 
            expanded=(i == 0)
        ):
            st.markdown(f"**Question:** {entry.question}")
            st.markdown(f"**Answer:** {entry.answer}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Confidence", f"{entry.confidence_score:.2f}")
            with col2:
                st.caption(f"Asked: {format_timestamp(entry.timestamp)}")
            
            st.markdown("**Sources:**")
            st.markdown(format_source_references(entry.source_references))


def display_document_management():
    """Display document management interface."""
    st.subheader("📁 Document Management")
    
    if not st.session_state.uploaded_documents:
        st.info("📄 No documents uploaded yet.")
        return
    
    st.success(f"✅ **{len(st.session_state.uploaded_documents)}** document(s) processed")
    
    with st.expander("View uploaded documents", expanded=False):
        for doc in st.session_state.uploaded_documents:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                display_name = clean_document_name(doc["name"])
                st.write(f"📄 **{display_name}**")
                if "chunks_created" in doc:
                    st.caption(f"Created {doc['chunks_created']} text chunks")
            
            with col2:
                st.caption(doc["uploaded_at"])


def display_processing_status():
    """Display current processing status."""
    status = st.session_state.processing_status
    
    if status == ProcessingStatus.IDLE:
        return
    elif status == ProcessingStatus.UPLOADING:
        st.info("📤 Uploading document...")
        st.progress(0.3)
    elif status == ProcessingStatus.PROCESSING:
        st.info("⚙️ Processing document...")
        st.progress(0.7)
    elif status == ProcessingStatus.QUERYING:
        st.info("🔍 Searching for answer...")
        st.progress(0.5)
    elif status == ProcessingStatus.ERROR:
        st.error("❌ An error occurred during processing")


def display_api_status():
    """Display API health status in sidebar."""
    st.sidebar.subheader("🔧 System Status")
    
    # Get health status (cached)
    health_result = st.session_state.health_checker.get_health_status()
    
    if health_result["success"]:
        health_data = health_result["data"]
        
        if health_data["status"] == "healthy":
            st.sidebar.success("✅ System Online")
            
            # Display component status if available
            if "components" in health_data:
                components = health_data["components"]
                
                with st.sidebar.expander("Component Details", expanded=False):
                    for component, status in components.items():
                        if component == "documents_indexed":
                            st.write(f"📚 Documents: **{status}**")
                        elif "ready" in str(status):
                            provider = status.split("(")[-1].rstrip(")") if "(" in str(status) else ""
                            component_name = component.replace("_", " ").title()
                            if provider:
                                st.write(f"✅ {component_name}: **{provider}**")
                            else:
                                st.write(f"✅ {component_name}")
                        elif "error" in str(status):
                            st.write(f"❌ {component.replace('_', ' ').title()}")
        else:
            st.sidebar.error("❌ System Offline")
            if "components" in health_data:
                with st.sidebar.expander("Error Details", expanded=True):
                    for component, status in health_data["components"].items():
                        if "error" in str(status):
                            st.write(f"❌ {component}: {status}")
    else:
        st.sidebar.error("❌ Backend Unavailable")
        st.sidebar.write(f"Error: {health_result['error']}")
        st.sidebar.info("💡 Make sure the FastAPI server is running on http://localhost:8000")


def handle_document_upload(uploaded_file):
    """Handle document upload process."""
    # Validate file size
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    if file_size_mb > MAX_FILE_SIZE_MB:
        st.error(f"❌ File size ({file_size_mb:.1f}MB) exceeds the maximum limit of {MAX_FILE_SIZE_MB}MB")
        return False
    
    # Validate PDF content
    validation_result = validate_pdf_file(uploaded_file.getvalue())
    if not validation_result["valid"]:
        st.error(f"❌ {validation_result['error']}")
        return False
    
    # Display file info and upload button
    col_upload, col_info = st.columns([1, 2])
    
    with col_info:
        st.write(f"📄 **{uploaded_file.name}**")
        st.caption(f"Size: {format_file_size(len(uploaded_file.getvalue()))}")
    
    with col_upload:
        if st.button("Upload & Process", type="primary", key="upload_btn"):
            return process_upload(uploaded_file)
    
    return False


def process_upload(uploaded_file):
    """Process the document upload."""
    st.session_state.processing_status = ProcessingStatus.UPLOADING
    st.rerun()


def handle_upload_processing(uploaded_file):
    """Handle the actual upload processing."""
    with DebugContext("handle_upload_processing"):
        st.session_state.processing_status = ProcessingStatus.PROCESSING
        
        with st.spinner("Processing document..."):
            try:
                debug_print(f"Uploading file: {uploaded_file.name}")
                result = st.session_state.api_client.upload_document(
                    uploaded_file.name, 
                    uploaded_file.getvalue()
                )
                debug_api_call("upload_document", {"filename": uploaded_file.name}, result)
            except Exception as e:
                debug_exception(e, "upload_document")
                result = {"success": False, "error": f"Upload failed: {str(e)}"}
        
        if result["success"]:
            st.success("✅ Document uploaded and processed successfully!")
            
            # Add to uploaded documents list
            doc_info = {
                "name": uploaded_file.name,
                "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "chunks_created": result["data"].get("chunks_created", 0)
            }
            st.session_state.uploaded_documents.append(doc_info)
            debug_print(f"Added document to session: {doc_info}")
            
            # Force refresh health status to update document count
            st.session_state.health_checker.get_health_status(force_refresh=True)
            
            st.session_state.processing_status = ProcessingStatus.IDLE
            time.sleep(1)  # Brief pause to show success message
            st.rerun()
        else:
            st.error(f"❌ Upload failed: {result['error']}")
            st.session_state.processing_status = ProcessingStatus.ERROR
            time.sleep(3)  # Show error for longer
            st.session_state.processing_status = ProcessingStatus.IDLE
            st.rerun()


def handle_question_submission(question: str, top_k: int):
    """Handle question submission and processing."""
    with DebugContext("handle_question_submission"):
        st.session_state.processing_status = ProcessingStatus.QUERYING
        st.session_state.current_question = question
        
        with st.spinner("Searching for answer..."):
            try:
                debug_print(f"Querying: {question[:50]}... (top_k={top_k})")
                result = st.session_state.api_client.query_documents(question.strip(), top_k)
                debug_api_call("query_documents", {"question": question[:50], "top_k": top_k}, result)
            except Exception as e:
                debug_exception(e, "query_documents")
                result = {"success": False, "error": f"Query failed: {str(e)}"}
        
        if result["success"]:
            data = result["data"]
            
            # Display answer
            st.subheader("💡 Answer")
            st.markdown(data["answer"])
            
            # Display metrics
            col1, col2 = st.columns(2)
            with col1:
                confidence = data.get("confidence_score", 0.0)
                st.metric("Confidence Score", f"{confidence:.2f}")
            with col2:
                source_count = len(data.get("source_references", []))
                st.metric("Sources Used", source_count)
            
            # Display sources
            if data.get("source_references"):
                st.subheader("📚 Sources")
                sources_text = format_source_references(data["source_references"])
                st.markdown(sources_text)
            
            # Add to conversation history
            entry = ConversationEntry(
                question=question.strip(),
                answer=data["answer"],
                source_references=data.get("source_references", []),
                timestamp=datetime.now(),
                confidence_score=confidence
            )
            st.session_state.conversation_history.append(entry)
            debug_print(f"Added to conversation history: Q={question[:30]}...")
            
            # Clear current question and reset status
            st.session_state.current_question = ""
            st.session_state.processing_status = ProcessingStatus.IDLE
            st.rerun()
        else:
            st.error(f"❌ Query failed: {result['error']}")
            st.session_state.processing_status = ProcessingStatus.ERROR
            time.sleep(3)
            st.session_state.processing_status = ProcessingStatus.IDLE
            st.rerun()


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.title("📚 Document QA RAG Agent")
    st.markdown("Upload PDF documents and ask questions to get accurate, grounded answers.")
    
    # Display processing status
    display_processing_status()
    
    # Main layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Document Upload Section
        st.subheader("📤 Upload Documents")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help=f"Maximum file size: {MAX_FILE_SIZE_MB}MB"
        )
        
        # Handle upload processing if in progress
        if (st.session_state.processing_status == ProcessingStatus.UPLOADING and
            uploaded_file is not None):
            handle_upload_processing(uploaded_file)
        elif uploaded_file is not None:
            handle_document_upload(uploaded_file)
        
        st.markdown("---")
        
        # Question Input Section
        st.subheader("❓ Ask Questions")
        
        # Check if documents are available
        if not st.session_state.uploaded_documents:
            st.info("📝 Please upload a document first before asking questions.")
            question_disabled = True
        else:
            question_disabled = False
        
        question = st.text_area(
            "Enter your question:",
            value=st.session_state.current_question,
            height=100,
            disabled=question_disabled,
            max_chars=MAX_QUESTION_LENGTH,

            placeholder="What is the main topic of the document?" if not question_disabled else "Upload a document first...",
            help=f"Maximum {MAX_QUESTION_LENGTH} characters"
        )
        
        col_ask, col_settings = st.columns([1, 1])
        
        with col_ask:
            ask_button = st.button(
                "Ask Question", 
                type="primary", 
                disabled=question_disabled or not question.strip(),
                key="ask_btn"
            )
        
        with col_settings:
            top_k = st.selectbox(
                "Number of sources to retrieve:",
                options=[3, 5, 7, 10],
                index=1,
                disabled=question_disabled,
                help="More sources may provide better context but slower responses"
            )
        
        # Handle question submission
        if ask_button and question.strip():
            handle_question_submission(question, top_k)
    
    with col2:
        # Right column content
        display_document_management()
        st.markdown("---")
        display_conversation_history()
    
    # Sidebar
    with st.sidebar:
        display_api_status()
        
        st.markdown("---")
        
        st.subheader("ℹ️ About")
        st.markdown("""
        This Document QA RAG Agent uses **Retrieval-Augmented Generation** to provide 
        accurate answers based on your uploaded documents.
        
        **Features:**
        - 📄 PDF document processing
        - 🔍 Semantic search
        - 💡 Grounded answers
        - 📚 Source references
        - 💬 Conversation history
        - 🔧 Real-time status monitoring
        """)
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🗑️ Clear History", help="Clear conversation history"):
                st.session_state.conversation_history = []
                st.session_state.current_question = ""
                st.rerun()
        
        with col2:
            if st.button("🔄 Refresh", help="Refresh system status"):
                st.session_state.health_checker.get_health_status(force_refresh=True)
                st.rerun()
        
        # Debug info (only show if there are issues)
        health_result = st.session_state.health_checker.get_health_status()
        if not health_result["success"]:
            with st.expander("🔧 Troubleshooting", expanded=False):
                st.markdown("""
                **Common Issues:**
                
                1. **Backend not running**: Start the FastAPI server with:
                   ```bash
                   python -m uvicorn src.app:app --reload
                   ```
                
                2. **Port conflicts**: Make sure port 8000 is available
                
                3. **Dependencies**: Install with:
                   ```bash
                   pip install -e .
                   ```
                """)


if __name__ == "__main__":
    main()