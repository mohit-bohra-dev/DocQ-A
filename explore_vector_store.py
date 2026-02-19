"""
Interactive Vector Store Explorer

A simple command-line tool to explore your vector store interactively.
"""

import json
import numpy as np
import faiss
from collections import Counter, defaultdict
from datetime import datetime


class VectorStoreExplorer:
    """Interactive explorer for FAISS vector store."""
    
    def __init__(self, vector_store_path="src/data/vector_store", metadata_path="src/data/metadata.json"):
        self.vector_store_path = vector_store_path
        self.metadata_path = metadata_path
        self.metadata = None
        self.index = None
        
    def load_data(self):
        """Load vector store and metadata."""
        print("Loading data...")
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.metadata = data.get('metadata_store', {})
        
        self.index = faiss.read_index(self.vector_store_path)
        print(f"✓ Loaded {len(self.metadata)} chunks from {self.index.ntotal} vectors\n")
        
    def show_summary(self):
        """Display summary statistics."""
        print("\n" + "="*70)
        print("VECTOR STORE SUMMARY")
        print("="*70)
        
        doc_names = [m['document_name'] for m in self.metadata.values()]
        doc_counter = Counter(doc_names)
        
        print(f"\n📊 Overview:")
        print(f"   Total Documents: {len(doc_counter)}")
        print(f"   Total Chunks: {len(self.metadata)}")
        print(f"   Vector Dimension: {self.index.d}")
        
        print(f"\n📄 Documents:")
        for idx, (doc, count) in enumerate(doc_counter.most_common(), 1):
            print(f"   {idx}. {doc}")
            print(f"      └─ {count} chunks")
        
        print("="*70 + "\n")
    
    def show_document_details(self, doc_name):
        """Show detailed information about a specific document."""
        chunks = [m for m in self.metadata.values() if m['document_name'] == doc_name]
        
        if not chunks:
            print(f"❌ Document '{doc_name}' not found")
            return
        
        print(f"\n{'='*70}")
        print(f"DOCUMENT: {doc_name}")
        print(f"{'='*70}")
        
        pages = sorted(set(c['page_number'] for c in chunks))
        print(f"\n📄 Total Chunks: {len(chunks)}")
        print(f"📖 Pages: {len(pages)} (Pages {min(pages)} - {max(pages)})")
        print(f"📅 Created: {chunks[0]['created_at']}")
        
        # Chunks per page
        page_dist = Counter(c['page_number'] for c in chunks)
        print(f"\n📊 Chunks per Page:")
        for page in sorted(page_dist.keys()):
            count = page_dist[page]
            bar = "█" * min(count, 50)
            print(f"   Page {page:3d}: {bar} ({count})")
        
        print("="*70 + "\n")
    
    def search_similar_chunks(self, chunk_idx, k=5):
        """Find similar chunks to a given chunk."""
        if str(chunk_idx) not in self.metadata:
            print(f"❌ Chunk {chunk_idx} not found")
            return
        
        query_meta = self.metadata[str(chunk_idx)]
        query_vector = np.zeros((1, self.index.d), dtype=np.float32)
        query_vector[0] = self.index.reconstruct(int(chunk_idx))
        
        distances, indices = self.index.search(query_vector, k+1)
        
        print(f"\n{'='*70}")
        print(f"SIMILAR CHUNKS TO: Chunk {chunk_idx}")
        print(f"{'='*70}")
        
        print(f"\n🔍 Query Chunk:")
        print(f"   Document: {query_meta['document_name']}")
        print(f"   Page: {query_meta['page_number']}")
        print(f"   Chunk Index: {query_meta['chunk_index']}")
        
        print(f"\n🎯 Top {k} Most Similar Chunks:")
        for rank, (idx, dist) in enumerate(zip(indices[0][1:k+1], distances[0][1:k+1]), 1):
            meta = self.metadata[str(idx)]
            similarity = 1 / (1 + dist)
            
            print(f"\n   {rank}. Chunk {idx} (Similarity: {similarity:.4f})")
            print(f"      Document: {meta['document_name']}")
            print(f"      Page: {meta['page_number']}, Chunk: {meta['chunk_index']}")
        
        print("="*70 + "\n")
    
    def list_documents(self):
        """List all documents with indices."""
        doc_names = sorted(set(m['document_name'] for m in self.metadata.values()))
        print(f"\n📚 Available Documents ({len(doc_names)}):")
        for idx, doc in enumerate(doc_names, 1):
            print(f"   {idx}. {doc}")
        print()
        return doc_names
    
    def interactive_menu(self):
        """Display interactive menu."""
        while True:
            print("\n" + "="*70)
            print("VECTOR STORE EXPLORER - MENU")
            print("="*70)
            print("\n1. Show Summary")
            print("2. List All Documents")
            print("3. Show Document Details")
            print("4. Find Similar Chunks")
            print("5. Search by Document and Page")
            print("6. Random Chunk Analysis")
            print("0. Exit")
            print("\n" + "-"*70)
            
            choice = input("\nEnter your choice: ").strip()
            
            if choice == '0':
                print("\n👋 Goodbye!\n")
                break
            elif choice == '1':
                self.show_summary()
            elif choice == '2':
                self.list_documents()
            elif choice == '3':
                docs = self.list_documents()
                doc_input = input("\nEnter document name or number: ").strip()
                try:
                    doc_idx = int(doc_input) - 1
                    if 0 <= doc_idx < len(docs):
                        self.show_document_details(docs[doc_idx])
                    else:
                        print("❌ Invalid document number")
                except ValueError:
                    self.show_document_details(doc_input)
            elif choice == '4':
                chunk_idx = input("\nEnter chunk index: ").strip()
                try:
                    k = input("Number of similar chunks to show (default 5): ").strip()
                    k = int(k) if k else 5
                    self.search_similar_chunks(int(chunk_idx), k)
                except ValueError:
                    print("❌ Invalid input")
            elif choice == '5':
                docs = self.list_documents()
                doc_input = input("\nEnter document name or number: ").strip()
                try:
                    doc_idx = int(doc_input) - 1
                    doc_name = docs[doc_idx] if 0 <= doc_idx < len(docs) else doc_input
                except ValueError:
                    doc_name = doc_input
                
                page_num = input("Enter page number: ").strip()
                try:
                    self.show_chunks_on_page(doc_name, int(page_num))
                except ValueError:
                    print("❌ Invalid page number")
            elif choice == '6':
                import random
                chunk_idx = random.randint(0, len(self.metadata) - 1)
                print(f"\n🎲 Randomly selected chunk: {chunk_idx}")
                self.search_similar_chunks(chunk_idx, k=5)
            else:
                print("❌ Invalid choice. Please try again.")
    
    def show_chunks_on_page(self, doc_name, page_num):
        """Show all chunks on a specific page."""
        chunks = [
            (idx, m) for idx, m in self.metadata.items()
            if m['document_name'] == doc_name and m['page_number'] == page_num
        ]
        
        if not chunks:
            print(f"\n❌ No chunks found for '{doc_name}' on page {page_num}")
            return
        
        print(f"\n{'='*70}")
        print(f"CHUNKS: {doc_name} - Page {page_num}")
        print(f"{'='*70}")
        
        print(f"\n📄 Found {len(chunks)} chunk(s):")
        for idx, meta in sorted(chunks, key=lambda x: x[1]['chunk_index']):
            print(f"\n   Chunk {idx}:")
            print(f"      Chunk Index: {meta['chunk_index']}")
            print(f"      Chunk ID: {meta['chunk_id']}")
            print(f"      Created: {meta['created_at']}")
        
        print("="*70 + "\n")


def main():
    """Main execution function."""
    print("\n" + "="*70)
    print("🔍 VECTOR STORE EXPLORER")
    print("="*70 + "\n")
    
    explorer = VectorStoreExplorer()
    
    try:
        explorer.load_data()
        explorer.interactive_menu()
    except FileNotFoundError as e:
        print(f"\n❌ Error: Could not find required files.")
        print(f"Details: {e}")
        print("\nMake sure you have:")
        print("  - src/data/vector_store (FAISS index file)")
        print("  - src/data/metadata.json (metadata file)")
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
