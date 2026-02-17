# Duplicate Detection and Replace Functionality

## Overview

Implemented comprehensive duplicate detection and document replacement functionality to prevent users from uploading the same document multiple times.

## Changes Made

### 1. Vector Store (`src/vector_store.py`)

Added new methods to support duplicate detection and document management:

- `get_all_document_names()` - Returns list of all unique document names
- `delete_document_by_name(document_name)` - Deletes all chunks for a specific document
- `document_exists(document_name)` - Checks if a document exists
- `get_document_info(document_name)` - Returns detailed information about a document
- `_rebuild_index()` - Internal method to rebuild FAISS index after deletions

### 2. FastAPI Backend (`src/app.py`)

#### Modified `/upload` Endpoint
- Added `replace_existing` parameter (default: False)
- Checks for duplicate documents before processing
- Returns HTTP 409 (Conflict) if duplicate found and replace_existing=False
- Automatically deletes old document if replace_existing=True
- Uses simple filename as document_name (no UUID prefix)

#### New Endpoints
- `GET /documents` - List all uploaded documents with metadata
- `DELETE /documents/{document_name}` - Delete a specific document

### 3. API Client (`src/ui_utils.py`)

Updated methods:
- `upload_document()` - Added `replace_existing` parameter
- `list_documents()` - NEW: Get list of all documents
- `delete_document()` - NEW: Delete a specific document

### 4. Streamlit UI (`streamlit_app.py`)

Enhanced upload interface:
- Detects duplicate documents before upload
- Shows warning message if document already exists
- Displays "Replace existing?" checkbox for duplicates
- Changes button text to "Replace & Process" when replacing
- Updates document list correctly after replacement
- Better error handling for duplicate scenarios

## Usage

### API Usage

```python
# Upload new document
POST /upload
- file: PDF file
- replace_existing: false (default)

# Replace existing document
POST /upload
- file: PDF file
- replace_existing: true

# List all documents
GET /documents

# Delete a document
DELETE /documents/{document_name}
```

### UI Usage

1. **Upload New Document**:
   - Select PDF file
   - Click "Upload & Process"

2. **Replace Existing Document**:
   - Select same PDF file
   - Warning appears: "⚠️ This document already exists!"
   - Check "Replace existing?" checkbox
   - Click "Replace & Process"

3. **View Documents**:
   - See list in "Document Management" section
   - Shows document name, status, and upload time

## Benefits

✅ **Prevents Duplicates** - No more duplicate chunks in vector store
✅ **Saves Storage** - Avoids storing same embeddings multiple times
✅ **Better Search Results** - No duplicate results in top-k searches
✅ **Clear Source References** - No confusion from multiple versions
✅ **User Control** - Users can explicitly choose to replace documents
✅ **Clean Document Names** - No UUID prefixes, just original filenames

## Error Handling

- **409 Conflict**: Document already exists (with helpful message)
- **404 Not Found**: Document doesn't exist when trying to delete
- **500 Internal Error**: Processing or deletion failures

## Example Scenarios

### Scenario 1: Accidental Duplicate Upload
```
User uploads "report.pdf" → Success
User uploads "report.pdf" again → Error 409: "Document 'report.pdf' already exists"
UI shows: "⚠️ This document already exists!"
User can check "Replace existing?" to proceed
```

### Scenario 2: Intentional Document Update
```
User uploads "report_v1.pdf" → Success
User uploads "report_v2.pdf" → Success (different name)
OR
User uploads "report.pdf" → Success
User uploads "report.pdf" with replace=true → Old version deleted, new version uploaded
```

### Scenario 3: Document Management
```
User views document list → Sees all uploaded documents
User deletes "old_report.pdf" → Document and all chunks removed
Vector store automatically rebuilt
```

## Technical Details

### Document Identification
- Documents are identified by their **filename** (not UUID)
- Example: `report.pdf` instead of `uuid123_report.pdf`
- Makes source references more readable

### Deletion Process
1. Find all chunks with matching document_name
2. Remove from metadata and chunks stores
3. Rebuild FAISS index without deleted chunks
4. Save updated index to disk

### Index Rebuilding
- Efficiently reconstructs FAISS index after deletions
- Maintains embedding quality (no re-computation needed)
- Updates internal ID mappings

## Future Enhancements

Potential improvements:
- Content-based deduplication (using file hash)
- Document versioning system
- Bulk document operations
- Document filtering in queries
- Document metadata (upload date, size, page count)

## Testing

To test the feature:

```python
# Test duplicate detection
python test_upload.py

# Test via Streamlit UI
streamlit run streamlit_app.py

# Test via API
curl -X POST http://localhost:8000/upload -F "file=@test.pdf"
curl -X POST http://localhost:8000/upload -F "file=@test.pdf" -F "replace_existing=true"
curl -X GET http://localhost:8000/documents
curl -X DELETE http://localhost:8000/documents/test.pdf
```

## Migration Notes

**Breaking Change**: Document naming has changed from `{uuid}_{filename}` to just `{filename}`.

Existing documents with UUID prefixes will still work, but new uploads will use simple filenames. To migrate:
1. List all documents
2. Delete old UUID-prefixed documents
3. Re-upload with new naming scheme

Or keep both naming schemes (they won't conflict).