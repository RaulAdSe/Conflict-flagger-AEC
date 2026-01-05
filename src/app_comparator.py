import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ifcopenshell
import ifcopenshell.util.element
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from datetime import datetime
import os

class ConflictFlaggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conflict Flagger AEC - Generador Excel")
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
        tk.Button(frame_main, text="GENERAR EXCEL AMB COLORS", 
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

    # --- LÒGICA DE PARSEIG ---

    def get_bc3_codes(self, filepath):
        """Llegeix els codis (~C) del fitxer BC3"""
        codes = {} # Diccionari {codi: descripcio}
        try:
            with open(filepath, 'r', encoding='latin1') as f:
                for line in f:
                    if line.startswith('~C|'):
                        parts = line.split('|')
                        if len(parts) > 1:
                            c = parts[1].replace('\\', '').strip()
                            # Intentem agafar la descripció si existeix (sol ser el camp 3 o 4)
                            desc = parts[2] if len(parts) > 2 else "Sense descripció"
                            if c: codes[c] = desc
            return codes
        except Exception as e:
            self.log(f"Error llegint BC3: {e}")
            return {}

    def get_ifc_data(self, filepath):
        """Busca codis dins les propietats de l'IFC"""
        found_codes = set()
        elements_map = [] # Llista de tuples (NomElement, CodiTrobat, TipusIFC)
        
        try:
            ifc = ifcopenshell.open(filepath)
            # Busquem elements físics comuns
            products = ifc.by_type("IfcElement")
            
            total = len(products)
            self.log(f"Analitzant {total} elements a l'IFC...")

            for i, product in enumerate(products):
                if i % 50 == 0: self.root.update() # Refresc UI

                # 1. Obtenir totes les propietats de l'element com un diccionari
                # Això busca a Psets, Type Objects, etc.
                props = ifcopenshell.util.element.get_psets(product)
                
                # Busquem valors que semblin codis dins de totes les propietats
                found_match = None
                
                # Aplanem el diccionari de propietats per buscar valors
                all_values = []
                for pset_name, properties in props.items():
                    all_values.extend(properties.values())
                
                # Afegim també el nom i Tag per si de cas
                if product.Name: all_values.append(product.Name)
                if product.Tag: all_values.append(product.Tag)

                # Guardem informació per l'informe
                # Aquí la clau: Retornem TOTS els valors per comparar-los després amb el BC3
                # O per optimitzar: Si coincideix amb algun codi BC3 conegut (ho farem al pas de creuament)
                
                elements_map.append({
                    "name": product.Name,
                    "type": product.is_a(),
                    "properties": [str(v).strip() for v in all_values if v]
                })

            return elements_map

        except Exception as e:
            self.log(f"Error llegint IFC: {e}")
            return []

    # --- GENERACIÓ EXCEL ---

    def generate_excel_report(self):
        if not self.path_ifc.get() or not self.path_bc3.get():
            messagebox.showwarning("Atenció", "Selecciona els arxius.")
            return

        self.log("Iniciant anàlisi profunda...")
        
        # 1. Carregar dades
        bc3_data = self.get_bc3_codes(self.path_bc3.get()) # Dict {code: desc}
        bc3_codes_set = set(bc3_data.keys())
        self.log(f"BC3: {len(bc3_codes_set)} partides carregades.")

        ifc_elements = self.get_ifc_data(self.path_ifc.get())
        self.log(f"IFC: {len(ifc_elements)} elements processats.")

        # 2. Creuar dades (MATCHING)
        matches = []
        errors_ifc = [] # A l'IFC però no al BC3 (si té algun codi potencial)
        
        # Elements trobats a l'IFC que coincideixen amb BC3
        found_in_ifc_codes = set()

        for el in ifc_elements:
            # Busquem si algun valor de les propietats de l'element coincideix amb un codi BC3
            # Intersecció entre els valors de l'element i les claus del BC3
            element_values_set = set(el['properties'])
            intersection = element_values_set.intersection(bc3_codes_set)
            
            if intersection:
                code = list(intersection)[0] # Agafem el primer match
                matches.append([el['name'], code, bc3_data[code], "CORRECTE"])
                found_in_ifc_codes.add(code)
            else:
                # Si no trobem match, ho marquem com error (o element sense partida)
                errors_ifc.append([el['name'], "Cap codi trobat", "-", "ERROR: NO MATCH"])

        # Identificar partides del BC3 que no estan al model
        missing_in_model = bc3_codes_set - found_in_ifc_codes
        
        # 3. Crear Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Informe Comparatiu"

        # Estils
        fill_red = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid")
        fill_green = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
        fill_yellow = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
        bold_font = Font(bold=True)

        # Capçaleres
        headers = ["Element Model (IFC)", "Codi Partida", "Descripció BC3", "Estat"]
        ws.append(headers)
        for cell in ws[1]: cell.font = bold_font

        # Escriure Matches (Verd)
        for row in matches:
            ws.append(row)
            ws[f"D{ws.max_row}"].fill = fill_green

        # Escriure Errors IFC (Vermell)
        # Limitem a 100 errors per no saturar si tot està malament
        for row in errors_ifc[:100]: 
            ws.append(row)
            ws[f"D{ws.max_row}"].fill = fill_red
        
        if len(errors_ifc) > 100:
            ws.append(["... i molts més elements sense codi ...", "", "", ""])

        # Escriure Missing BC3 (Groc)
        ws.append(["", "", "", ""])
        ws.append(["PARTIDES AL PRESSUPOST (BC3) NO TROBADES AL MODEL", "", "", ""])
        ws[f"A{ws.max_row}"].font = bold_font
        
        for code in missing_in_model:
            ws.append(["NO MODELAT", code, bc3_data[code], "AVÍS: FALTEN AL MODEL"])
            ws[f"D{ws.max_row}"].fill = fill_yellow

        # Ajustar columnes
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 50
        ws.column_dimensions['D'].width = 20

        # Guardar
        filename = f"Informe_AEC_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        try:
            wb.save(filename)
            self.log(f"Excel guardat: {filename}")
            messagebox.showinfo("Èxit", f"Informe generat!\n\nMatches: {len(matches)}\nErrors IFC: {len(errors_ifc)}\nFalten al Model: {len(missing_in_model)}")
            os.startfile(filename)
        except Exception as e:
            messagebox.showerror("Error", f"No s'ha pogut guardar l'Excel: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConflictFlaggerApp(root)
    root.mainloop()