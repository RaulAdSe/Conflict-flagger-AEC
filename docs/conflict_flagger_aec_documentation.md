# Technical Documentation: Conflict Flagger AEC

## 1. Introduction

This application is a desktop tool developed in Python using Tkinter. Its main objective is to automate the consistency review between a BIM model (IFC format) and a construction budget (BC3 format).

The program performs a data audit to verify that modeled elements contain the item codes corresponding to the budget, generating a visual report in Excel.

## 2. Dependencies and Libraries

The code makes use of several external and standard libraries:

| Library | Main Use |
|---------|----------|
| `tkinter` | User Interface (Standard Python GUI) |
| `ifcopenshell` | Analysis, reading, and manipulation of BIM files (IFC) |
| `openpyxl` | Creation and styling of the Excel report (.xlsx) |
| `datetime` | Timestamp management for filenames and logs |
| `os` | Operating system operations (opening files automatically) |

## 3. Data Flow Architecture

The program follows a linear data processing flow:

```mermaid
graph TD
    A[User] -->|Selects Files| B(Tkinter Interface)
    B -->|Clicks Generate| C{Processing}
    
    C -->|Reads| D[BC3 Parser]
    D -->|Extracts Codes| E[Budget Items List]
    
    C -->|Reads| F[IFC Parser]
    F -->|Extracts Properties| G[Model Elements List]
    
    E & G --> H[Comparison Engine]
    H -->|Cross-references Data| I[Excel Generation]
    I --> J[Final Report (.xlsx)]
```

## 4. Detailed Code Analysis

### 4.1. The `ConflictFlaggerApp` Class

This is the main class that encapsulates all the application logic.

**Initialization (`__init__`)**

- Configures the main window to 650x550 pixels.
- Defines control variables `self.path_ifc` and `self.path_bc3` to store file paths.
- Creates the visual interface divided into:
  - **Inputs:** Text fields and buttons to select files.
  - **Action:** A large green button to start the process.
  - **Log:** A scrolled text area to display real-time progress.

### 4.2. BC3 Reading Module (`get_bc3_codes`)

The BC3 (FIEBDC) format is the standard for exchanging construction databases in Spain.

- **Encoding:** Uses `latin1` (common in older BC3 files or Spanish standards) to avoid errors with accents or special characters.
- **Extraction Logic:**
  - Reads the file line by line.
  - Detects lines starting with `~C|` (Concept/Item definition).
  - Performs a `split('|')` to separate fields.
  - Stores the Code (index 1) and the Description (index 2).
- **Return:** A dictionary `{ "CODE": "Description" }`.

### 4.3. IFC Reading Module (`get_ifc_data`)

This function uses `ifcopenshell` to mine data from the 3D model.

- **Element Filter:** Selects all elements of type `IfcElement`. This includes walls, doors, windows, but excludes abstract elements or type definitions.
- **Mass Extraction ("Flattening"):**
  - The code does not look for a specific property (e.g., "AssemblyCode").
  - Instead, it uses `ifcopenshell.util.element.get_psets(product)` to obtain all object properties.
  - It creates a flat list (`all_values`) with all values found within the object, including the Name and Tag.
- **Objective:** This strategy allows finding the item code regardless of where the modeler wrote it (`Pset_WallCommon`, instance parameter, type name, etc.).

### 4.4. Comparison Engine (`generate_excel_report`)

Here lies the intelligence of the program. It performs a **Set Theory** operation to determine matches.

- **Loading:** Loads the BC3 dictionaries and the list of IFC elements.
- **Iteration:** Iterates through each element of the IFC.
- **Intersection (Matching):**

```python
element_values_set = set(el['properties'])
intersection = element_values_set.intersection(bc3_codes_set)
```

It compares the set of all element properties with the set of all budget codes. If there is an intersection, it means the element has a valid code assigned.

### 4.5. Classification Logic (States)

The program classifies results into three categories for the Excel report:

#### MATCH (Green)

- The IFC element contains, somewhere, a value that matches exactly with a BC3 code.
- Written to Excel with a light green background.

#### IFC ERROR (Red)

- The element exists in the model but none of its properties match any BC3 code.
- Indicates the element is unlinked or the code is wrong.
- **Note:** Errors are limited to 100 rows to avoid freezing Excel in large unencoded models.

#### MISSING IN MODEL (Yellow)

- Codes that exist in the BC3 file but were not found in any model element.
- **Calculation:** `Total_BC3_Codes - Found_In_IFC_Codes`.
- Indicates budgeted items that have not been modeled (e.g., preliminary works, health and safety, or modeling oversights).

## 5. Excel Report Generation

`openpyxl` is used to create a professional report.

- **Styles:** `PatternFill` objects are defined for traffic light colors (Green, Red, Yellow).
- **Structure:**
  - **Columns:** Model Element, Item Code, BC3 Description, Status.
  - Columns are auto-adjusted (`ws.column_dimensions`).
- **Saving:** The file is saved with a unique timestamp (`%Y%m%d_%H%M%S`) to avoid overwriting previous reports and opens automatically upon completion.

## 6. Quick User Guide

1. Run the script `app_comparator.py`.
2. Click **"Search..."** for Model File (IFC) and select the `.ifc` file.
3. Click **"Search..."** for Budget File (BC3) and select the `.bc3` file.
4. Press the large **"GENERATE EXCEL WITH COLORS"** button.
5. Wait for the log to show "Excel saved".
6. The Excel file will open automatically with the results.
