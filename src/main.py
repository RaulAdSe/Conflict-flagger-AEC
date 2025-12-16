import os
import sys

# Add src to path just in case
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from ingest.revit import load_revit_data
from ingest.presto import load_presto_data
from ingest.memoria import load_memoria_data
from processing.validator import perform_audit
from report.excel_exporter import generate_excel_report

def main():
    print("--- BIM-Cost-Spec Auditor v1.0 ---")
    
    # Paths
    # base_dir is project root. __file__ is src/main.py, so go up two levels? 
    # Actually, let's just use relative to run location or fix the logic.
    # os.path.dirname(__file__) -> src
    # os.path.dirname(...) -> root
    src_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(src_dir)
    
    input_dir = os.path.join(project_root, 'data', 'input')
    output_dir = os.path.join(project_root, 'data', 'output')
    os.makedirs(output_dir, exist_ok=True)
    
    revit_path = os.path.join(input_dir, 'revit_mock.xlsx')
    presto_path = os.path.join(input_dir, 'presto_mock.bc3')
    memoria_path = os.path.join(input_dir, 'memoria_mock.xlsx')
    
    # 1. Ingest
    print(f"Loading Revit data from {revit_path}...")
    try:
        df_revit = load_revit_data(revit_path)
    except Exception as e:
        print(f"Error loading Revit: {e}")
        return

    print(f"Loading Presto data from {presto_path}...")
    try:
        df_presto = load_presto_data(presto_path)
    except Exception as e:
        print(f"Error loading Presto: {e}")
        return

    print(f"Loading Memoria data from {memoria_path}...")
    try:
        df_memoria = load_memoria_data(memoria_path)
    except Exception as e:
        print(f"Error loading Memoria: {e}")
        return

    # 2. Process
    print("Auditing data...")
    report_df = perform_audit(df_revit, df_presto, df_memoria)
    
    if report_df.empty:
        print("No discrepancies found or no data to check.")
    else:
        print(f"Generated {len(report_df)} report entries.")

    # 3. Report
    output_file = os.path.join(output_dir, 'report_matrix_v4.xlsx')
    generate_excel_report(report_df, output_file)
    print(f"Report saved to {output_file}")
    print("Done.")

if __name__ == "__main__":
    main()
