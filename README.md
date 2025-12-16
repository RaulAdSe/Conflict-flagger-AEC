# Especificación de Requerimientos de Software (SRS)

**Nombre del Proyecto:** Sistema de Auditoría de Coherencia Documental (BIM-Cost-Spec)  
**Versión:** 1.0 (MVP)  
**Fecha:** 16 de Diciembre, 2025  
**Estado:** Borrador Inicial

---

## 1. Introducción

### 1.1 Propósito
El propósito de este software es automatizar la validación de datos cruzados entre el modelo geométrico (**Revit**), el presupuesto (**Presto**) y la memoria descriptiva (**Excel**). El objetivo es asegurar la integridad del proyecto ejecutivo detectando discrepancias en códigos y variables técnicas.

### 1.2 Alcance
El sistema funcionará como una herramienta de **lectura y análisis** (Auditoría).
* **Entradas:** * `Revit`: Tablas de planificación exportadas a `.xlsx`.
    * `Presto`: Archivos de intercambio estándar `.bc3`.
    * `Memoria`: Base de datos de especificaciones en `.xlsx`.
* **Proceso:** Fusión de datos (Data Mashup) y comparación lógica.
* **Salida:** Un informe en Excel con alertas visuales (Semáforo de colores).

---

## 2. Descripción General

### 2.1 Flujo de Datos
El sistema ingiere datos de tres fuentes desconectadas y los unifica mediante una **Clave Primaria (Codi)**.

1.  **Ingesta:** Lectura de archivos fuente.
2.  **Normalización:** Limpieza de strings (trimming, uppercase).
3.  **Cruce:** Alineación de filas basada en el `Codi`.
4.  **Validación:** Comparación de valores paramétricos.
5.  **Reporte:** Generación de la Matriz de Control.

### 2.2 Roles de Usuario
* **BIM Manager:** Valida la información contenida en el modelo.
* **Dpto. de Costes:** Valida que las partidas presupuestadas existen en el modelo.
* **Redactor de Memoria:** Asegura que la descripción técnica coincide con lo modelado/presupuestado.

---

## 3. Requerimientos Funcionales (RF)

### 3.1 Módulo de Ingesta (Inputs)
* **RF-001 (Revit):** El sistema debe leer archivos Excel procedentes de Revit. Debe identificar columnas de `Familia`, `Tipo` y `Codi` (Keynote/Type Mark).
* **RF-002 (Presto):** El sistema debe parsear la estructura jerárquica del formato **FIEBDC-3 (.bc3)** para extraer `Código`, `Resumen`, `Precio` y `Unidad`.
* **RF-003 (Memoria):** El sistema debe leer tablas Excel estructuradas de especificaciones técnicas.

### 3.2 Lógica de Comparación
* **RF-004 (Validación de Existencia):**
    * `Revit` vs `Presto`: Identificar elementos modelados sin partida (No cobrables) y partidas sin modelo (No construibles).
* **RF-005 (Validación de Variables):**
    * Comparar N variables definidas (ej. Material, Kg/m2, Resistencia).
    * **Tolerancia:** Las comparaciones numéricas deben admitir una tolerancia de $\pm 0.01$.

### 3.3 Módulo de Reporte (Outputs)
* **RF-006 (Matriz de Control):** Generación de un archivo `.xlsx`.
* **RF-007 (Semáforo de Estado):**
    * 🔴 **ROJO (Error):** Los valores son diferentes entre plataformas.
    * 🟢 **VERDE (OK):** Los valores son idénticos.
    * 🟡 **AMARILLO (Warning):** El dato no existe en una de las fuentes (Vacío).

---

## 4. Requerimientos de Interfaz (UI)

### 4.1 Estructura de la Tabla de Control
La tabla de salida debe seguir estrictamente esta estructura para facilitar la lectura visual:

| Familia | Subgrupo | Codi | Variable (Nombre) | Valor Revit | Valor Presto | Valor Memoria | CHECK |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| *Revit* | *Presto* | *Key* | *Definición* | *Dato* | *Dato* | *Dato* | 🔴/🟢 |

> **Nota:** Se generará una fila por cada variable a comprobar dentro de cada código.

---

## 5. Requerimientos No Funcionales

* **RNF-01 (Stack Tecnológico):** Python 3.9+ con librería `Pandas`.
* **RNF-02 (Dependencias):** El software no debe requerir licencias activas de Revit o Presto para ejecutarse (standalone).
* **RNF-03 (Rendimiento):** Procesamiento de < 1 minuto para proyectos de envergadura media (5.000 partidas).

---

## 6. Historial de Versiones

| Versión | Fecha | Cambios | Autor |
| :--- | :--- | :--- | :--- |
| 1.0 | 16/12/2025 | Creación del documento | Gemini |