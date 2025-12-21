# Desktop Application (Future Plan)

## Overview

This document outlines options for packaging Conflict Flagger AEC as a desktop application for office use. Two approaches are planned for initial implementation.

## Option 1: Standalone Executable (PyInstaller)

### Description

Package the CLI as a standalone executable that runs without requiring Python installation.

### Advantages

- No Python installation required on user machines
- Single file distribution
- Works on Windows, Mac, and Linux
- Minimal development effort

### Implementation

```bash
# Install PyInstaller
pip install pyinstaller

# Create standalone executable
pyinstaller --onefile --name conflict-flagger src/main.py

# Output: dist/conflict-flagger.exe (Windows) or dist/conflict-flagger (Mac/Linux)
```

### Usage

Users can run the executable from command line or create batch scripts:

**Windows batch file (compare.bat):**
```batch
@echo off
conflict-flagger.exe --ifc "%1" --bc3 "%2" --output report.xlsx
pause
```

**Mac/Linux shell script (compare.sh):**
```bash
#!/bin/bash
./conflict-flagger --ifc "$1" --bc3 "$2" --output report.xlsx
open report.xlsx
```

### Distribution

1. Build executable on target platform
2. Distribute single file to users
3. Users run from command line or via scripts

### Considerations

- Build separately for each OS (Windows, Mac, Linux)
- Large file size (~50-100MB due to bundled Python + dependencies)
- ifcopenshell may require special handling during packaging

---

## Option 2: Streamlit Web Interface

### Description

Create a local web application with a modern, user-friendly interface that runs in the browser but executes locally.

### Advantages

- Modern, intuitive drag-and-drop interface
- No command line knowledge required
- Real-time progress feedback
- Easy to develop and maintain
- Cross-platform (runs in any browser)

### Implementation

**Install Streamlit:**
```bash
pip install streamlit
```

**Create app.py:**
```python
import streamlit as st
import tempfile
import os
from src.parsers.ifc_parser import IFCParser
from src.parsers.bc3_parser import BC3Parser
from src.matching.matcher import Matcher
from src.comparison.comparator import Comparator
from src.reporting.reporter import Reporter

st.set_page_config(
    page_title="Conflict Flagger AEC",
    page_icon="🏗️",
    layout="wide"
)

st.title("🏗️ Conflict Flagger AEC")
st.markdown("Detecta discrepancias entre modelos BIM (IFC) y presupuestos (BC3)")

# File uploaders
col1, col2 = st.columns(2)

with col1:
    st.subheader("📐 Modelo IFC")
    ifc_file = st.file_uploader("Selecciona archivo IFC", type=['ifc'])

with col2:
    st.subheader("💰 Presupuesto BC3")
    bc3_file = st.file_uploader("Selecciona archivo BC3", type=['bc3'])

# Options
st.sidebar.header("⚙️ Opciones")
tolerance = st.sidebar.slider("Tolerancia numérica (%)", 1, 10, 1) / 100
use_name_matching = st.sidebar.checkbox("Emparejar por nombre", value=True)

# Process button
if ifc_file and bc3_file:
    if st.button("🔍 Analizar", type="primary"):
        with st.spinner("Procesando..."):
            # Save uploaded files temporarily
            with tempfile.TemporaryDirectory() as tmpdir:
                ifc_path = os.path.join(tmpdir, "model.ifc")
                bc3_path = os.path.join(tmpdir, "budget.bc3")
                report_path = os.path.join(tmpdir, "report.xlsx")

                with open(ifc_path, "wb") as f:
                    f.write(ifc_file.getbuffer())
                with open(bc3_path, "wb") as f:
                    f.write(bc3_file.getbuffer())

                # Process
                progress = st.progress(0)

                st.text("Parseando IFC...")
                ifc_result = IFCParser().parse(ifc_path)
                progress.progress(25)

                st.text("Parseando BC3...")
                bc3_result = BC3Parser().parse(bc3_path)
                progress.progress(50)

                st.text("Emparejando elementos...")
                matcher = Matcher(match_by_name=use_name_matching)
                match_result = matcher.match(ifc_result, bc3_result)
                progress.progress(75)

                st.text("Comparando y generando informe...")
                comparator = Comparator(tolerance=tolerance)
                comparison = comparator.compare(match_result)
                Reporter().generate_report(match_result, comparison, report_path)
                progress.progress(100)

                # Show results
                st.success("✅ Análisis completado")

                # Summary metrics
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Emparejados", len(match_result.matched))
                col2.metric("Sin Presupuestar", len(match_result.ifc_only))
                col3.metric("Sin Modelar", len(match_result.bc3_only))
                col4.metric("Discrepancias", len(comparison.conflicts))

                # Download button
                with open(report_path, "rb") as f:
                    st.download_button(
                        label="📥 Descargar Informe Excel",
                        data=f.read(),
                        file_name="informe_comparacion.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
else:
    st.info("👆 Sube ambos archivos para comenzar el análisis")

# Footer
st.markdown("---")
st.markdown("*Conflict Flagger AEC - Validación automática de proyectos BIM*")
```

### Running the App

```bash
# Development
streamlit run app.py

# Opens browser at http://localhost:8501
```

### Distribution Options

**Option A: Python + Streamlit (for technical users)**
```bash
pip install -r requirements.txt
streamlit run app.py
```

**Option B: Executable with Streamlit**
```bash
pip install pyinstaller
# Create launcher script and package
```

**Option C: Docker container**
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt streamlit
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### Interface Preview

```
┌─────────────────────────────────────────────────────────────┐
│  🏗️ Conflict Flagger AEC                                    │
│  Detecta discrepancias entre modelos BIM y presupuestos    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐        │
│  │ 📐 Modelo IFC       │    │ 💰 Presupuesto BC3  │        │
│  │                     │    │                     │        │
│  │  [Drag & Drop]      │    │  [Drag & Drop]      │        │
│  │  or click to browse │    │  or click to browse │        │
│  │                     │    │                     │        │
│  └─────────────────────┘    └─────────────────────┘        │
│                                                             │
│              [ 🔍 Analizar ]                                │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ✅ Análisis completado                                     │
│                                                             │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐               │
│  │   47   │ │   56   │ │   21   │ │  175   │               │
│  │Emparej.│ │Sin Pres│ │Sin Mod.│ │Discrep.│               │
│  └────────┘ └────────┘ └────────┘ └────────┘               │
│                                                             │
│              [ 📥 Descargar Informe Excel ]                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Comparison

| Feature | PyInstaller | Streamlit |
|---------|-------------|-----------|
| User Interface | Command line | Web browser |
| Ease of use | Technical users | All users |
| Development time | 1 hour | 2-3 hours |
| File size | ~100MB | Requires Python |
| Drag & drop | No | Yes |
| Progress feedback | Text only | Visual progress bar |
| Cross-platform | Build per OS | Any browser |
| Updates | Redistribute exe | Update code |

## Recommendation

1. **Start with Streamlit** for office use - more user-friendly
2. **Add PyInstaller** for distribution to external users without Python

## Future Enhancements

- [ ] Batch processing multiple file pairs
- [ ] Save/load comparison settings
- [ ] Email report automatically
- [ ] Integration with cloud storage (OneDrive, Google Drive)
- [ ] Multi-language interface support
- [ ] Dark mode theme
