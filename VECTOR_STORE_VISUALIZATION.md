# Vector Store Visualization Guide

This guide explains how to visualize and explore your FAISS vector store.

## Available Tools

### 1. `visualize_vector_store.py` - Comprehensive Visualization
Generates multiple visualizations and statistical analyses of your vector store.

**Features:**
- Document and page distribution charts
- 2D/3D embedding visualizations (PCA, t-SNE, UMAP)
- Similarity heatmaps
- Vector statistics (norms, distributions)
- Nearest neighbor analysis

**Usage:**
```bash
python visualize_vector_store.py
```

**Output:**
All visualizations are saved to the `visualizations/` directory:
- `document_distribution.png` - Bar chart showing chunks per document
- `page_distribution.png` - Chunks per page for each document
- `vector_statistics.png` - Statistical properties of embeddings
- `similarity_heatmap.png` - Cosine similarity between chunks
- `embeddings_2d.png` - 2D projection of embeddings (PCA/t-SNE/UMAP)

### 2. `explore_vector_store.py` - Interactive Explorer
Command-line tool for interactive exploration of your vector store.

**Features:**
- Summary statistics
- Document details
- Similar chunk search
- Page-level exploration
- Random chunk analysis

**Usage:**
```bash
python explore_vector_store.py
```

**Interactive Menu:**
1. Show Summary - Overview of all documents and chunks
2. List All Documents - See all indexed documents
3. Show Document Details - Detailed info about a specific document
4. Find Similar Chunks - Find chunks similar to a given chunk
5. Search by Document and Page - View chunks on a specific page
6. Random Chunk Analysis - Analyze a randomly selected chunk

## Installation Requirements

### Basic Requirements (already installed):
```bash
pip install numpy matplotlib seaborn faiss-cpu
```

### Optional (for advanced visualizations):
```bash
# For PCA and t-SNE
pip install scikit-learn

# For UMAP (better than t-SNE for large datasets)
pip install umap-learn
```

## Quick Start

### Option 1: Generate All Visualizations
```bash
python visualize_vector_store.py
```
This will create all visualizations in the `visualizations/` folder.

### Option 2: Interactive Exploration
```bash
python explore_vector_store.py
```
Then follow the interactive menu to explore your data.

## Understanding the Visualizations

### Document Distribution
Shows how many chunks each document has. Useful for understanding:
- Which documents are largest
- Data balance across documents
- Potential chunking issues

### Page Distribution
Shows chunks per page within each document. Helps identify:
- Pages with more/less content
- Chunking patterns
- Potential processing issues

### 2D Embeddings
Projects high-dimensional vectors into 2D space. Look for:
- **Clusters** - Groups of similar chunks (often from same document)
- **Outliers** - Chunks that are very different
- **Document separation** - How well documents are separated in embedding space

**Methods:**
- **PCA** - Fast, linear projection (good for overview)
- **t-SNE** - Better at preserving local structure (shows clusters well)
- **UMAP** - Best of both worlds (fast + good structure preservation)

### Similarity Heatmap
Shows cosine similarity between chunks. Patterns to look for:
- **Diagonal blocks** - Chunks from same document are similar
- **Off-diagonal patterns** - Cross-document similarities
- **Dark regions** - Dissimilar chunks

### Vector Statistics
Shows statistical properties of embeddings:
- **Norms** - Should be relatively consistent
- **Mean/Std per dimension** - Shows which dimensions are most active
- **Distribution** - Should be roughly normal

## Example Workflows

### Workflow 1: Initial Exploration
```bash
# 1. Generate all visualizations
python visualize_vector_store.py

# 2. Review the generated images in visualizations/

# 3. Explore interactively
python explore_vector_store.py
# Choose option 1 (Show Summary)
```

### Workflow 2: Document Analysis
```bash
python explore_vector_store.py
# Choose option 3 (Show Document Details)
# Enter document name
# Review chunk distribution across pages
```

### Workflow 3: Similarity Analysis
```bash
python explore_vector_store.py
# Choose option 4 (Find Similar Chunks)
# Enter a chunk index (e.g., 0, 50, 100)
# Review which chunks are most similar
```

### Workflow 4: Quality Check
```bash
# Generate visualizations
python visualize_vector_store.py

# Check for:
# 1. Balanced document distribution
# 2. Clear clusters in 2D embeddings
# 3. High similarity within documents (heatmap)
# 4. Normal vector statistics
```

## Interpreting Results

### Good Signs ✅
- Documents form distinct clusters in 2D visualization
- Chunks from same document have high similarity (>0.7)
- Vector norms are consistent (low variance)
- Page distribution is relatively uniform

### Potential Issues ⚠️
- All documents mixed together in 2D space → Embeddings may not be discriminative
- Very low similarity between chunks from same document → Chunking may be too aggressive
- Extreme outliers in vector statistics → Potential data quality issues
- Highly uneven page distribution → Chunking strategy may need adjustment

## Customization

### Change Sample Size for Heatmap
Edit `visualize_vector_store.py`:
```python
self.plot_similarity_heatmap(sample_size=100)  # Default is 50
```

### Change Dimensionality Reduction Method
```python
self.plot_embeddings_2d(method='umap')  # Options: 'pca', 'tsne', 'umap'
```

### Analyze Specific Chunks
```python
visualizer.analyze_nearest_neighbors(chunk_idx=42, k=10)
```

## Troubleshooting

### "scikit-learn not available"
```bash
pip install scikit-learn
```

### "UMAP not available"
```bash
pip install umap-learn
```

### "File not found" errors
Make sure you have:
- `src/data/vector_store` (FAISS index file)
- `src/data/metadata.json` (metadata file)

### Memory issues with large datasets
- Reduce `sample_size` in similarity heatmap
- Use PCA instead of t-SNE/UMAP for 2D visualization
- Process documents one at a time in explorer

## Tips

1. **Start with the explorer** - Get familiar with your data structure
2. **Generate visualizations** - Get the big picture
3. **Focus on specific documents** - Deep dive into areas of interest
4. **Compare similar chunks** - Understand what makes chunks similar
5. **Iterate** - Use insights to improve chunking and embedding strategies

## Next Steps

After visualizing your vector store, you might want to:
- Adjust chunking parameters if distribution is uneven
- Try different embedding models if clusters aren't clear
- Add more documents to improve coverage
- Fine-tune similarity thresholds based on observed similarities
- Implement duplicate detection based on similarity patterns
