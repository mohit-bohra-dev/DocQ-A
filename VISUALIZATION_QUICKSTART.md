# Vector Store Visualization - Quick Start

## 🚀 Three Ways to Visualize Your Vector Store

### 1. Quick Analysis (Works Now!)
**Best for:** Fast overview

```bash
uv run quick_viz.py
```

**Shows:**
- Document and chunk counts
- Vector statistics
- Similarity analysis
- Quality insights

**Time:** ~10 seconds

---

### 2. Interactive Explorer
**Best for:** Detailed exploration and investigation

```bash
# Install dependencies if needed
uv sync

# Run explorer
uv run explore_vector_store.py
```

**Features:**
- Browse documents
- Find similar chunks
- Search by page
- Random sampling

**Time:** Interactive (as long as you want)

---

### 3. Full Visualization Suite
**Best for:** Comprehensive analysis with charts and graphs

```bash
# Install dependencies if needed
uv sync

# Generate all visualizations
uv run visualize_vector_store.py
```

**Generates:**
- Document distribution charts
- Page distribution graphs
- 2D embedding projections (PCA, t-SNE, UMAP)
- Similarity heatmaps
- Vector statistics plots

**Output:** `visualizations/` folder with PNG files

**Time:** 1-5 minutes depending on dataset size

---

## 📋 Recommended Workflow

### First Time
```bash
# 1. Quick check
uv run quick_viz.py

# 2. If everything looks good, install viz dependencies
uv sync

# 3. Generate full visualizations
uv run visualize_vector_store.py

# 4. Explore interactively
uv run explore_vector_store.py
```

### Regular Use
```bash
# Quick check after adding new documents
uv run quick_viz.py

# Deep dive when needed
uv run explore_vector_store.py
```

---

## 🎯 What to Look For

### ✅ Good Signs
- **Chunks per document:** Relatively balanced (within 2-3x of each other)
- **Same-doc similarity:** > 0.7 (chunks from same document are similar)
- **Cross-doc similarity:** < 0.5 (different documents are distinct)
- **Separation ratio:** > 1.5x (same-doc vs cross-doc similarity)
- **Vector norms:** Consistent (low std deviation)

### ⚠️ Warning Signs
- **Highly unbalanced chunks:** One document has 10x more chunks than others
- **Low same-doc similarity:** < 0.5 (chunking may be too aggressive)
- **High cross-doc similarity:** > 0.7 (documents not well separated)
- **Separation ratio:** < 1.2x (embeddings not discriminative)
- **Extreme vector norms:** Very high variance in norms

---

## 🛠️ Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements-viz.txt
```

### "File not found" errors
Make sure you have:
- `src/data/vector_store` (FAISS index)
- `src/data/metadata.json` (metadata)

### Memory issues
- Use `quick_viz.py` instead (samples data)
- Reduce sample size in visualization scripts
- Process one document at a time in explorer

### Slow performance
- Use PCA instead of t-SNE/UMAP
- Reduce sample size for heatmaps
- Use quick_viz.py for fast checks

---

## 📊 Understanding Your Results

### Document Distribution
Shows how chunks are distributed across documents.
- **Even distribution:** Good chunking strategy
- **Uneven distribution:** May need to adjust chunk size or overlap

### Similarity Scores
- **0.9-1.0:** Nearly identical (possible duplicates)
- **0.7-0.9:** Very similar (same topic/section)
- **0.5-0.7:** Moderately similar (related content)
- **0.3-0.5:** Somewhat similar (same document)
- **< 0.3:** Different content

### 2D Embeddings
- **Tight clusters:** Documents are well-separated
- **Mixed colors:** Documents overlap in embedding space
- **Outliers:** Unusual or unique content

---

## 💡 Tips

1. **Start simple:** Use `quick_viz.py` first
2. **Install once:** `pip install -r requirements-viz.txt` for full features
3. **Visualize regularly:** After adding new documents
4. **Compare over time:** Track how metrics change
5. **Use insights:** Adjust chunking based on what you see

---

## 📚 More Information

See `VECTOR_STORE_VISUALIZATION.md` for:
- Detailed explanations of each visualization
- Customization options
- Advanced usage patterns
- Interpretation guidelines

---

## 🎓 Example Session

```bash
# Quick check
$ python quick_viz.py
✓ Loaded 124 metadata entries
✓ Loaded index with 124 vectors
📄 Documents: 3
📦 Total Chunks: 124
Average similarity within same document: 0.756
✅ Good: Chunks from same document are highly similar
✅ Good: Clear separation between documents

# Looks good! Let's explore
$ python explore_vector_store.py
# [Interactive menu appears]
# Choose option 1 to see summary
# Choose option 4 to find similar chunks

# Generate visualizations
$ python visualize_vector_store.py
Generating all visualizations...
Saved: visualizations/document_distribution.png
Saved: visualizations/embeddings_2d.png
...
VISUALIZATION COMPLETE!

# Open visualizations folder to view charts
```

---

## 🚦 Quick Decision Guide

**Just want to check if everything is working?**
→ `python quick_viz.py`

**Want to explore specific documents or chunks?**
→ `python explore_vector_store.py`

**Need charts and graphs for analysis or presentation?**
→ `python visualize_vector_store.py`

**Want to understand the quality of your embeddings?**
→ All three! Start with quick_viz, then visualize, then explore

---

Happy visualizing! 🎉
