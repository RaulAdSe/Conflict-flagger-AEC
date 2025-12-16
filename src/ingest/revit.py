import pandas as pd

def load_revit_data(filepath):
    """
    Reads Revit Excel export.
    Expected columns: 'Familia', 'Tipo', 'Codi', and variables.
    Returns: DataFrame with 'Codi' as key.
    """
    df = pd.read_excel(filepath)
    # Normalizing columns
    df.columns = [c.strip() for c in df.columns]
    
    # Requirement: Identify 'Codi'
    if 'Codi' not in df.columns:
        raise ValueError("Revit file missing 'Codi' column")
        
    df['Codi'] = df['Codi'].astype(str).str.strip()
    return df
