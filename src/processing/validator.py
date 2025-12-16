import pandas as pd
import numpy as np

def perform_audit(revit_df, presto_df, memoria_df):
    """
    Merges dataframes and performs validation.
    Returns: DataFrame structured for the output report.
    """
    
    # 1. Master List of Codis
    all_codis = set(revit_df['Codi']).union(set(presto_df['Codi'])).union(set(memoria_df['Codi']))
    
    report_rows = []
    
    for codi in all_codis:
        # Get data from each source
        r_row = revit_df[revit_df['Codi'] == codi].iloc[0] if codi in revit_df['Codi'].values else None
        p_row = presto_df[presto_df['Codi'] == codi].iloc[0] if codi in presto_df['Codi'].values else None
        m_row = memoria_df[memoria_df['Codi'] == codi].iloc[0] if codi in memoria_df['Codi'].values else None
        
        # Base Info
        familia = r_row['Familia'] if r_row is not None else "N/A"
        subgrupo = r_row['Tipo'] if r_row is not None else (p_row['Presto_Desc'][:20] if p_row is not None else "N/A")
        
        # --- Check 1: Existence ---
        exists_revit = r_row is not None
        exists_presto = p_row is not None
        exists_memoria = m_row is not None
        
        # Revit vs Presto
        if exists_revit and not exists_presto:
            check_val = "🟡 Warning" # Modelado no cobrable
            val_r = "Presente"
            val_p = "AUSENTE"
            val_m = "Presente" if exists_memoria else "AUSENTE"
            
            report_rows.append({
                'Familia': familia, 'Subgrupo': subgrupo, 'Codi': codi,
                'Variable': 'Existencia (Revit vs Presto)',
                'Valor Revit': val_r, 'Valor Presto': val_p, 'Valor Memoria': val_m,
                'CHECK': check_val, 'Color': 'YELLOW'
            })
        elif not exists_revit and exists_presto:
            check_val = "🟡 Warning" # Partida sin modelo
            val_r = "AUSENTE"
            val_p = "Presente"
            val_m = "Presente" if exists_memoria else "AUSENTE"
            
            report_rows.append({
                'Familia': "N/A", 'Subgrupo': subgrupo, 'Codi': codi,
                'Variable': 'Existencia (Revit vs Presto)',
                'Valor Revit': val_r, 'Valor Presto': val_p, 'Valor Memoria': val_m,
                'CHECK': check_val, 'Color': 'YELLOW'
            })
        else:
            # Both exist -> Green on Existence (implicit, usually verify variables)
             pass


        # --- Check 2: Variables (Intersection) ---
        # Find common columns between Revit and Memoria (e.g. Material)
        # Presto usually doesn't have these params parsed in this MVP unless mapped.
        
        if exists_revit and exists_memoria:
            common_cols = set(revit_df.columns).intersection(set(memoria_df.columns))
            common_cols.discard('Codi')
            common_cols.discard('Familia')
            common_cols.discard('Tipo') # Already used as descriptors
            
            for col in common_cols:
                val_r_v = r_row[col]
                val_m_v = m_row[col]
                
                # Check for N/A or empty
                is_na_r = pd.isna(val_r_v) or str(val_r_v).strip() == ""
                is_na_m = pd.isna(val_m_v) or str(val_m_v).strip() == ""
                
                # Logic Refinement:
                # 1. Collect all non-N/A values.
                # 2. Check for conflicts (Error).
                # 3. If no conflicts, check for missing values (Warning).
                # 4. If full match, OK.
                
                # Presto placeholder (as implemented previously)
                val_p_v = "N/A" 
                
                # Helper to normalize for comparison
                def normalize(v):
                    if pd.isna(v): return None
                    s = str(v).strip()
                    if s == "" or s == "N/A": return None # Handle explicitly
                    return s

                norm_r = normalize(val_r_v)
                norm_m = normalize(val_m_v)
                norm_p = normalize(val_p_v)
                
                # List of values present
                present_values = []
                if norm_r is not None: present_values.append(norm_r)
                if norm_m is not None: present_values.append(norm_m)
                if norm_p is not None: present_values.append(norm_p)
                
                # Check for Mismatch (Error)
                # We need to compare all present values against each other.
                # Numeric handling included.
                mismatch_found = False
                if len(present_values) > 1:
                    base_val = present_values[0]
                    for other_val in present_values[1:]:
                        # Try numeric comparison first
                        try:
                            f_base = float(base_val)
                            f_other = float(other_val)
                            if abs(f_base - f_other) > 0.01:
                                mismatch_found = True
                        except:
                            # String comparison
                            if base_val.upper() != other_val.upper():
                                mismatch_found = True
                        
                        if mismatch_found: break

                if mismatch_found:
                    check_status = "🔴 Error"
                    color = "RED"
                elif len(present_values) < 3:
                     # No mismatch, but missing data (e.g. Presto is N/A)
                     check_status = "🟡 Warning"
                     color = "YELLOW"
                else:
                    # All 3 present and matching
                    check_status = "🟢 OK"
                    color = "GREEN"
                
                report_rows.append({
                    'Familia': familia, 'Subgrupo': subgrupo, 'Codi': codi,
                    'Variable': col,
                    'Valor Revit': val_r_v, 
                    'Valor Presto': val_p_v, 
                    'Valor Memoria': val_m_v,
                    'CHECK': check_status,
                    'Color': color
                })

    return pd.DataFrame(report_rows)
