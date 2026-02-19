# Vector Store Visualization Tools

Complete toolkit for visualizing and analyzing your FAISS vector store.

## 🎯 Quick Start

### Fastest Way (Works Immediately)
```bash
.venv\Scripts\python.exe quick_viz.py
```

### Windows Batch File
```bash
visualize.bat
```

## 📦 What You Get

### Three Powerful Tools

| Tool | Purpose | Dependencies | Speed |
|------|---------|--------------|-------|
| `quick_viz.py` | Fast statistics & insights | ✅ None (built-in) | 10 sec |
| `explore_vector_store.py` | Interactive exploration | matplotlib, seaborn | Interactive |
| `visualize_vector_store.py` | Full visualization suite | + scikit-learn, umap | 1-5 min |

### Complete Documentation

| File | Description |
|------|-------------|
| `VISUALIZATION_QUICKSTART.md` | Get started in 5 minutes |
| `VECTOR_STORE_VISUALIZATION.md` | Complete guide with examples |
| `VISUALIZATION_SUMMARY.md` | Your current results & insights |
| `README_VISUALIZATION.md` | This file |

## 🚀 Installation

### Already Works
```bash
# Quick analysis (no installation needed)
uv run quick_viz.py
```

### Full Features
```bash
# Install visualization dependencies (matplotlib, seaborn, umap-learn)
uv sync

# Now you can use all tools
uv run explore_vector_store.py
uv run visualize_vector_store.py
```

## 📊 Your Vector Store Status

**Current State:** ✅ Healthy
- 3 documents indexed
- 152 chunks total
- 384-dimensional embeddings
- Normalized vectors (all norms = 1.0)
- Moderate within-document similarity (0.615)

See `VISUALIZATION_SUMMARY.md` for detailed analysis.

## 🎨 What Each Tool Does

### 1. quick_viz.py
**Best for:** Daily checks, quick insights

**Shows:**
- Document breakdown
- Chunk distribution
- Vector statistics
- Similarity analysis
- Quality metrics

**Example Output:**
```
📄 Documents: 3
📦 Total Chunks: 152
📐 Vector Dimension: 384

Average similarity within same document: 0.615
⚠️ Moderate: Some similarity within documents
```

### 2. explore_vector_store.py
**Best for:** Investigation, deep dives

**Features:**
- Interactive menu
- Browse documents
- Find similar chunks
- Search by page
- Random sampling

**Example Session:**
```
1. Show Summary
2. List All Documents
3. Show Document Details
4. Find Similar Chunks
5. Search by Document and Page
6. Random Chunk Analysis
```

### 3. visualize_vector_store.py
**Best for:** Reports, presentations, analysis

**Generates:**
- `document_distribution.png` - Bar chart of chunks per document
- `page_distribution.png` - Chunks per page breakdown
- `embeddings_2d.png` - 2D projection (PCA/t-SNE/UMAP)
- `similarity_heatmap.png` - Cosine similarity matrix
- `vector_statistics.png` - Statistical properties

**Output:** All files saved to `visualizations/` folder

## 📖 Documentation Guide

### New User?
Start here: `VISUALIZATION_QUICKSTART.md`

### Want Details?
Read: `VECTOR_STORE_VISUALIZATION.md`

### See Your Results?
Check: `VISUALIZATION_SUMMARY.md`

### Quick Reference?
This file: `README_VISUALIZATION.md`

## 🔍 Common Tasks

### Check Vector Store Health
```bash
uv run quick_viz.py
```

### Explore a Specific Document
```bash
uv run explore_vector_store.py
# Choose option 3, enter document name
```

### Generate Charts for Presentation
```bash
# Install deps if needed
uv sync

# Generate all visualizations
uv run visualize_vector_store.py

# Open folder
start visualizations
```

### Find Similar Chunks
```bash
uv run explore_vector_store.py
# Choose option 4, enter chunk index
```

### Analyze After Adding Documents
```bash
# Quick check
uv run quick_viz.py

# Full analysis if needed
uv run visualize_vector_store.py
```

## 💡 Tips

1. **Run quick_viz.py regularly** - Fast health check
2. **Use explore_vector_store.py for debugging** - Find issues
3. **Generate visualizations for reports** - Professional charts
4. **Check similarity scores** - Ensure quality
5. **Monitor chunk distribution** - Balanced is better

## 🎓 Understanding Results

### Good Signs ✅
- Same-document similarity > 0.7
- Separation ratio > 1.5x
- Consistent vector norms
- Balanced chunk distribution

### Warning Signs ⚠️
- Same-document similarity < 0.5
- Separation ratio < 1.2x
- Highly uneven chunks
- Extreme outliers

### Your Current Status
- ✅ Normalized vectors
- ⚠️ Moderate similarity (0.615)
- ✅ Balanced distribution
- ✅ Consistent chunking

See `VISUALIZATION_SUMMARY.md` for interpretation.

## 🛠️ Troubleshooting

### "Module not found"
```bash
uv sync
```

### "File not found"
Make sure you have:
- `src/data/vector_store`
- `src/data/metadata.json`

### Emojis Look Weird
Normal on Windows PowerShell. Data is correct.

### Slow Performance
- Use `quick_viz.py` for speed
- Reduce sample sizes in scripts
- Use PCA instead of t-SNE

### Memory Issues
- Sample data instead of full dataset
- Process documents one at a time
- Use quick_viz.py

## 🔗 Integration

These tools work with your existing RAG system:
- Read from `src/data/vector_store` (FAISS index)
- Read from `src/data/metadata.json` (metadata)
- No modifications to your main code needed
- Run anytime without affecting your app

## 📈 Next Steps

1. ✅ **You're ready!** Run `uv run quick_viz.py` now
2. 📚 Read `VISUALIZATION_QUICKSTART.md` for details
3. 🎨 Run `uv sync` to install visualization dependencies
4. 🔍 Explore your data with `uv run explore_vector_store.py`
5. 📊 Generate charts with `uv run visualize_vector_store.py`

## 🎉 Summary

You now have professional-grade vector store visualization tools:

- ✅ **Works immediately** - No installation needed for quick_viz
- 📊 **Three tools** - Fast, interactive, and comprehensive
- 📖 **Complete docs** - Four guides to help you
- 🎨 **Beautiful charts** - Professional visualizations
- 🔍 **Deep insights** - Understand your embeddings

Start with: `quick_viz.py`

Happy visualizing! 🚀
