import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
import pandas as pd
from openpyxl.styles import PatternFill, Font, Alignment

# --- PARSER BC3 MEJORADO ---
class BC3Parser:
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self):
        """Devuelve {codigo: {'qty': float, 'unit': str, 'desc': str, 'guid': str}}"""
        data = {}
        try:
            try:
                with open(self.filepath, 'r', encoding='latin-1') as f: content = f.read()
            except:
                with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
            
            lines = content.split('\n')
            
            # 1. Leer Conceptos (~C)
            for line in lines:
                line = line.strip()
                if line.startswith('~C|'):
                    parts = line.split('|')
                    if len(parts) >= 4:
                        code = parts[1].strip().rstrip('#')
                        unit = parts[2].strip()
                        desc = parts[3].strip()
                        data[code] = {'desc': desc, 'unit': unit, 'quantity': 0.0, 'guid': None}

            # 2. Leer Propiedades (~X) para extraer GUIDs si existen
            for line in lines:
                if line.startswith('~X|'):
                    parts = line.split('|')
                    if len(parts) > 1:
                        code = parts[1].strip().rstrip('#')
                        match_guid = re.search(r"IfcGUID\\([a-zA-Z0-9_$]{22})", line)
                        if match_guid and code in data:
                            data[code]['guid'] = match_guid.group(1)

            # 3. Leer Mediciones (~M)
            for line in lines:
                line = line.strip()
                if line.startswith('~M|'):
                    parts = line.split('|')
                    if len(parts) > 1:
                        hierarchy = parts[1]
                        child_code = hierarchy.split('\\')[-1].strip().rstrip('#') if '\\' in hierarchy else hierarchy.strip().rstrip('#')

                        qty = 0.0
                        for idx in [3, 4, 2]: 
                            if idx < len(parts):
                                val_str = parts[idx].strip()
                                if val_str and val_str.replace('.','',1).isdigit():
                                    try:
                                        qty = float(val_str)
                                        break
                                    except: pass
                        
                        if child_code in data:
                            data[child_code]['quantity'] += qty
            return data
        except Exception as e:
            messagebox.showerror("Error BC3", f"Error leyendo BC3: {str(e)}")
            return {}

# --- PARSER IFC MEJORADO ---
class IFCParser:
    def __init__(self, filepath):
        self.filepath = filepath

    def parse(self, valid_bc3_codes=None):
        """
        Devuelve counts_by_code y guids_found
        """
        counts_by_code = {}
        guids_found = {}
        if valid_bc3_codes is None: valid_bc3_codes = set()

        try:
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f: lines = f.readlines()
            except:
                with open(self.filepath, 'r', encoding='latin-1') as f: lines = f.readlines()

            id_map = {}
            for line in lines:
                if line.startswith('#'):
                    idx = line.find('=')
                    if idx != -1:
                        oid = line[:idx].strip()
                        content = line[idx+1:].strip()
                        id_map[oid] = content
            
            # 1. Mapeo de Tipos por CÓDIGO
            code_to_type_ids = {}
            guid_pattern = re.compile(r'^[a-zA-Z0-9_$]{22}$')

            for oid, content in id_map.items():
                if 'TYPE(' in content or 'STYLE(' in content:
                    candidates = re.findall(r"'([^']*)'", content)
                    for val in candidates:
                        code = val.strip()
                        # FILTRO ESTRICTO
                        is_valid = False
                        if code in valid_bc3_codes:
                            is_valid = True
                        else:
                            # Filtro anti-ruido
                            if (len(code) < 15 and len(code) > 0 and 
                                ' ' not in code and ':' not in code and 
                                not guid_pattern.match(code) and 
                                not (code.isdigit() and len(code) > 4)):
                                is_valid = True
                        
                        if is_valid:
                            if code not in code_to_type_ids: code_to_type_ids[code] = []
                            code_to_type_ids[code].append(oid)

            # 2. Contar por CÓDIGO
            for content in id_map.values():
                if 'IFCRELDEFINESBYTYPE' in content:
                    for code, type_ids in code_to_type_ids.items():
                        for tid in type_ids:
                            if tid in content:
                                match_list = re.search(r"\(\s*(#[0-9, \s#]+)\)", content)
                                if match_list:
                                    num_objects = len(match_list.group(1).split(','))
                                    if code not in counts_by_code: counts_by_code[code] = 0
                                    counts_by_code[code] += num_objects

            # 3. Mapeo auxiliar por GUID (GlobalId)
            for content in id_map.values():
                first_quote = content.find("'")
                if first_quote != -1:
                    guid_candidate = content[first_quote+1 : first_quote+23]
                    if len(guid_candidate) == 22 and guid_pattern.match(guid_candidate):
                        guids_found[guid_candidate] = 1

            return counts_by_code, guids_found

        except Exception as e:
            messagebox.showerror("Error IFC", f"Error leyendo IFC: {str(e)}")
            return {}, {}

