
import pandas as pd
import os

file_path = 'sample_bill.xls'
if os.path.exists(file_path):
    print(f"File size: {os.path.getsize(file_path)} bytes")
    try:
        df = pd.read_excel(file_path)
        print(f"Shape: {df.shape}")
        print("Columns:", df.columns.tolist())
        if not df.empty:
            print("First row:", df.iloc[0].to_dict())
        else:
            print("DataFrame is empty")
    except Exception as e:
        print(f"Error reading excel: {e}")
else:
    print("File not found")
