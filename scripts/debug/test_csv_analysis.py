
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from src.parsers.alipay_parser import AlipayParser
from src.processors.pipeline import DataProcessingPipeline

def test_csv_analysis():
    print("Testing analysis on sample_bill.csv...")
    file_path = 'sample_bill.csv'
    
    # 1. Parse
    parser = AlipayParser()
    try:
        print(f"Detecting format for {file_path}...")
        is_alipay = parser.detect_format(file_path)
        print(f"Is Alipay format: {is_alipay}")
        
        print("Parsing file...")
        df = parser.parse(file_path)
        print("Parse successful!")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        if not df.empty:
            print("First row:", df.iloc[0].to_dict())
    except Exception as e:
        print(f"Parse failed: {e}")
        return

    # 2. Pipeline
    print("\nRunning pipeline...")
    pipeline = DataProcessingPipeline()
    try:
        result = pipeline.process(df)
        print("Pipeline successful!")
        
        print("\nStats:")
        print(result['stats'])
        
        if result['errors']:
            print("\nErrors:", result['errors'])
        else:
            print("\nNo pipeline errors.")
            
    except Exception as e:
        print(f"Pipeline failed: {e}")

if __name__ == "__main__":
    test_csv_analysis()
