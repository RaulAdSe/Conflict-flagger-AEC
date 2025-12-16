import pandas as pd

def load_memoria_data(filepath):
    """
    Reads Memoria Excel database.
    Expected columns: 'Codi' and specification variables.
    """
    df = pd.read_excel(filepath)
    # Normalizing columns
    df.columns = [c.strip() for c in df.columns]
    
    if 'Codi' not in df.columns:
        raise ValueError("Memoria file missing 'Codi' column")
        
    df['Codi'] = df['Codi'].astype(str).str.strip()
    return df
