import pandas as pd
import os

# Ensure directories exist
os.makedirs('data/input', exist_ok=True)

# 1. Revit Mock
revit_data = {
    'Familia': ['Muros', 'Puertas', 'Ventanas', 'Muros', 'Test', 'MismatchNA'],
    'Tipo': ['Muro Básico', 'Puerta Paso', 'Ventana Fija', 'Muro Cortina', 'Test NAN', 'Test Mismatch'],
    'Codi': ['W-01', 'D-101', 'Win-55', 'W-XX', 'T-NAN', 'T-Bad'], 
    'Material': ['Hormigón', 'Madera', 'Vidrio', 'Aluminio', None, 'Madera']
}
df_revit = pd.DataFrame(revit_data)
df_revit.to_excel('data/input/revit_mock.xlsx', index=False)
print("Created data/input/revit_mock.xlsx")

# 2. Memoria Mock
memoria_data = {
    'Codi': ['W-01', 'D-101', 'Win-55', 'F-NULL', 'T-NAN', 'T-Bad'], 
    'Material': ['Hormigón', 'Metal', 'Vidrio', 'Acero', 'Plástico', 'Acero'] # T-Bad: Madera vs Acero
}
df_memoria = pd.DataFrame(memoria_data)
df_memoria.to_excel('data/input/memoria_mock.xlsx', index=False)
print("Created data/input/memoria_mock.xlsx")
