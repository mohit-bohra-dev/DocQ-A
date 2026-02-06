#!/usr/bin/env python3
"""Test the document ingestion service directly."""

import tempfile
import os
from src.config import config
from src.embeddings import EmbeddingService
from src.vector_store import FAISSVectorStore
from src.ingestion import DocumentIngestionService

def test_ingestion_service():
    """Test the document ingestion service directly."""
    print("Testing DocumentIngestionService...")
    
    # Create a simple PDF content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000074 00000 n 
0000000120 00000 n 
0000000179 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
274
%%EOF"""
    
    try:
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_content)
            temp_file_path = temp_file.name
        
        print(f"Created temporary PDF: {temp_file_path}")
        
        # Test each component individually
        print("\n1. Testing EmbeddingService...")
        try:
            embedding_service = EmbeddingService(config)
            print(f"✅ EmbeddingService created successfully")
            
            # Test embedding generation
            test_embedding = embedding_service.generate_embedding("test text")
            print(f"✅ Embedding generated: dimension = {len(test_embedding)}")
            
        except Exception as e:
            print(f"❌ EmbeddingService failed: {e}")
            return False
        
        print("\n2. Testing FAISSVectorStore...")
        try:
            dimension = embedding_service.get_embedding_dimension()
            vector_store = FAISSVectorStore(
                dimension=dimension,
                index_path=config.vector_store_path,
                metadata_path=config.metadata_path
            )
            print(f"✅ FAISSVectorStore created successfully")
            
        except Exception as e:
            print(f"❌ FAISSVectorStore failed: {e}")
            return False
        
        print("\n3. Testing DocumentIngestionService...")
        try:
            ingestion_service = DocumentIngestionService(
                config=config,
                embedding_service=embedding_service,
                vector_store=vector_store
            )
            print(f"✅ DocumentIngestionService created successfully")
            
        except Exception as e:
            print(f"❌ DocumentIngestionService creation failed: {e}")
            return False
        
        print("\n4. Testing document processing...")
        try:
            success = ingestion_service.process_document(temp_file_path, "test.pdf")
            print(f"Document processing result: {success}")
            
            if success:
                print("✅ Document processing successful!")
                
                # Get stats
                stats = ingestion_service.get_processing_stats()
                print(f"Processing stats: {stats}")
                
            else:
                print("❌ Document processing failed!")
                return False
                
        except Exception as e:
            print(f"❌ Document processing exception: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Clean up
        os.unlink(temp_file_path)
        print(f"Cleaned up temporary file: {temp_file_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the ingestion test."""
    print("=" * 60)
    print("Testing Document Ingestion Service")
    print("=" * 60)
    
    if test_ingestion_service():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")

if __name__ == "__main__":
    main()