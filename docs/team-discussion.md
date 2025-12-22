# Discusión de Equipo: Estado Actual y Próximos Pasos

**Fecha:** 22 de diciembre de 2025
**Objetivo:** Recoger feedback del equipo sobre el estado del proyecto y decisiones clave

---

## 1. Estado Actual del Proyecto

### Funcionalidades Implementadas

| Componente | Estado | Descripción |
|------------|--------|-------------|
| Parser IFC | Completo | Extrae elementos de modelos BIM (IFC2x3, IFC4) |
| Parser BC3 | Completo | Procesa presupuestos FIEBDC-3 (Presto, Arquímedes, TCQ) |
| Matcher | Completo | Empareja elementos por GUID, Tag o nombre |
| Comparador | Completo | Detecta 5 tipos de conflictos con niveles de severidad |
| Reportero | Completo | Genera Excel con 5 hojas en español |
| CLI | Completo | Interfaz de línea de comandos funcional |
| Tests | Completo | Cobertura de tests unitarios + generador de escenarios |
| Documentación | Completo | Documentación técnica completa en inglés |

### Tipos de Conflictos Detectados

1. **Sin Presupuestar** - Elementos en el modelo sin partida de presupuesto
2. **Sin Modelar** - Partidas presupuestadas sin elemento en el modelo
3. **Discrepancia de Propiedades** - Valores diferentes entre modelo y presupuesto
4. **Discrepancia de Cantidades** - Diferencias en volumen, área o longitud
5. **Discrepancia de Tipo** - Tipos de elementos diferentes

### Arquitectura Actual

```
Archivo IFC → Parser IFC ─┐
                          ├→ Matcher → Comparador → Reportero → Excel/JSON
Archivo BC3 → Parser BC3 ─┘
```

**Preguntas para el equipo:**
- ¿Qué os parece el estado actual?
- ¿Falta alguna funcionalidad crítica antes de pasar a la siguiente fase?
- ¿El formato del Excel de salida es útil o necesita ajustes?

---

## 2. Decisión: Aplicación de Escritorio vs Aplicación Web

Necesitamos decidir cómo presentar esta herramienta a los usuarios finales.

### Opción A: Aplicación de Escritorio (PyInstaller)

| Ventajas | Desventajas |
|----------|-------------|
| Funciona sin conexión | Actualizaciones manuales |
| Sin dependencias externas | Tamaño ~100MB por ejecutable |
| Datos permanecen locales | Un ejecutable por SO (Windows/Mac/Linux) |
| Más rápido para archivos grandes | Sin colaboración en tiempo real |

**Ideal para:** Usuarios que trabajan offline o con datos sensibles.

### Opción B: Aplicación Web (Streamlit/FastAPI)

| Ventajas | Desventajas |
|----------|-------------|
| Acceso desde cualquier navegador | Requiere servidor/hosting |
| Actualizaciones centralizadas | Dependencia de conexión |
| Interfaz moderna con drag & drop | Costes de infraestructura |
| Fácil de compartir en oficina | Consideraciones de seguridad |
| Posibilidad de colaboración | Latencia con archivos grandes |

**Ideal para:** Equipos que comparten oficina o trabajo remoto colaborativo.

### Opción C: Híbrido

Streamlit puede empaquetarse como ejecutable con Electron o como servicio local.

**Preguntas para el equipo:**
- ¿Quiénes son los usuarios principales? ¿Trabajan solos o en equipo?
- ¿Hay restricciones de IT en las empresas cliente?
- ¿Priorizamos facilidad de distribución o funcionalidades avanzadas?
- ¿Qué presupuesto hay para hosting si elegimos web?

---

## 3. Tercer Pilar: Excel como Soporte para la Memoria Constructiva

### Visión

El Excel generado por el comparador no es solo un informe de discrepancias, sino que puede servir como **base documental para redactar la Memoria Constructiva en Word**.

### Flujo Propuesto

```
Modelo IFC + Presupuesto BC3
           ↓
    Conflict Flagger
           ↓
      Excel de Salida
           ↓
    ┌──────┴──────┐
    ↓             ↓
Resolver      Exportar datos
discrepancias  verificados
    ↓             ↓
Modelo/Presupuesto  Memoria Constructiva
   corregido           en Word
```

### Datos del Excel Útiles para la Memoria

| Hoja del Excel | Uso en Memoria Constructiva |
|----------------|----------------------------|
| **Elementos Emparejados** | Listado verificado de elementos del proyecto |
| **Resumen** | Estadísticas para sección de introducción |
| **Sin Presupuestar** | Elementos a justificar o añadir al presupuesto |
| **Sin Modelar** | Partidas a revisar o eliminar |

