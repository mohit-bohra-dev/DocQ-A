"""
Quick Vector Store Visualization

A simple script that shows basic statistics without requiring extra dependencies.
"""

import json
import numpy as np
import faiss
from collections import Counter, defaultdict
from datetime import datetime
import sys
import io

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def load_and_analyze():
    """Load and display basic vector store information."""
    
    print("\n" + "="*70)
    print("🔍 QUICK VECTOR STORE ANALYSIS")
    print("="*70 + "\n")
    
    # Load metadata
    print("Loading metadata...")
    try:
        with open("src/data/metadata.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
            metadata = data.get('metadata_store', {})
        print(f"✓ Loaded {len(metadata)} metadata entries")
    except FileNotFoundError:
        print("❌ Error: src/data/metadata.json not found")
        return
    
    # Load FAISS index
    print("Loading FAISS index...")
    try:
        index = faiss.read_index("src/data/vector_store")
        print(f"✓ Loaded index with {index.ntotal} vectors")
    except Exception as e:
        print(f"❌ Error loading FAISS index: {e}")
        return
    
    # Basic statistics
    print("\n" + "="*70)
    print("📊 STATISTICS")
    print("="*70)
    
    doc_names = [m['document_name'] for m in metadata.values()]
    doc_counter = Counter(doc_names)
    
    print(f"\n📄 Documents: {len(doc_counter)}")
    print(f"📦 Total Chunks: {len(metadata)}")
    print(f"📐 Vector Dimension: {index.d}")
    
    # Document breakdown
    print(f"\n{'='*70}")
    print("📚 DOCUMENT BREAKDOWN")
    print(f"{'='*70}\n")
    
    for idx, (doc, count) in enumerate(doc_counter.most_common(), 1):
        # Get page info
        pages = sorted(set(m['page_number'] for m in metadata.values() 
                          if m['document_name'] == doc))
        
        print(f"{idx}. {doc}")
        print(f"   ├─ Chunks: {count}")
        print(f"   ├─ Pages: {len(pages)} (Page {min(pages)} - {max(pages)})")
        
        # Chunks per page distribution
        chunks_per_page = Counter(m['page_number'] for m in metadata.values() 
                                 if m['document_name'] == doc)
        avg_chunks = sum(chunks_per_page.values()) / len(chunks_per_page)
        print(f"   └─ Avg chunks/page: {avg_chunks:.1f}")
        print()
    
    # Vector analysis
    print(f"{'='*70}")
    print("🔢 VECTOR ANALYSIS")
    print(f"{'='*70}\n")
    
    print("Extracting vectors...")
    vectors = np.zeros((index.ntotal, index.d), dtype=np.float32)
    for i in range(min(index.ntotal, 1000)):  # Sample first 1000 for speed
        vectors[i] = index.reconstruct(int(i))
    
    sample_size = min(index.ntotal, 1000)
    vectors = vectors[:sample_size]
    
    # Compute statistics
    norms = np.linalg.norm(vectors, axis=1)
    mean_vals = np.mean(vectors, axis=0)
    std_vals = np.std(vectors, axis=0)
    
    print(f"Sample Size: {sample_size} vectors")
    print(f"\nVector Norms:")
    print(f"   ├─ Mean: {np.mean(norms):.4f}")
    print(f"   ├─ Std Dev: {np.std(norms):.4f}")
    print(f"   ├─ Min: {np.min(norms):.4f}")
    print(f"   └─ Max: {np.max(norms):.4f}")
    
    print(f"\nDimension Statistics:")
    print(f"   ├─ Mean of means: {np.mean(mean_vals):.4f}")
    print(f"   ├─ Mean of std devs: {np.mean(std_vals):.4f}")
    print(f"   ├─ Most active dim: {np.argmax(std_vals)} (std: {np.max(std_vals):.4f})")
    print(f"   └─ Least active dim: {np.argmin(std_vals)} (std: {np.min(std_vals):.4f})")
    
    # Similarity analysis
    print(f"\n{'='*70}")
    print("🎯 SIMILARITY ANALYSIS")
    print(f"{'='*70}\n")
    
    # Sample a few random chunks and find their neighbors
    sample_indices = np.random.choice(min(index.ntotal, 100), min(3, index.ntotal), replace=False)
    
    for sample_idx in sample_indices:
        query_vector = vectors[sample_idx:sample_idx+1] if sample_idx < len(vectors) else \
                      np.array([index.reconstruct(int(sample_idx))], dtype=np.float32)
        
        distances, indices = index.search(query_vector, 6)
        
        query_meta = metadata[str(sample_idx)]
        print(f"Sample Chunk {sample_idx}:")
        print(f"   Document: {query_meta['document_name']}")
        print(f"   Page: {query_meta['page_number']}")
        
        print(f"   Top 5 Similar Chunks:")
        for rank, (idx, dist) in enumerate(zip(indices[0][1:6], distances[0][1:6]), 1):
            meta = metadata[str(idx)]
            similarity = 1 / (1 + dist)
            same_doc = "✓" if meta['document_name'] == query_meta['document_name'] else "✗"
            print(f"      {rank}. Chunk {idx} (sim: {similarity:.3f}) {same_doc} {meta['document_name'][:30]}")
        print()
    
    # Summary insights
    print(f"{'='*70}")
    print("💡 INSIGHTS")
    print(f"{'='*70}\n")
    
    # Check if chunks from same document are similar
    same_doc_similarities = []
    diff_doc_similarities = []
    
    # Use more samples for better statistics
    insight_samples = np.random.choice(min(index.ntotal, 100), min(20, index.ntotal), replace=False)
    
    for sample_idx in insight_samples:
        query_vector = vectors[sample_idx:sample_idx+1] if sample_idx < len(vectors) else \
                      np.array([index.reconstruct(int(sample_idx))], dtype=np.float32)
        distances, indices = index.search(query_vector, 11)
        
        query_meta = metadata[str(sample_idx)]
        for idx, dist in zip(indices[0][1:11], distances[0][1:11]):
            if str(idx) in metadata:
                meta = metadata[str(idx)]
                similarity = 1 / (1 + dist)
                
                if meta['document_name'] == query_meta['document_name']:
                    same_doc_similarities.append(similarity)
                else:
                    diff_doc_similarities.append(similarity)
    
    if same_doc_similarities:
        avg_same = np.mean(same_doc_similarities)
        print(f"Average similarity within same document: {avg_same:.3f}")
        print(f"  (Based on {len(same_doc_similarities)} comparisons)")
        
        if avg_same > 0.7:
            print("  ✅ Good: Chunks from same document are highly similar")
        elif avg_same > 0.5:
            print("  ⚠️  Moderate: Some similarity within documents")
        else:
            print("  ❌ Low: Chunks from same document are not very similar")
    
    if diff_doc_similarities:
        avg_diff = np.mean(diff_doc_similarities)
        print(f"\nAverage similarity across different documents: {avg_diff:.3f}")
        print(f"  (Based on {len(diff_doc_similarities)} comparisons)")
        
        if same_doc_similarities:
            ratio = avg_same / avg_diff
            print(f"\nSeparation ratio: {ratio:.2f}x")
            if ratio > 1.5:
                print("  ✅ Good: Clear separation between documents")
            elif ratio > 1.2:
                print("  ⚠️  Moderate: Some separation between documents")
            else:
                print("  ❌ Low: Documents are not well separated in embedding space")
    
    if not same_doc_similarities and not diff_doc_similarities:
        print("⚠️  Not enough data for similarity analysis")
    
    print(f"\n{'='*70}")
    print("✨ ANALYSIS COMPLETE")
    print(f"{'='*70}\n")
    
    print("Next steps:")
    print("  1. Run 'python explore_vector_store.py' for interactive exploration")
    print("  2. Run 'python visualize_vector_store.py' for detailed visualizations")
    print("     (requires: pip install -r requirements-viz.txt)")
    print()


if __name__ == "__main__":
    try:
        load_and_analyze()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
