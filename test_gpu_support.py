#!/usr/bin/env python3
"""Test script to check GPU support for PyTorch and FAISS."""

def test_pytorch_gpu():
    """Test PyTorch GPU support."""
    try:
        import torch
        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"CUDA device count: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"CUDA device {i}: {torch.cuda.get_device_name(i)}")
            print(f"CUDA version: {torch.version.cuda}")
            
            # Test tensor operations on GPU
            device = torch.device("cuda:0")
            x = torch.randn(1000, 1000, device=device)
            y = torch.randn(1000, 1000, device=device)
            z = torch.mm(x, y)
            print("✅ PyTorch GPU tensor operations working")
        else:
            print("❌ CUDA not available for PyTorch")
            
    except ImportError as e:
        print(f"❌ PyTorch not installed: {e}")
    except Exception as e:
        print(f"❌ PyTorch GPU test failed: {e}")


def test_faiss_gpu():
    """Test FAISS GPU support."""
    try:
        import faiss
        print(f"FAISS version: {faiss.__version__}")
        
        # Check if GPU functions are available
        if hasattr(faiss, 'get_num_gpus'):
            gpu_count = faiss.get_num_gpus()
            print(f"FAISS GPU count: {gpu_count}")
            
            if gpu_count > 0:
                print("✅ FAISS GPU support available")
                
                # Test GPU index creation
                try:
                    dimension = 128
                    cpu_index = faiss.IndexFlatL2(dimension)
                    
                    # Try to create GPU resources
                    gpu_resources = faiss.StandardGpuResources()
                    gpu_index = faiss.index_cpu_to_gpu(gpu_resources, 0, cpu_index)
                    print("✅ FAISS GPU index creation working")
                    
                    # Test adding vectors
                    import numpy as np
                    vectors = np.random.random((100, dimension)).astype('float32')
                    gpu_index.add(vectors)
                    print("✅ FAISS GPU vector operations working")
                    
                except Exception as e:
                    print(f"❌ FAISS GPU operations failed: {e}")
            else:
                print("❌ No GPUs detected by FAISS")
        else:
            print("❌ FAISS GPU functions not available (CPU-only version)")
            
    except ImportError as e:
        print(f"❌ FAISS not installed: {e}")
    except Exception as e:
        print(f"❌ FAISS GPU test failed: {e}")


def test_sentence_transformers_gpu():
    """Test Sentence Transformers GPU support."""
    try:
        from sentence_transformers import SentenceTransformer
        import torch
        
        if torch.cuda.is_available():
            model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cuda')
            embeddings = model.encode(["This is a test sentence"], convert_to_tensor=True)
            print(f"✅ Sentence Transformers GPU working, embedding shape: {embeddings.shape}")
            print(f"✅ Embeddings on device: {embeddings.device}")
        else:
            print("❌ CUDA not available for Sentence Transformers")
            
    except ImportError as e:
        print(f"❌ Sentence Transformers not installed: {e}")
    except Exception as e:
        print(f"❌ Sentence Transformers GPU test failed: {e}")


if __name__ == "__main__":
    print("=== GPU Support Test ===\n")
    
    print("1. Testing PyTorch GPU support:")
    test_pytorch_gpu()
    print()
    
    print("2. Testing FAISS GPU support:")
    test_faiss_gpu()
    print()
    
    print("3. Testing Sentence Transformers GPU support:")
    test_sentence_transformers_gpu()
    print()
    
    print("=== Test Complete ===")