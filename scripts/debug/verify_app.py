
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

def verify_imports():
    print("Verifying imports...")
    try:
        from src.parsers.alipay_parser import AlipayParser
        print("AlipayParser imported successfully")
        
        from src.integrations.alipay_client import AlipayClient
        print("AlipayClient imported successfully")
        
        # Try instantiating
        parser = AlipayParser()
        print("AlipayParser instantiated")
        
        client = AlipayClient()
        print("AlipayClient instantiated (might warn about missing keys)")
        
    except ImportError as e:
        print(f"Import failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Verification failed: {e}")
        sys.exit(1)

    print("Verification successful!")

if __name__ == "__main__":
    verify_imports()
