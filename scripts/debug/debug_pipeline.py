
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

from src.processors.pipeline import DataProcessingPipeline
from src.parsers.alipay_parser import AlipayParser

def debug_pipeline():
    print("Starting pipeline debug...")
    
    # 1. Parse the file (assuming sample_bill.xls exists and is empty/merchant format)
    parser = AlipayParser()
    file_path = 'sample_bill.xls'
    
    if not os.path.exists(file_path):
        print(f"File {file_path} not found. Creating a dummy empty merchant file.")
        # Create a dummy empty merchant excel
        df = pd.DataFrame(columns=['账单编号', '月份', '服务提供方', '应收总额', '实收总额'])
        df.to_excel(file_path, index=False)
        
    print(f"Parsing {file_path}...")
    try:
        df = parser.parse(file_path)
        print("Parse result:")
        print(f"Shape: {df.shape}")
        print(f"Columns: {df.columns.tolist()}")
        print(f"Empty? {df.empty}")
    except Exception as e:
        print(f"Parse failed: {e}")
        return

    # 2. Run pipeline
    print("\nRunning pipeline...")
    pipeline = DataProcessingPipeline()
    result = pipeline.process(df)
    
    print("\nPipeline Result:")
    print("Errors:", result.get('errors'))
    print("Warnings:", result.get('warnings'))
    print("Stats:", result.get('stats'))

if __name__ == "__main__":
    debug_pipeline()
