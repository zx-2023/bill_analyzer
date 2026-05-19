
import sys
import os
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from src.parsers.alipay_parser import AlipayParser

def test_parser():
    parser = AlipayParser()
    file_path = 'sample_bill.xls'
    
    print(f"Testing parser with {file_path}")
    
    if not os.path.exists(file_path):
        print("File not found!")
        return

    try:
        # Try detection
        is_alipay = parser.detect_format(file_path)
        print(f"Is Alipay format: {is_alipay}")
        
        if is_alipay:
            df = parser.parse(file_path)
            print("Parse successful!")
            print(df.head())
            print(df.columns)
        else:
            print("Detection failed.")
            # Try parsing anyway to see error
            try:
                df = parser.parse(file_path)
                print("Parse successful (despite detection failure)!")
                print(df.head())
            except Exception as e:
                print(f"Parse failed: {e}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_parser()
