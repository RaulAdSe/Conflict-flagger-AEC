import pandas as pd
import re

def load_presto_data(filepath):
    """
    Parses a BC3 (FIEBDC-3) file.
    Extracts ~C records: Code, Unit, Summary, Price.
    Returns: DataFrame with 'Codi' as key.
    """
    records = []
    
    with open(filepath, 'r', encoding='latin-1', errors='replace') as f:
        for line in f:
            line = line.strip()
            if line.startswith('~C'):
                # Format: ~C|Code#|Unit|Summary|Price|...
                parts = line.split('|')
                if len(parts) > 4:
                    # Clean Code: Remove # suffix if present
                    raw_code = parts[1]
                    code = raw_code.replace('#', '').strip()
                    
                    unit = parts[2].strip()
                    summary = parts[3].strip()
                    try:
                        price = float(parts[4].replace(',', '.'))
                    except:
                        price = 0.0
                    
                    records.append({
                        'Codi': code,
                        'Presto_Unit': unit,
                        'Presto_Desc': summary,
                        'Presto_Price': price
                    })
    
    df = pd.DataFrame(records)
    if 'Codi' in df.columns:
        df['Codi'] = df['Codi'].astype(str).str.strip()
    else:
         df = pd.DataFrame(columns=['Codi', 'Presto_Unit', 'Presto_Desc', 'Presto_Price'])

    return df
