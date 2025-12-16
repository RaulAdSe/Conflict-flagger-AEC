import pandas as pd
import os

output_path = 'data/output/report_matrix.xlsx'
if not os.path.exists(output_path):
    print("Report not found!")
    exit(1)

df = pd.read_excel(output_path)
print(df[['Codi', 'Variable', 'CHECK', 'Valor Revit', 'Valor Memoria']])