# --- APLICACIÓN PRINCIPAL ---
class ComparadorBIMApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Comparador BIM - Final")
        self.root.geometry("600x250")

        self.path_bc3 = tk.StringVar()
        self.path_ifc = tk.StringVar()

        frame = tk.Frame(root, padx=20, pady=20)
        frame.pack(expand=True, fill='both')

        tk.Label(frame, text="1. Arxiu BC3:").grid(row=0, column=0, sticky='w')
        tk.Entry(frame, textvariable=self.path_bc3, width=50).grid(row=0, column=1, padx=5)
        tk.Button(frame, text="...", command=lambda: self.browse(self.path_bc3, "*.bc3")).grid(row=0, column=2)

        tk.Label(frame, text="2. Arxiu IFC:").grid(row=1, column=0, sticky='w', pady=10)
        tk.Entry(frame, textvariable=self.path_ifc, width=50).grid(row=1, column=1, padx=5, pady=10)
        tk.Button(frame, text="...", command=lambda: self.browse(self.path_ifc, "*.ifc")).grid(row=1, column=2)

        tk.Button(frame, text="COMPARAR", command=self.run_comparison, bg="#dddddd", height=2).grid(row=2, column=0, columnspan=3, pady=20, sticky='ew')

    def browse(self, var, filetype):
        f = filedialog.askopenfilename(filetypes=[("Archivos", filetype)])
        if f: var.set(f)

    def is_ignored_item(self, code, desc):
        """Ignora elementos irrelevantes o administrativos."""
        ignore_terms = [
            "información", "project info", "plano", "sheet", "vista", "view",
            "zona de", "climatización", "topografía", "surface", "habitaciones", "rooms",
            "áreas", "areas", "system panel", "materiales", "materials", 
            "aberturas", "hueco", "opening", "void", "corte", "líneas", "lines", 
            "earth", "tubería", "pipe", "ductile", "hierro"
        ]
        text_check = (str(desc) + " " + str(code)).lower()
        for term in ignore_terms:
            if term in text_check: return True
        return False

    def run_comparison(self):
        bc3_path = self.path_bc3.get()
        ifc_path = self.path_ifc.get()

        if not bc3_path or not ifc_path:
            messagebox.showwarning("Aviso", "Selecciona ambos archivos.")
            return

        bc3_data = BC3Parser(bc3_path).parse()
        bc3_keys = set(bc3_data.keys())
        ifc_counts, ifc_guids = IFCParser(ifc_path).parse(valid_bc3_codes=bc3_keys)

        discrepancias = []
        coincidencias = []
        all_codes = set(bc3_data.keys()) | set(ifc_counts.keys())

        for code in all_codes:
            if not code or len(code) > 40: continue

            bc3_info = bc3_data.get(code, {'quantity': 0, 'unit': '-', 'desc': '-', 'guid': None})
            qty_bc3 = bc3_info['quantity']
            unit = bc3_info['unit']
            desc = bc3_info['desc']
            bc3_guid = bc3_info.get('guid')
            
            qty_ifc = ifc_counts.get(code, 0)

            # Recuperación por GUID si existe
            if qty_ifc == 0 and bc3_guid and bc3_guid in ifc_guids:
                qty_ifc = 1 

            # --- FILTROS ---
            if qty_bc3 == 0 and qty_ifc == 0: continue
            if self.is_ignored_item(code, desc): continue
            if code not in bc3_data and (":" in code or len(code) > 20 or (code.isdigit() and len(code)>5)):
                continue

            status = "OK"
            msg = ""

            if code not in bc3_data:
                status = "MISSING_IN_BC3"
                msg = "En IFC pero no en Presupuesto"
            elif qty_ifc == 0:
                status = "MISSING_IN_IFC"
                msg = "En Presupuesto pero no en IFC"
            else:
                is_count = unit.lower() in ['u', 'ud', 'un', 'pza', 'ut']
                if is_count:
                    if abs(qty_bc3 - qty_ifc) > 0.1:
                        status = "QTY_MISMATCH"
                        msg = f"Diferencia: BC3={qty_bc3} vs IFC={qty_ifc}"
                else:
                    msg = f"Info: {unit} vs Count ({qty_ifc})"

            row = {'CODI': code, 'DESC': desc, 'UNIDAD': unit, 'VALOR_BC3': qty_bc3, 'VALOR_IFC': qty_ifc, 'ESTADO': status, 'MENSAJE': msg}

            if status == "OK":
                coincidencias.append(row)
            else:
                discrepancias.append(row)

        try:
            ifc_filename = os.path.basename(ifc_path)
            base_name = os.path.splitext(ifc_filename)[0]
            output_file = f"{base_name}_excel.xlsx"
            
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                green_fill = PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid')
                red_fill = PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid')
                yellow_fill = PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid')
                success_fill = PatternFill(start_color='00B050', end_color='00B050', fill_type='solid')
                white_font = Font(color="FFFFFF", bold=True)
                center_align = Alignment(horizontal='center', vertical='center')

                if not discrepancias:
                    df_success = pd.DataFrame({'RESULTADO': ["NO EXISTE NINGUNA DISCREPANCIA IMPORTANTE"]})
                    df_success.to_excel(writer, sheet_name='Resumen', index=False)
                    ws = writer.sheets['Resumen']
                    cell = ws['A2']
                    cell.fill = success_fill
                    cell.font = white_font
                    cell.alignment = center_align
                    ws.column_dimensions['A'].width = 60
                else:
                    df_disc = pd.DataFrame(discrepancias)
                    status_priority = {'MISSING_IN_BC3': 1, 'MISSING_IN_IFC': 1, 'QTY_MISMATCH': 2}
                    df_disc['Sort'] = df_disc['ESTADO'].map(status_priority)
                    df_disc = df_disc.sort_values('Sort').drop('Sort', axis=1)
                    
                    df_disc.to_excel(writer, sheet_name='Discrepancias', index=False)
                    ws = writer.sheets['Discrepancias']
                    for row_idx, row_data in enumerate(df_disc.itertuples(), start=2):
                        st = row_data.ESTADO
                        fill = red_fill if st == 'QTY_MISMATCH' else yellow_fill
                        for col_idx in range(1, len(df_disc.columns) + 1):
                            ws.cell(row=row_idx, column=col_idx).fill = fill
                
                if coincidencias:
                    df_match = pd.DataFrame(coincidencias)
                    df_match.to_excel(writer, sheet_name='Coincidencias (Matches)', index=False)
                    ws_match = writer.sheets['Coincidencias (Matches)']
                    for row_idx in range(2, len(df_match) + 2):
                        for col_idx in range(1, len(df_match.columns) + 1):
                            ws_match.cell(row=row_idx, column=col_idx).fill = green_fill

            messagebox.showinfo("Éxito", f"Reporte generado: {output_file}")
            os.startfile(output_file) if os.name == 'nt' else None

        except Exception as e:
            messagebox.showerror("Error Exportación", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = ComparadorBIMApp(root)
    root.mainloop()