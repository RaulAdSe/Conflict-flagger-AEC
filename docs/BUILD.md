# Guía de Compilación - Conflict Flagger AEC

Esta guía explica cómo compilar la aplicación para Windows y macOS.

---

## Requisitos Previos

### Para Windows (compilación nativa)
- Python 3.11 o superior: https://www.python.org/downloads/
- Git (opcional): https://git-scm.com/downloads

### Para macOS (compilación nativa)
- Python 3.11 o superior
- Xcode Command Line Tools: `xcode-select --install`

### Para macOS con Wine (compilación cruzada para Windows)
- Wine: `brew install --cask wine-stable`
- Python for Windows instalado en Wine

---

## Compilación en Windows

### 1. Clonar el repositorio

```powershell
git clone https://github.com/RaulAdSe/Conflict-flagger-AEC.git
cd Conflict-flagger-AEC
```

O descargar el ZIP desde GitHub y extraerlo.

### 2. Crear entorno virtual (recomendado)

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

```powershell
pip install --upgrade pip
pip install pyinstaller openpyxl pillow tkinterdnd2 ifcopenshell
```

### 4. Compilar el ejecutable

```powershell
python -m PyInstaller --clean --noconfirm --name ConflictFlaggerAEC --windowed --onedir src/app_comparator.py
```

### 5. Resultado

El ejecutable estará en:
```
dist\ConflictFlaggerAEC\ConflictFlaggerAEC.exe
```

Para distribuir, copia toda la carpeta `ConflictFlaggerAEC`.

---

## Compilación en macOS

### 1. Instalar dependencias

```bash
pip3 install pyinstaller openpyxl pillow tkinterdnd2 ifcopenshell
```

### 2. Compilar usando el script

```bash
python3 build_app.py --clean
```

### 3. Resultado

La aplicación estará en:
```
dist/Flagger.app
```

---

## Compilación cruzada (macOS → Windows con Wine)

### 1. Instalar Wine

```bash
brew install --cask wine-stable
```

### 2. Instalar Python para Windows en Wine

```bash
# Descargar Python 3.11 para Windows
curl -L -o /tmp/python-3.11.9-amd64.exe "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

# Instalar (silencioso)
wine /tmp/python-3.11.9-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
```

### 3. Instalar dependencias en Wine

```bash
wine "C:\\Program Files\\Python311\\python.exe" -m pip install --upgrade pip
wine "C:\\Program Files\\Python311\\python.exe" -m pip install pyinstaller openpyxl pillow tkinterdnd2 ifcopenshell
```

### 4. Compilar el .exe

```bash
cd /path/to/Conflict-flagger-AEC
wine "C:\\Program Files\\Python311\\python.exe" -m PyInstaller --clean --noconfirm --name ConflictFlaggerAEC --windowed --onedir src/app_comparator.py
```

### 5. Resultado

El ejecutable estará en:
```
dist/ConflictFlaggerAEC/ConflictFlaggerAEC.exe
```

---

## Estructura del Ejecutable

```
ConflictFlaggerAEC/
├── ConflictFlaggerAEC.exe    # Ejecutable principal
└── _internal/                 # Dependencias y librerías
    ├── python311.dll
    ├── ifcopenshell/
    ├── openpyxl/
    └── ...
```

**Importante**: Para distribuir, copia TODA la carpeta `ConflictFlaggerAEC`, no solo el `.exe`.

---

## Solución de Problemas

### Error: "No module named 'ifcopenshell'"
```bash
pip install ifcopenshell
```

### Error: "DLL load failed"
Asegúrate de tener Visual C++ Redistributable instalado:
https://aka.ms/vs/17/release/vc_redist.x64.exe

### Error en Wine: "wine: failed to open"
Usa la ruta de Windows con barras invertidas:
```bash
wine "C:\\Program Files\\Python311\\python.exe" ...
```

### La aplicación no abre archivos IFC
Verifica que `ifcopenshell` esté correctamente instalado:
```bash
python -c "import ifcopenshell; print(ifcopenshell.version)"
```

---

## Scripts Útiles

### build_windows.sh (para macOS con Wine)
```bash
#!/bin/bash
wine "C:\\Program Files\\Python311\\python.exe" -m PyInstaller \
    --clean --noconfirm \
    --name ConflictFlaggerAEC \
    --windowed \
    --onedir \
    src/app_comparator.py
```

### build_windows.bat (para Windows)
```batch
@echo off
python -m PyInstaller ^
    --clean --noconfirm ^
    --name ConflictFlaggerAEC ^
    --windowed ^
    --onedir ^
    src\app_comparator.py
```

---

## Versiones Probadas

| Componente | Versión |
|------------|---------|
| Python | 3.11.9 |
| PyInstaller | 6.16.0 |
| ifcopenshell | 0.8.4 |
| openpyxl | 3.1.5 |
| Wine (macOS) | 10.0 |

---

## Contacto

Para problemas de compilación, abre un issue en:
https://github.com/RaulAdSe/Conflict-flagger-AEC/issues
