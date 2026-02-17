"""FAISS-based vector store implementation for the RAG system."""

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import numpy as np
import faiss
from faiss import IndexFlatIP

try:
    from .interfaces import VectorStore
    from .models import SearchResult, ChunkMetadata, TextChunk
except ImportError:
    from interfaces import VectorStore
    from models import SearchResult, ChunkMetadata, TextChunk


class FAISSVectorStore(VectorStore):
    """FAISS-based implementation of the VectorStore interface."""
    index: IndexFlatIP | IndexFlatIP

    def __init__(self, dimension: int, index_path: str = "data/faiss_index", 
                 metadata_path: str = "data/metadata.json"):
        """
        Initialize the FAISS vector store.
        
        Args:
            dimension: Dimension of the embeddings
            index_path: Path to save/load the FAISS index
            metadata_path: Path to save/load the metadata JSON file
        """
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = metadata_path
        
        # Initialize FAISS index (using IndexFlatIP for inner product similarity)
        self.index = faiss.IndexFlatIP(dimension)
        
        # Store metadata separately
        self.metadata_store: Dict[int, ChunkMetadata] = {}
        self.chunks_store: Dict[int, TextChunk] = {}
        self.next_id = 0
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    
    def add_embeddings(self, embeddings: List[List[float]], metadata: List[ChunkMetadata]) -> None:
        """
        Add embeddings with metadata to the store.
        
        Args:
            embeddings: List of embedding vectors
            metadata: List of metadata objects corresponding to embeddings
        """
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings must match number of metadata items")
        
        if not embeddings:
            return
        
        # Convert embeddings to numpy array and normalize for cosine similarity
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # Normalize embeddings for cosine similarity using inner product
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        # Avoid division by zero for zero vectors
        norms = np.where(norms == 0, 1, norms)
        embeddings_array = embeddings_array / norms
        
        # Add to FAISS index
        self.index.add(embeddings_array)
        
        # Store metadata and chunks
        for i, meta in enumerate(metadata):
            current_id = self.next_id + i
            self.metadata_store[current_id] = meta
            
            # Create TextChunk from metadata (we'll need to reconstruct this)
            # For now, we'll store a placeholder - this should be passed separately
            # or reconstructed from the metadata
            chunk = TextChunk(
                chunk_id=meta.chunk_id,
                text="",  # Text will be stored separately or reconstructed
                page_number=meta.page_number,
                document_name=meta.document_name,
                start_char=0,  # These would need to be passed in metadata
                end_char=0
            )
            self.chunks_store[current_id] = chunk
        
        self.next_id += len(embeddings)
    
    def add_chunks_with_embeddings(self, chunks: List[TextChunk], 
                                 embeddings: List[List[float]], 
                                 metadata: List[ChunkMetadata]) -> None:
        """
        Add chunks with their embeddings and metadata to the store.
        
        Args:
            chunks: List of text chunks
            embeddings: List of embedding vectors
            metadata: List of metadata objects
        """
        if len(chunks) != len(embeddings) or len(embeddings) != len(metadata):
            raise ValueError("Number of chunks, embeddings, and metadata must match")
        
        if not embeddings:
            return
        
        # Convert embeddings to numpy array and normalize
        embeddings_array = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
        # Avoid division by zero for zero vectors
        norms = np.where(norms == 0, 1, norms)
        embeddings_array = embeddings_array / norms
        
        # Add to FAISS index
        self.index.add(embeddings_array)
        
        # Store metadata and chunks
        for i, (chunk, meta) in enumerate(zip(chunks, metadata)):
            current_id = self.next_id + i
            self.metadata_store[current_id] = meta
            self.chunks_store[current_id] = chunk
        
        self.next_id += len(embeddings)
    
    def search_similar(self, query_embedding: List[float], top_k: int) -> List[SearchResult]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return
            
        Returns:
            List of SearchResult objects ordered by similarity score
        """
        if self.index.ntotal == 0:
            return []
        
        # Normalize query embedding
        query_array = np.array([query_embedding], dtype=np.float32)
        query_norm = np.linalg.norm(query_array)
        if query_norm > 0:
            query_array = query_array / query_norm
        
        # Search in FAISS index
        scores, indices = self.index.search(query_array, min(top_k, self.index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for invalid indices
                continue
                
            if idx in self.metadata_store and idx in self.chunks_store:
                result = SearchResult(
                    chunk=self.chunks_store[idx],
                    similarity_score=float(score),
                    metadata=self.metadata_store[idx]
                )
                results.append(result)
        
        return results
    
    def save_index(self, file_path: Optional[str] = None) -> None:
        """
        Save the index to disk.
        
        Args:
            file_path: Optional custom path to save the index
        """
        index_path = file_path or self.index_path
        metadata_path = file_path.replace('.index', '_metadata.json') if file_path else self.metadata_path
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save metadata and chunks
        save_data = {
            'metadata_store': {
                str(k): {
                    'chunk_id': v.chunk_id,
                    'document_name': v.document_name,
                    'page_number': v.page_number,
                    'chunk_index': v.chunk_index,
                    'created_at': v.created_at.isoformat()
                } for k, v in self.metadata_store.items()
            },
            'chunks_store': {
                str(k): {
                    'chunk_id': v.chunk_id,
                    'text': v.text,
                    'page_number': v.page_number,
                    'document_name': v.document_name,
                    'start_char': v.start_char,
                    'end_char': v.end_char
                } for k, v in self.chunks_store.items()
            },
            'next_id': self.next_id
        }
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
    
    def load_index(self, file_path: Optional[str] = None) -> None:
        """
        Load the index from disk.
        
        Args:
            file_path: Optional custom path to load the index from
        """
        index_path = file_path or self.index_path
        metadata_path = file_path.replace('.index', '_metadata.json') if file_path else self.metadata_path
        
        # Load FAISS index if it exists
        if os.path.exists(index_path):
            self.index = faiss.read_index(index_path)
        else:
            # Initialize empty index if file doesn't exist
            self.index = faiss.IndexFlatIP(self.dimension)
        
        # Load metadata and chunks if they exist
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # Restore metadata store
            self.metadata_store = {}
            for k, v in save_data.get('metadata_store', {}).items():
                from datetime import datetime
                self.metadata_store[int(k)] = ChunkMetadata(
                    chunk_id=v['chunk_id'],
                    document_name=v['document_name'],
                    page_number=v['page_number'],
                    chunk_index=v['chunk_index'],
                    created_at=datetime.fromisoformat(v['created_at'])
                )
            
            # Restore chunks store
            self.chunks_store = {}
            for k, v in save_data.get('chunks_store', {}).items():
                self.chunks_store[int(k)] = TextChunk(
                    chunk_id=v['chunk_id'],
                    text=v['text'],
                    page_number=v['page_number'],
                    document_name=v['document_name'],
                    start_char=v['start_char'],
                    end_char=v['end_char']
                )
            
            self.next_id = save_data.get('next_id', 0)
        else:
            # Initialize empty stores if file doesn't exist
            self.metadata_store = {}
            self.chunks_store = {}
            self.next_id = 0
    
    def get_document_count(self) -> int:
        """
        Get the number of documents in the store.
        
        Returns:
            Number of unique documents
        """
        unique_docs = set()
        for metadata in self.metadata_store.values():
            unique_docs.add(metadata.document_name)
        return len(unique_docs)
    
    def get_chunk_count(self) -> int:
        """
        Get the total number of chunks in the store.
        
        Returns:
            Total number of chunks
        """
        return self.index.ntotal
    
    def clear(self) -> None:
        """Clear all data from the vector store."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata_store.clear()
        self.chunks_store.clear()
        self.next_id = 0
    
    def get_all_document_names(self) -> List[str]:
        """
        Get list of all unique document names in the store.
        
        Returns:
            List of document names
        """
        unique_docs = set()
        for metadata in self.metadata_store.values():
            unique_docs.add(metadata.document_name)
        return sorted(list(unique_docs))
    
    def delete_document_by_name(self, document_name: str) -> int:
        """
        Delete all chunks belonging to a specific document.
        
        Args:
            document_name: Name of the document to delete
            
        Returns:
            Number of chunks deleted
        """
        # Find all indices for this document
        indices_to_delete = []
        for idx, metadata in self.metadata_store.items():
            if metadata.document_name == document_name:
                indices_to_delete.append(idx)
        
        if not indices_to_delete:
            return 0
        
        # Remove from metadata and chunks stores
        for idx in indices_to_delete:
            self.metadata_store.pop(idx, None)
            self.chunks_store.pop(idx, None)
        
        # Rebuild FAISS index without deleted items
        self._rebuild_index()
        
        return len(indices_to_delete)
    
    def _rebuild_index(self) -> None:
        """Rebuild the FAISS index after deletions."""
        # Create new index
        new_index = faiss.IndexFlatIP(self.dimension)
        new_metadata_store = {}
        new_chunks_store = {}
        new_id = 0
        
        # Get all remaining embeddings
        if self.index.ntotal > 0:
            # Reconstruct embeddings from existing index
            all_embeddings = []
            id_mapping = {}
            
            for old_id in sorted(self.metadata_store.keys()):
                if old_id in self.chunks_store:
                    # Get embedding from old index
                    embedding = self.index.reconstruct(old_id)
                    all_embeddings.append(embedding)
                    id_mapping[new_id] = old_id
                    new_id += 1
            
            if all_embeddings:
                # Add to new index
                embeddings_array = np.array(all_embeddings, dtype=np.float32)
                new_index.add(embeddings_array)
                
                # Rebuild metadata and chunks stores with new IDs
                for new_id, old_id in id_mapping.items():
                    new_metadata_store[new_id] = self.metadata_store[old_id]
                    new_chunks_store[new_id] = self.chunks_store[old_id]
        
        # Replace old index and stores
        self.index = new_index
        self.metadata_store = new_metadata_store
        self.chunks_store = new_chunks_store
        self.next_id = new_id
    
    def document_exists(self, document_name: str) -> bool:
        """
        Check if a document with the given name exists in the store.
        
        Args:
            document_name: Name of the document to check
            
        Returns:
            True if document exists, False otherwise
        """
        for metadata in self.metadata_store.values():
            if metadata.document_name == document_name:
                return True
        return False
    
    def get_document_info(self, document_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific document.
        
        Args:
            document_name: Name of the document
            
        Returns:
            Dictionary with document information or None if not found
        """
        chunks_count = 0
        pages = set()
        
        for metadata in self.metadata_store.values():
            if metadata.document_name == document_name:
                chunks_count += 1
                pages.add(metadata.page_number)
        
        if chunks_count == 0:
            return None
        
        return {
            "document_name": document_name,
            "chunks_count": chunks_count,
            "pages_count": len(pages),
            "pages": sorted(list(pages))
        }