"""
Vector Store Visualization Tool

This script provides multiple ways to visualize and explore the FAISS vector store:
1. Document statistics and distribution
2. 2D/3D visualization of embeddings using dimensionality reduction
3. Similarity heatmaps
4. Cluster analysis
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import faiss

# Optional imports for advanced visualizations
try:
    from sklearn.manifold import TSNE
    from sklearn.decomposition import PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. Install with: pip install scikit-learn")

try:
    import umap
    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    print("Info: UMAP not available. Install with: pip install umap-learn for better visualizations")


class VectorStoreVisualizer:
    """Visualize and analyze FAISS vector store."""
    
    def __init__(self, vector_store_path="src/data/vector_store", metadata_path="src/data/metadata.json"):
        self.vector_store_path = vector_store_path
        self.metadata_path = metadata_path
        self.metadata = None
        self.index = None
        self.vectors = None
        
    def load_data(self):
        """Load vector store and metadata."""
        print("Loading metadata...")
        with open(self.metadata_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.metadata = data.get('metadata_store', {})
        
        print(f"Loaded {len(self.metadata)} metadata entries")
        
        print("Loading FAISS index...")
        self.index = faiss.read_index(self.vector_store_path)
        print(f"Index contains {self.index.ntotal} vectors")
        print(f"Vector dimension: {self.index.d}")
        
        # Extract vectors from index
        self.vectors = np.zeros((self.index.ntotal, self.index.d), dtype=np.float32)
        for i in range(self.index.ntotal):
            self.vectors[i] = self.index.reconstruct(int(i))
        
        return True
    
    def print_statistics(self):
        """Print basic statistics about the vector store."""
        print("\n" + "="*60)
        print("VECTOR STORE STATISTICS")
        print("="*60)
        
        # Document statistics
        doc_names = [m['document_name'] for m in self.metadata.values()]
        doc_counter = Counter(doc_names)
        
        print(f"\nTotal Documents: {len(doc_counter)}")
        print(f"Total Chunks: {len(self.metadata)}")
        print(f"Vector Dimension: {self.index.d}")
        
        print("\nDocument Distribution:")
        for doc, count in doc_counter.most_common():
            print(f"  {doc}: {count} chunks")
        
        # Page statistics
        pages_per_doc = defaultdict(set)
        for m in self.metadata.values():
            pages_per_doc[m['document_name']].add(m['page_number'])
        
        print("\nPages per Document:")
        for doc, pages in pages_per_doc.items():
            print(f"  {doc}: {len(pages)} pages")
        
        # Temporal statistics
        if self.metadata:
            dates = [datetime.fromisoformat(m['created_at']) for m in self.metadata.values()]
            print(f"\nFirst upload: {min(dates)}")
            print(f"Last upload: {max(dates)}")
        
        print("="*60 + "\n")
    
    def plot_document_distribution(self, save_path="visualizations/document_distribution.png"):
        """Plot document chunk distribution."""
        Path(save_path).parent.mkdir(exist_ok=True)
        
        doc_names = [m['document_name'] for m in self.metadata.values()]
        doc_counter = Counter(doc_names)
        
        plt.figure(figsize=(12, 6))
        docs, counts = zip(*doc_counter.most_common())
        
        plt.bar(range(len(docs)), counts, color='steelblue', alpha=0.8)
        plt.xlabel('Document', fontsize=12)
        plt.ylabel('Number of Chunks', fontsize=12)
        plt.title('Document Chunk Distribution', fontsize=14, fontweight='bold')
        plt.xticks(range(len(docs)), docs, rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")
        plt.close()
    
    def plot_page_distribution(self, save_path="visualizations/page_distribution.png"):
        """Plot page distribution across documents."""
        Path(save_path).parent.mkdir(exist_ok=True)
        
        pages_per_doc = defaultdict(list)
        for m in self.metadata.values():
            pages_per_doc[m['document_name']].append(m['page_number'])
        
        fig, axes = plt.subplots(len(pages_per_doc), 1, figsize=(12, 4*len(pages_per_doc)))
        if len(pages_per_doc) == 1:
            axes = [axes]
        
        for idx, (doc, pages) in enumerate(pages_per_doc.items()):
            page_counter = Counter(pages)
            sorted_pages = sorted(page_counter.items())
            page_nums, counts = zip(*sorted_pages)
            
            axes[idx].bar(page_nums, counts, color='coral', alpha=0.7)
            axes[idx].set_xlabel('Page Number', fontsize=10)
            axes[idx].set_ylabel('Chunks', fontsize=10)
            axes[idx].set_title(f'{doc}', fontsize=11, fontweight='bold')
            axes[idx].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")
        plt.close()
    
    def plot_embeddings_2d(self, method='tsne', save_path="visualizations/embeddings_2d.png"):
        """Visualize embeddings in 2D using dimensionality reduction."""
        if not SKLEARN_AVAILABLE:
            print("Skipping 2D visualization - scikit-learn not available")
            return
        
        Path(save_path).parent.mkdir(exist_ok=True)
        
        print(f"Reducing dimensions using {method.upper()}...")
        
        if method == 'tsne':
            reducer = TSNE(n_components=2, random_state=42, perplexity=min(30, len(self.vectors)-1))
        elif method == 'pca':
            reducer = PCA(n_components=2, random_state=42)
        elif method == 'umap' and UMAP_AVAILABLE:
            reducer = umap.UMAP(n_components=2, random_state=42)
        else:
            print(f"Method {method} not available, using PCA")
            reducer = PCA(n_components=2, random_state=42)
        
        embeddings_2d = reducer.fit_transform(self.vectors)
        
        # Color by document
        doc_names = [self.metadata[str(i)]['document_name'] for i in range(len(self.metadata))]
        unique_docs = list(set(doc_names))
        color_map = {doc: idx for idx, doc in enumerate(unique_docs)}
        colors = [color_map[doc] for doc in doc_names]
        
        plt.figure(figsize=(14, 10))
        scatter = plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], 
                            c=colors, cmap='tab10', alpha=0.6, s=50)
        
        # Create legend
        handles = [plt.Line2D([0], [0], marker='o', color='w', 
                             markerfacecolor=plt.cm.tab10(color_map[doc]/10), 
                             markersize=10, label=doc) 
                  for doc in unique_docs]
        plt.legend(handles=handles, loc='best', fontsize=9)
        
        plt.xlabel(f'{method.upper()} Component 1', fontsize=12)
        plt.ylabel(f'{method.upper()} Component 2', fontsize=12)
        plt.title(f'2D Embedding Visualization ({method.upper()})', fontsize=14, fontweight='bold')
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")
        plt.close()
    
    def plot_similarity_heatmap(self, sample_size=50, save_path="visualizations/similarity_heatmap.png"):
        """Plot similarity heatmap for a sample of vectors."""
        Path(save_path).parent.mkdir(exist_ok=True)
        
        # Sample vectors if too many
        if len(self.vectors) > sample_size:
            indices = np.random.choice(len(self.vectors), sample_size, replace=False)
            sample_vectors = self.vectors[indices]
            sample_labels = [f"{self.metadata[str(i)]['document_name'][:20]}...\nChunk {i}" 
                           for i in indices]
        else:
            sample_vectors = self.vectors
            sample_labels = [f"{self.metadata[str(i)]['document_name'][:20]}...\nChunk {i}" 
                           for i in range(len(self.vectors))]
        
        # Compute cosine similarity
        print("Computing similarity matrix...")
        norms = np.linalg.norm(sample_vectors, axis=1, keepdims=True)
        normalized_vectors = sample_vectors / (norms + 1e-8)
        similarity_matrix = np.dot(normalized_vectors, normalized_vectors.T)
        
        plt.figure(figsize=(14, 12))
        sns.heatmap(similarity_matrix, cmap='coolwarm', center=0, 
                   square=True, linewidths=0.5, cbar_kws={"shrink": 0.8},
                   vmin=-1, vmax=1)
        plt.title(f'Cosine Similarity Heatmap (Sample of {len(sample_vectors)} chunks)', 
                 fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")
        plt.close()
    
    def plot_vector_statistics(self, save_path="visualizations/vector_statistics.png"):
        """Plot statistical properties of vectors."""
        Path(save_path).parent.mkdir(exist_ok=True)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # Vector norms
        norms = np.linalg.norm(self.vectors, axis=1)
        axes[0, 0].hist(norms, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        axes[0, 0].set_xlabel('L2 Norm', fontsize=10)
        axes[0, 0].set_ylabel('Frequency', fontsize=10)
        axes[0, 0].set_title('Distribution of Vector Norms', fontsize=11, fontweight='bold')
        axes[0, 0].grid(alpha=0.3)
        
        # Mean values per dimension
        mean_values = np.mean(self.vectors, axis=0)
        axes[0, 1].plot(mean_values, color='green', alpha=0.7)
        axes[0, 1].set_xlabel('Dimension', fontsize=10)
        axes[0, 1].set_ylabel('Mean Value', fontsize=10)
        axes[0, 1].set_title('Mean Values Across Dimensions', fontsize=11, fontweight='bold')
        axes[0, 1].grid(alpha=0.3)
        
        # Standard deviation per dimension
        std_values = np.std(self.vectors, axis=0)
        axes[1, 0].plot(std_values, color='orange', alpha=0.7)
        axes[1, 0].set_xlabel('Dimension', fontsize=10)
        axes[1, 0].set_ylabel('Standard Deviation', fontsize=10)
        axes[1, 0].set_title('Std Dev Across Dimensions', fontsize=11, fontweight='bold')
        axes[1, 0].grid(alpha=0.3)
        
        # Distribution of first dimension values
        axes[1, 1].hist(self.vectors[:, 0], bins=50, color='purple', edgecolor='black', alpha=0.7)
        axes[1, 1].set_xlabel('Value', fontsize=10)
        axes[1, 1].set_ylabel('Frequency', fontsize=10)
        axes[1, 1].set_title('Distribution of First Dimension', fontsize=11, fontweight='bold')
        axes[1, 1].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")
        plt.close()
    
    def analyze_nearest_neighbors(self, chunk_idx=0, k=5):
        """Analyze nearest neighbors for a specific chunk."""
        print(f"\n{'='*60}")
        print(f"NEAREST NEIGHBORS ANALYSIS - Chunk {chunk_idx}")
        print(f"{'='*60}")
        
        query_vector = self.vectors[chunk_idx:chunk_idx+1]
        distances, indices = self.index.search(query_vector, k+1)
        
        query_meta = self.metadata[str(chunk_idx)]
        print(f"\nQuery Chunk:")
        print(f"  Document: {query_meta['document_name']}")
        print(f"  Page: {query_meta['page_number']}")
        print(f"  Chunk Index: {query_meta['chunk_index']}")
        
        print(f"\nTop {k} Nearest Neighbors:")
        for rank, (idx, dist) in enumerate(zip(indices[0][1:k+1], distances[0][1:k+1]), 1):
            meta = self.metadata[str(idx)]
            similarity = 1 / (1 + dist)  # Convert distance to similarity
            print(f"\n  {rank}. Chunk {idx} (Similarity: {similarity:.4f})")
            print(f"     Document: {meta['document_name']}")
            print(f"     Page: {meta['page_number']}")
            print(f"     Chunk Index: {meta['chunk_index']}")
        
        print(f"{'='*60}\n")
    
    def generate_all_visualizations(self):
        """Generate all available visualizations."""
        print("\nGenerating all visualizations...")
        print("-" * 60)
        
        self.print_statistics()
        self.plot_document_distribution()
        self.plot_page_distribution()
        self.plot_vector_statistics()
        self.plot_similarity_heatmap()
        
        if SKLEARN_AVAILABLE:
            self.plot_embeddings_2d(method='pca')
            self.plot_embeddings_2d(method='tsne')
            
            if UMAP_AVAILABLE:
                self.plot_embeddings_2d(method='umap')
        
        # Analyze a few sample chunks
        sample_indices = np.random.choice(len(self.vectors), min(3, len(self.vectors)), replace=False)
        for idx in sample_indices:
            self.analyze_nearest_neighbors(chunk_idx=int(idx), k=5)
        
        print("\n" + "="*60)
        print("VISUALIZATION COMPLETE!")
        print("="*60)
        print("\nAll visualizations saved to 'visualizations/' directory")
        print("\nGenerated files:")
        print("  - document_distribution.png")
        print("  - page_distribution.png")
        print("  - vector_statistics.png")
        print("  - similarity_heatmap.png")
        if SKLEARN_AVAILABLE:
            print("  - embeddings_2d.png (PCA, t-SNE" + (", UMAP" if UMAP_AVAILABLE else "") + ")")


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("VECTOR STORE VISUALIZATION TOOL")
    print("="*60 + "\n")
    
    visualizer = VectorStoreVisualizer()
    
    try:
        visualizer.load_data()
        visualizer.generate_all_visualizations()
    except FileNotFoundError as e:
        print(f"\nError: Could not find required files.")
        print(f"Details: {e}")
        print("\nMake sure you have:")
        print("  - src/data/vector_store (FAISS index file)")
        print("  - src/data/metadata.json (metadata file)")
    except Exception as e:
        print(f"\nError during visualization: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
