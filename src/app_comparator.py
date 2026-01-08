import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ifcopenshell
import ifcopenshell.util.element
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from datetime import datetime
import os

class ConflictFlaggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conflict Flagger AEC - Eina de Revisió")
        self.root.geometry("650x550")

        self.path_ifc = tk.StringVar()
        self.path_bc3 = tk.StringVar()

        # --- UI SETUP ---
        frame_main = tk.Frame(root, padx=10, pady=10)
        frame_main.pack(fill="both", expand=True)

        # Inputs
        self._make_file_input(frame_main, "Arxiu Model (IFC)", self.path_ifc, self.load_ifc)
        self._make_file_input(frame_main, "Arxiu Pressupost (BC3)", self.path_bc3, self.load_bc3)

        # Botó
        tk.Button(frame_main, text="GENERAR EXCEL", 
                  bg="#217346", fg="white", font=("Segoe UI", 11, "bold"),
                  command=self.generate_excel_report, pady=10).pack(fill="x", pady=15)

        # Log
        self.log_area = scrolledtext.ScrolledText(frame_main, height=15)
        self.log_area.pack(fill="both", expand=True)

    def _make_file_input(self, parent, label, var, cmd):
        frame = tk.LabelFrame(parent, text=label, padx=5, pady=5)
        frame.pack(fill="x", pady=5)
        tk.Entry(frame, textvariable=var).pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frame, text="Buscar...", command=cmd).pack(side="left")

    def log(self, msg):
        self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)
        self.root.update()

    def load_ifc(self):
        f = filedialog.askopenfilename(filetypes=[("IFC Files", "*.ifc")])
        if f: self.path_ifc.set(f)

    def load_bc3(self):
        f = filedialog.askopenfilename(filetypes=[("BC3 Files", "*.bc3")])
        if f: self.path_bc3.set(f)

    # --- LÒGICA DE LECTURA ---

    def get_bc3_codes(self, filepath):
        codes = {} 
        try:
            with open(filepath, 'r', encoding='latin1') as f:
                for line in f:
                    if line.startswith('~C|'):
                        parts = line.split('|')
                        if len(parts) > 1:
                            c = parts[1].replace('\\', '').strip()
                            desc = parts[2] if len(parts) > 2 else "Sense descripció"
                            if c: codes[c] = desc
            return codes
        except Exception as e:
            self.log(f"Error llegint BC3: {e}")
            return {}

    def get_ifc_data(self, filepath):
        elements_map = [] 
        try:
            ifc = ifcopenshell.open(filepath)
            products = ifc.by_type("IfcElement")
            total = len(products)
            self.log(f"Analitzant {total} elements a l'IFC...")

            for i, product in enumerate(products):
                if i % 50 == 0: self.root.update()

                props = ifcopenshell.util.element.get_psets(product)
                all_values = []
                for pset_name, properties in props.items():
                    all_values.extend(properties.values())
                
                if product.Name: all_values.append(product.Name)
                if product.Tag: all_values.append(product.Tag)

                elements_map.append({
                    "name": product.Name,
                    "properties": [str(v).strip() for v in all_values if v]
                })

            return elements_map

        except Exception as e:
            self.log(f"Error llegint IFC: {e}")
            return []

    # --- GENERACIÓ EXCEL ---

    def generate_excel_report(self):
        if not self.path_ifc.get() or not self.path_bc3.get():
            messagebox.showwarning("Atenció", "Selecciona els arxius primer.")
            return

        self.log("Processant dades...")
        
        # 1. Obtenir dades
        bc3_path_full = self.path_bc3.get()
        bc3_data = self.get_bc3_codes(bc3_path_full)
        bc3_codes_set = set(bc3_data.keys())
        ifc_elements = self.get_ifc_data(self.path_ifc.get())

        # 2. Classificar
        matches = []
        errors_ifc = []
        full_list_memory = [] # Llista preparada per Mail Merge Word
        
        found_in_ifc_codes = set()

        for el in ifc_elements:
            element_values_set = set(el['properties'])
            intersection = element_values_set.intersection(bc3_codes_set)
            
            if intersection:
                code = list(intersection)[0]
                desc = bc3_data[code]
                
                # Afegir a llista MATCH
                matches.append([el['name'], code, desc, "CORRECTE"])
                # Afegir a llista MEMÒRIA (Dades reals)
                full_list_memory.append([el['name'], code, desc])
                
                found_in_ifc_codes.add(code)
            else:
                # Afegir a llista ERROR
                errors_ifc.append([el['name'], "Cap codi trobat", "-", "ERROR: NO MATCH"])
                # Afegir a llista MEMÒRIA (Text d'error específic per al Word)
                full_list_memory.append([el['name'], "ERROR: NO MATCH", "Element sense partida"])

        missing_in_model = bc3_codes_set - found_in_ifc_codes
        
        # 3. Crear Excel
        wb = Workbook()
        
        # PESTANYA 1: INFORME TÈCNIC (Visual)
        ws = wb.active
        ws.title = "Informe Tècnic"
        
        fill_green = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
        fill_red = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
        fill_yellow = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
        bold_font = Font(bold=True)

        ws.append(["Element Model", "Codi Partida", "Descripció", "Estat"])
        for cell in ws[1]: cell.font = bold_font

        for row in matches:
            ws.append(row)
            ws[f"D{ws.max_row}"].fill = fill_green

        for row in errors_ifc: 
            ws.append(row)
            ws[f"D{ws.max_row}"].fill = fill_red

        ws.append(["", "", "", ""])
        ws.append(["PARTIDES NO MODELADES", "", "", ""])
        ws[f"A{ws.max_row}"].font = bold_font
        
        for code in missing_in_model:
            ws.append(["NO MODELAT", code, bc3_data[code], "AVÍS"])
            ws[f"D{ws.max_row}"].fill = fill_yellow

        # Ajust ample columnes P1
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 20

        # PESTANYA 2: EXPORT MEMÒRIA (Base de dades per Word)
        ws_mem = wb.create_sheet("EXPORT_MEMORIA")
        # Capçaleres estil base de dades (sense espais)
        ws_mem.append(["Element_Model", "Codi_Partida", "Descripcio_BC3"]) 
        for cell in ws_mem[1]: cell.font = bold_font
        
        # Bolquem tota la llista neta
        for row in full_list_memory:
            ws_mem.append(row)
            
        # Ajust ample columnes P2
        ws_mem.column_dimensions['A'].width = 40
        ws_mem.column_dimensions['B'].width = 25
        ws_mem.column_dimensions['C'].width = 60

        # NOMENCLATURA DEL FITXER
        try:
            # Agafem el nom del fitxer BC3, traiem l'extensió i afegim _excel.xlsx
            base_name = os.path.basename(bc3_path_full)
            name_without_ext = os.path.splitext(base_name)[0]
            filename = f"{name_without_ext}_excel.xlsx"

            wb.save(filename)
            self.log(f"Generat: {filename}")
            
            # Pop-up amb el resum estadístic
            stats_msg = (
                f"Informe generat correctament!\n\n"
                f"✅ Matches: {len(matches)}\n"
                f"❌ Errors IFC: {len(errors_ifc)}\n"
                f"⚠️ Falten al Model: {len(missing_in_model)}\n\n"
                f"Arxiu: {filename}"
            )
            messagebox.showinfo("Resultat de l'Anàlisi", stats_msg)
            
            os.startfile(filename)
        except Exception as e:
            messagebox.showerror("Error", f"Error guardant Excel: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConflictFlaggerApp(root)
    root.mainloop()