### Posibles Mejoras para Este Pilar

1. **Plantilla Word automática**: Generar un .docx base con los datos del Excel
2. **Campos enlazados**: Usar mail merge o similar para actualizar Word desde Excel
3. **Categorización por capítulos**: Organizar elementos según estructura de memoria
4. **Exportación de propiedades**: Incluir descripciones técnicas listas para copiar

### Opción Destacada: Mail Merge (Combinar Correspondencia)

**¿Qué es?**
Mail Merge es una funcionalidad nativa de Word que permite insertar datos desde un Excel en cualquier documento. Se puede usar con o sin plantilla predefinida - simplemente conectas tu Word al Excel y donde necesites un dato, insertas un campo.

**Flujo de trabajo:**
1. Ejecutar Conflict Flagger → genera Excel
2. En Word (cualquier documento) → Correspondencia → Seleccionar origen de datos → Excel
3. Insertar campos donde se necesiten datos del modelo

**Ejemplo: Propiedades específicas de elementos**

En la Memoria Constructiva podríamos escribir:

> *"El muro de fachada principal (Muro_F01) tiene un espesor de `«Muro_F01.Ancho»` mm
> y una transmitancia térmica de `«Muro_F01.Transmitancia_Termica»` W/m²K,
> cumpliendo con los requisitos del CTE DB-HE."*

Que al combinar con el Excel se convierte en:

> *"El muro de fachada principal (Muro_F01) tiene un espesor de **280** mm
> y una transmitancia térmica de **0.27** W/m²K,
> cumpliendo con los requisitos del CTE DB-HE."*

**Campos disponibles por elemento:**

| Tipo de Campo | Ejemplo | Uso en Memoria |
|---------------|---------|----------------|
| `«Elemento.Nombre»` | Pilar_P12 | Identificación |
| `«Elemento.Ancho»` | 300 | Dimensiones |
| `«Elemento.Alto»` | 2800 | Dimensiones |
| `«Elemento.Volumen»` | 0.84 | Mediciones |
| `«Elemento.Material»` | HA-30 | Especificaciones |
| `«Elemento.Transmitancia»` | 0.27 | Cumplimiento CTE |
| `«Elemento.Resistencia_Fuego»` | EI-120 | Seguridad |

**Ventajas:**
- No requiere programación - Word ya lo tiene incorporado
- Se usa en cualquier documento, no hace falta plantilla
- Si cambia el Excel, se actualiza el documento
- Trazabilidad: cada dato viene del modelo verificado
- Reduce errores de transcripción manual

**Formato de Excel necesario para Mail Merge:**

Para que Word pueda leer los campos correctamente, el Excel debe tener:
- Primera fila = nombres de columnas (estos serán los nombres de los campos)
- Una fila por elemento
- Una columna por propiedad

Ejemplo de estructura:

| Codigo | Nombre | Ancho | Alto | Volumen | Transmitancia |
|--------|--------|-------|------|---------|---------------|
| 03.01.002 | Muro Fachada | 280 | 3000 | 12.4 | 0.27 |
| 02.03.015 | Pilar HA-30 | 300 | 2800 | 0.84 | - |

**¿Qué código usar como identificador?** Opciones disponibles:

| Origen | Ejemplo | Pros | Contras |
|--------|---------|------|---------|
| Código BC3 (Presto) | `03.01.002` | Ya existe, jerárquico | Solo elementos presupuestados |
| Nombre IFC | `Muro Básico:Fachada 280` | Descriptivo | Puede ser largo, inconsistente |
| Tag Revit | `1234567` | Único, corto | Solo numérico, poco descriptivo |
| GUID IFC | `2O2Fr$t4X7Zf8...` | Único universal | Ilegible para humanos |

Habría que decidir cuál es más útil para referenciar en la memoria.

Esto requeriría adaptar el Excel de salida actual o añadir una hoja adicional con este formato.

**Preguntas para el equipo:**
- ¿Qué propiedades de los elementos serían más útiles tener disponibles para la memoria?
- ¿Qué formato de datos facilitaría más el trabajo de redacción?

---

## Próximos Pasos Propuestos

1. **Corto plazo**: Recoger feedback del equipo sobre este documento
2. **Decisión**: Elegir entre desktop/web/híbrido
3. **Prototipo**: Crear MVP de la interfaz elegida
4. **Pilar 3**: Definir requisitos concretos para soporte de Memoria Constructiva

---

## Comentarios del Equipo

*Añadir comentarios aquí:*

| Miembro | Fecha | Comentario |
|---------|-------|------------|
| | | |
| | | |
| | | |

---

**Contacto:** [Añadir información de contacto para discusión]
