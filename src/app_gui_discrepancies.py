import tkinter as tk
from tkinter import filedialog, messagebox
from fase1_checker import generate_basic_discrepancy_report
import os
from datetime import datetime


class DiscrepancyCheckerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Comparador IFC vs BC3")
        self.root.geometry("600x300")

        self.path_ifc = tk.StringVar()
        self.path_bc3 = tk.StringVar()
        self.tolerance = tk.DoubleVar(value=0.1)

        self.build_ui()

    def build_ui(self):
        tk.Label(self.root, text="Comparador d'arxius IFC i BC3", font=("Segoe UI", 14, "bold")).pack(pady=10)

        frame_files = tk.Frame(self.root)
        frame_files.pack(pady=10, fill="x", padx=20)

        self.add_file_input(frame_files, "Arxiu IFC", self.path_ifc)
        self.add_file_input(frame_files, "Arxiu BC3", self.path_bc3)

        frame_tol = tk.Frame(self.root)
        frame_tol.pack(pady=5)
        tk.Label(frame_tol, text="Tolerància (quantitat):").pack(side="left", padx=5)
        tk.Entry(frame_tol, textvariable=self.tolerance, width=10).pack(side="left")

        tk.Button(self.root, text="Generar informe", font=("Segoe UI", 11, "bold"),
                  bg="#217346", fg="white", pady=8, command=self.run_report).pack(pady=15)

    def add_file_input(self, parent, label, var):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=5)
        tk.Label(frame, text=label, width=12).pack(side="left")
        entry = tk.Entry(frame, textvariable=var, width=50, state='readonly')
        entry.pack(side="left", padx=5)
        tk.Button(frame, text="Explora...", command=lambda t=label: self.select_file(var, "ifc" if "IFC" in t else "bc3")).pack(side="left")

    def select_file(self, var, tipus):
        if tipus == "ifc":
            filetypes = [("Fitxers IFC", "*.ifc")]
        elif tipus == "bc3":
            filetypes = [("Fitxers BC3", "*.bc3")]
        else:
            filetypes = [("Tots els arxius", "*.*")]
    
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def run_report(self):
        if not self.path_ifc.get() or not self.path_bc3.get():
            messagebox.showwarning("Falten arxius", "Selecciona l'arxiu IFC i l'arxiu BC3.")
            return

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_excel = f"informe_discrepancies_{timestamp}.xlsx"

            generate_basic_discrepancy_report(
                ifc_path=self.path_ifc.get(),
                bc3_path=self.path_bc3.get(),
                output_excel=output_excel,
                tolerance=self.tolerance.get()
            )

            messagebox.showinfo("Informe generat", f"Informe creat correctament:\n{output_excel}")
            os.startfile(output_excel)

        except Exception as e:
            messagebox.showerror("Error", f"S'ha produït un error:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = DiscrepancyCheckerApp(root)
    root.mainloop()
