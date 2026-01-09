import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from tkinter import ttk
import ifcopenshell
import ifcopenshell.util.element
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from datetime import datetime
import os
import re

class ConflictFlaggerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Conflict Flagger AEC - Comparador Codi/Unitat/Quantitat")
        self.root.geometry("800x600")

        self.path_ifc = tk.StringVar()
        self.path_bc3 = tk.StringVar()
        self.tolerance = tk.DoubleVar(value=0.1) # Tolerància per defecte 0.1 (per decimals)

        # --- UI SETUP ---
        frame_main = tk.Frame(root, padx=15, pady=15)
        frame_main.pack(fill="both", expand=True)

        # Header
        lbl_title = tk.Label(frame_main, text="COMPARADOR IFC vs BC3", font=("Segoe UI", 16, "bold"))
        lbl_title.pack(pady=(0, 20))

        # Inputs
        self._make_file_input(frame_main, "Arxiu Model (IFC)", self.path_ifc, self.load_ifc_dialog)
        self._make_file_input(frame_main, "Arxiu Pressupost (BC3)", self.path_bc3, self.load_bc3_dialog)

        # Options
        frame_opts = tk.Frame(frame_main)
        frame_opts.pack(fill="x", pady=5)
        tk.Label(frame_opts, text="Tolerància Quantitat (+/-):").pack(side="left")
        tk.Entry(frame_opts, textvariable=self.tolerance, width=10).pack(side="left", padx=5)

        # Botó Generar
        btn_generate = tk.Button(frame_main, text="ANALITZAR I GENERAR INFORME", 
                  bg="#217346", fg="white", font=("Segoe UI", 11, "bold"),
                  command=self.run_analysis, pady=12, cursor="hand2")
        btn_generate.pack(fill="x", pady=20)

        # Log Area
        lbl_log = tk.Label(frame_main, text="Registre d'activitat:", font=("Segoe UI", 9, "bold"))
        lbl_log.pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(frame_main, height=12, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

    def _make_file_input(self, parent, label, var, cmd):
        frame = tk.LabelFrame(parent, text=label, padx=5, pady=5)
        frame.pack(fill="x", pady=5)
        entry = tk.Entry(frame, textvariable=var, bg="#f0f0f0")
        entry.pack(side="left", fill="x", expand=True, padx=5)
        tk.Button(frame, text="Examinar...", command=cmd).pack(side="left")

    def log(self, msg):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update()

    def load_ifc_dialog(self):
        f = filedialog.askopenfilename(filetypes=[("IFC Files", "*.ifc")])
        if f: self.path_ifc.set(f)

    def load_bc3_dialog(self):
        f = filedialog.askopenfilename(filetypes=[("BC3 Files", "*.bc3")])
        if f: self.path_bc3.set(f)

    # --- PARSERS ---

    def parse_bc3(self, filepath):
        """
        Llegeix el BC3 i extreu: {CODI: {'desc': str, 'unit': str, 'qty': float}}
        """
        data = {}
        current_code = None
        
        try:
            with open(filepath, 'r', encoding='latin1', errors='replace') as f:
                lines = f.readlines()

            # Pas 1: Llegir Conceptes (~C)
            for line in lines:
                line = line.strip()
                if line.startswith('~C|'):
                    parts = line.split('|')
                    # Format típic: ~C|CODI|UNITAT|RESUM|...
                    if len(parts) > 2:
                        code = parts[1].replace('\\', '').strip()
                        unit = parts[2].strip()
                        desc = parts[3].strip() if len(parts) > 3 else "Sense descripció"
                        
                        # Guardem inicialment amb quantitat 0
                        data[code] = {'desc': desc, 'unit': unit, 'qty': 0.0}

            # Pas 2: Llegir Amidaments (~M) per sumar quantitats
            # Format típic: ~M|CODI|...|QUANTITAT|...
            # A vegades la quantitat total està a la línia ~C en camps posteriors, però ~M és més segur si existeix.
            # Si no hi ha ~M, alguns BC3 posen la quantitat a la descomposició ~D. 
            # PER SIMPLIFICAR: Sumarem valors numèrics al final de les línies ~M associades.
            
            for line in lines:
                if line.startswith('~M|'):
                    parts = line.split('|')
                    if len(parts) > 2:
                        code = parts[1].strip()
                        if code in data:
                            # Intentar trobar el camp de quantitat (sol ser l'últim o penúltim numèric)
                            # Busquem l'últim valor que sigui convertible a float
                            try:
                                # Iterem des del final
                                val = 0.0
                                for part in reversed(parts):
                                    try:
                                        val = float(part.replace(',', '.'))
                                        break # Hem trobat un número des del final
                                    except ValueError:
                                        continue
                                data[code]['qty'] += val
                            except:
                                pass
            
            # Neteja de dades buides o capçaleres
            if '' in data: del data['']
            
            return data
        except Exception as e:
            self.log(f"Error llegint BC3: {str(e)}")
            return {}

    def parse_ifc(self, filepath):
        """
        Llegeix IFC i busca elements.
        Retorna llista de dicts: [{'id': id, 'name': name, 'class': class, 'code': code, 'unit': unit, 'qty': qty}]
        """
        elements = []
        try:
            ifc = ifcopenshell.open(filepath)
            products = ifc.by_type("IfcElement")
            total = len(products)
            self.log(f"Processant {total} elements IFC...")

            # Propietats on buscar el CODI BC3
            code_props = ["Assembly Code", "Reference", "Codi", "Code", "Partida", "Description"]

            for i, p in enumerate(products):
                if i % 100 == 0: self.root.update()
                
                # 1. Trobar Codi
                psets = ifcopenshell.util.element.get_psets(p)
                found_code = None
                
                # Busquem a les propietats
                for pset_name, props in psets.items():
                    for prop_name, prop_val in props.items():
                        if prop_name in code_props and prop_val:
                            found_code = str(prop_val).strip()
                            break
                    if found_code: break
                
                # Si no trobem codi específic, usem el Nom o Tag com a fallback
                if not found_code:
                    found_code = p.Name if p.Name else str(p.GlobalId)

                # 2. Trobar Quantitat i Unitat (BaseQuantities)
                # Prioritat: Volume > Area > Length > Count
                qty = 0.0
                unit = "u"
                
                # Busquem Qtos (Quantity Sets)
                qtos = [x for x in psets.keys() if "Quantity" in x or "Qto" in x]
                found_qty = False
                
                for qto in qtos:
                    props = psets[qto]
                    # Logic per prioritzar Volum -> Area -> Longitud
                    for k, v in props.items():
                        if isinstance(v, (int, float)):
                            if "Volume" in k or "Volumen" in k:
                                qty = v; unit = "m3"; found_qty = True; break
                            elif "Area" in k:
                                qty = v; unit = "m2"; found_qty = True; break
                            elif "Length" in k or "Longitud" in k:
                                qty = v; unit = "m"; found_qty = True; break
                    if found_qty: break
                
                if not found_qty:
                    # Si no hi ha mesures, comptem com unitat
                    qty = 1.0
                    unit = "u"

                elements.append({
                    'guid': p.GlobalId,
                    'name': p.Name,
                    'class': p.is_a(),
                    'code': found_code,
                    'unit': unit,
                    'qty': float(qty)
                })

            return elements
        except Exception as e:
            self.log(f"Error llegint IFC: {str(e)}")
            return []

    # --- ANÀLISI I REPORTS ---

    def run_analysis(self):
        if not self.path_ifc.get() or not self.path_bc3.get():
            messagebox.showwarning("Falten arxius", "Selecciona l'arxiu IFC i el BC3.")
            return

        self.log("Iniciant anàlisi...")
        
        # 1. Carregar dades
        bc3_data = self.parse_bc3(self.path_bc3.get())
        ifc_data = self.parse_ifc(self.path_ifc.get())
        
        if not bc3_data or not ifc_data:
            self.log("Anàlisi cancel·lada per error de lectura.")
            return

        self.log("Comparant dades...")

        # 2. Estructures de resultats
        matches = []          # Coincideix tot
        discrepancies = []    # Coincideix Codi però falla Unitat o Qty
        not_in_bc3 = []       # A l'IFC però no al BC3
        not_in_ifc = []       # Al BC3 però no trobat a l'IFC (per codi)

        # Agrupar dades IFC per Codi per comparar sumes totals
        ifc_grouped = {}
        for item in ifc_data:
            c = item['code']
            if c not in ifc_grouped:
                ifc_grouped[c] = {'qty': 0.0, 'unit': item['unit'], 'items': []}
            
            # Sumem quantitats
            ifc_grouped[c]['qty'] += item['qty']
            ifc_grouped[c]['items'].append(item)
            # Nota: Assumim que tots els elements amb el mateix codi tenen la mateixa unitat a l'IFC.
            # Si no, agafem l'última.

        # 3. Lògica de Comparació
        processed_bc3_codes = set()

        tol = self.tolerance.get()

        for code, ifc_group in ifc_grouped.items():
            if code in bc3_data:
                # MATCH DE CODI
                bc3_item = bc3_data[code]
                processed_bc3_codes.add(code)

                # Comprovar Unitat
                unit_match = (ifc_group['unit'].lower().strip() == bc3_item['unit'].lower().strip())
                # (A vegades m3 vs m3. s'ha de normalitzar, aqui fem check simple)
                
                # Comprovar Quantitat
                diff_qty = abs(ifc_group['qty'] - bc3_item['qty'])
                qty_match = diff_qty <= tol

                if unit_match and qty_match:
                    matches.append({
                        'code': code,
                        'desc': bc3_item['desc'],
                        'unit': ifc_group['unit'],
                        'qty_ifc': ifc_group['qty'],
                        'qty_bc3': bc3_item['qty']
                    })
                else:
                    # DISCREPÀNCIA
                    reasons = []
                    if not unit_match: reasons.append(f"Unitat diferent ({ifc_group['unit']} vs {bc3_item['unit']})")
                    if not qty_match: reasons.append(f"Quantitat diferent (IFC:{ifc_group['qty']:.2f} vs BC3:{bc3_item['qty']:.2f})")
                    
                    discrepancies.append({
                        'code': code,
                        'desc': bc3_item['desc'],
                        'type': ", ".join(reasons),
                        'val_ifc': f"{ifc_group['qty']:.2f} {ifc_group['unit']}",
                        'val_bc3': f"{bc3_item['qty']:.2f} {bc3_item['unit']}"
                    })

            else:
                # NO EXISTEIX AL PRESSUPOST
                # Agafem el primer element per treure informació bàsica
                first_elem = ifc_group['items'][0]
                not_in_bc3.append({
                    'code': code,
                    'name': first_elem['name'],
                    'class': first_elem['class'],
                    'qty': ifc_group['qty'],
                    'unit': ifc_group['unit']
                })

        # Buscar elements al BC3 que no estan a l'IFC
        for code, data in bc3_data.items():
            if code not in processed_bc3_codes:
                not_in_ifc.append({
                    'code': code,
                    'desc': data['desc'],
                    'qty': data['qty'],
                    'unit': data['unit']
                })

        # 4. Generar Excel
        self.generate_excel(matches, discrepancies, not_in_bc3, not_in_ifc)

    def generate_excel(self, matches, discrepancies, not_in_bc3, not_in_ifc):
        wb = Workbook()
        
        # ESTILS
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        
        fill_red = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        font_red = Font(color="9C0006")
        
        fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        font_green = Font(color="006100")

        fill_yellow = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
        font_yellow = Font(color="9C5700")

        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

        def setup_sheet(ws, headers):
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.value = header
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center")
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 40
            ws.column_dimensions['C'].width = 15

        # 1. PESTANYA RESUMEN
        ws_res = wb.active
        ws_res.title = "Resumen"
        ws_res.append(["RESUM EXECUTIU"])
        ws_res['A1'].font = Font(size=14, bold=True)
        ws_res.append([])
        
        data_stats = [
            ("Total Partides BC3", len(matches) + len(discrepancies) + len(not_in_ifc)),
            ("Total Tipus IFC", len(matches) + len(discrepancies) + len(not_in_bc3)),
            ("Emparellats Correctes", len(matches)),
            ("Discrepàncies detectades", len(discrepancies)),
            ("Només a l'IFC (No Pressupostat)", len(not_in_bc3)),
            ("Només al BC3 (No Modelat)", len(not_in_ifc))
        ]
        
        for label, val in data_stats:
            ws_res.append([label, val])

        # 2. PESTANYA DISCREPANCIES
        ws_disc = wb.create_sheet("Discrepancias")
        setup_sheet(ws_disc, ["Codi", "Descripció", "Tipus de Discrepància", "Valor IFC", "Valor BC3", "Gravetat"])
        
        for item in discrepancies:
            row = [item['code'], item['desc'], item['type'], item['val_ifc'], item['val_bc3'], "ERROR"]
            ws_disc.append(row)
            # Pintar vermell
            for col in range(1, 7):
                ws_disc.cell(row=ws_disc.max_row, column=col).fill = fill_red
                ws_disc.cell(row=ws_disc.max_row, column=col).font = font_red
                ws_disc.cell(row=ws_disc.max_row, column=col).border = thin_border

        # 3. PESTANYA EMPARELLATS
        ws_match = wb.create_sheet("Elementos Emparejados")
        setup_sheet(ws_match, ["Codi", "Descripció", "Unitat", "Quantitat IFC", "Quantitat BC3", "Estat"])
        
        for item in matches:
            row = [item['code'], item['desc'], item['unit'], item['qty_ifc'], item['qty_bc3'], "OK"]
            ws_match.append(row)
            for col in range(1, 7):
                ws_match.cell(row=ws_match.max_row, column=col).fill = fill_green
                ws_match.cell(row=ws_match.max_row, column=col).font = font_green

        # 4. PESTANYA SIN PRESUPUESTAR (IFC sense BC3)
        ws_nobc3 = wb.create_sheet("Sin Presupuestar")
        setup_sheet(ws_nobc3, ["Codi/Tag", "Nom Element", "Classe IFC", "Quantitat Detectada", "Unitat", "Acció"])
        
        for item in not_in_bc3:
            row = [item['code'], item['name'], item['class'], item['qty'], item['unit'], "Afegir al Pressupost"]
            ws_nobc3.append(row)
            for col in range(1, 7):
                ws_nobc3.cell(row=ws_nobc3.max_row, column=col).fill = fill_yellow

        # 5. PESTANYA SIN MODELAR (BC3 sense IFC)
        ws_noifc = wb.create_sheet("Sin Modelar")
        setup_sheet(ws_noifc, ["Codi", "Descripció", "Quantitat", "Unitat", "Acció"])
        
        for item in not_in_ifc:
            row = [item['code'], item['desc'], item['qty'], item['unit'], "Modelar a l'IFC"]
            ws_noifc.append(row)
            for col in range(1, 6):
                ws_noifc.cell(row=ws_noifc.max_row, column=col).fill = fill_yellow

        # Guardar
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"Informe_AEC_{timestamp}.xlsx"
            wb.save(filename)
            self.log(f"Informe generat: {filename}")
            messagebox.showinfo("Èxit", f"Informe generat correctament:\n{filename}")
            os.startfile(filename)
        except Exception as e:
            messagebox.showerror("Error", f"No s'ha pogut guardar l'Excel: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConflictFlaggerApp(root)
    root.mainloop()