
import pandas as pd

try:
    df = pd.read_excel('sample_bill.xls')
    print("First 20 rows:")
    print(df.head(20).to_string())
    print("\nColumns:")
    print(df.columns.tolist())
except Exception as e:
    print(f"Error reading excel: {e}")
