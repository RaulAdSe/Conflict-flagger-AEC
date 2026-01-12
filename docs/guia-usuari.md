# Guia d'Usuari - Flagger

## Què és Flagger?

Flagger és una aplicació d'escriptori que compara automàticament els models BIM (fitxers IFC) amb els pressupostos d'obra (fitxers BC3) per detectar discrepàncies.

### Per què serveix?

- **Detectar elements sense pressupostar**: Elements que estan al model 3D però no apareixen al pressupost
- **Detectar partides sense modelar**: Partides pressupostades que no tenen cap element al model
- **Trobar diferències de quantitats**: Volums, superfícies o longituds que no coincideixen
- **Verificar codificació**: Assegurar que els elements tenen el codi de partida correcte

## Instal·lació

### Windows
1. Descarrega el fitxer `ConflictFlaggerAEC.exe`
2. Desa'l on vulguis (p.ex. l'Escriptori)
3. Fes doble clic per executar-lo

### macOS
1. Descarrega el fitxer `Flagger`
2. La primera vegada, fes clic dret > "Obrir" per evitar l'advertència de seguretat
3. Fes doble clic per executar-lo

## Com utilitzar l'aplicació

### Pas 1: Obrir l'aplicació

Fes doble clic a l'executable. S'obrirà una finestra amb dues zones de càrrega:

```
┌─────────────────────────────────────────────────────────────┐
│                                            [Logo Servitec] │
│                         Flagger                             │
│   Compara fitxers IFC i BC3 per detectar discrepàncies     │
│                                                             │
│  ┌─────────────────────┐   ┌─────────────────────┐         │
│  │                     │   │                     │         │
│  │   Arrossega aquí    │   │   Arrossega aquí    │         │
│  │   el fitxer .IFC    │   │   el fitxer .BC3    │         │
│  │                     │   │                     │         │
│  │     Model BIM       │   │     Pressupost      │         │
│  └─────────────────────┘   └─────────────────────┘         │
│                                                             │
│  Tipus d'anàlisi: ○ Comprovació Ràpida  ● Anàlisi Completa │
│                                                             │
│              ┌────────────────────────┐                    │
│              │     Generar Excel      │                    │
│              └────────────────────────┘                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Pas 2: Carregar els fitxers

**Opció A - Arrossegar i deixar anar (recomanat):**
1. Obre l'Explorador de fitxers (Windows) o Finder (Mac)
2. Arrossega el fitxer `.ifc` sobre la zona esquerra
3. Arrossega el fitxer `.bc3` sobre la zona dreta

**Opció B - Fer clic per seleccionar:**
1. Fes clic a la zona esquerra
2. Selecciona el fitxer `.ifc` des del diàleg
3. Fes clic a la zona dreta
4. Selecciona el fitxer `.bc3` des del diàleg

Quan un fitxer s'ha carregat correctament, la zona es posa verda i mostra el nom del fitxer.

### Pas 2.5: Seleccionar el tipus d'anàlisi

Abans de generar l'informe, pots escollir el tipus d'anàlisi:

| Opció | Descripció | Quan usar-la |
|-------|------------|--------------|
| **Comprovació Ràpida** | Només comprova codis, unitats i quantitats | Validació inicial ràpida |
| **Anàlisi Completa** | Compara totes les propietats en detall | Auditoria exhaustiva |

**Comprovació Ràpida** és ideal per:
- Primera passada de validació
- Fitxers molt grans on vols resultats ràpids
- Verificar només si els codis i quantitats coincideixen

**Anàlisi Completa** és ideal per:
- Revisió final abans d'entregar
- Detectar totes les discrepàncies possibles
- Comparar propietats com materials, dimensions, etc.

Per defecte, l'aplicació utilitza **Anàlisi Completa**.

### Pas 3: Generar l'informe

1. Fes clic al botó verd **"Generar Excel"**
2. Espera uns segons mentre processa (depèn de la mida dels fitxers)
3. Apareixerà un missatge confirmant que l'informe s'ha generat

### Pas 4: Revisar l'informe

L'informe Excel es guarda automàticament a la carpeta **Descàrregues** (Downloads) amb un nom com:
```
informe_20250106_143052.xlsx
```

L'Excel s'obre automàticament quan acaba el procés.

## L'Informe Excel

L'informe conté diverses pestanyes amb colors per facilitar la revisió:

### Pestanyes de l'informe

| Pestanya | Contingut |
|----------|-----------|
| **Resum** | Estadístiques generals del projecte |
| **Discrepàncies** | Detall de tots els conflictes detectats |
| **Elements Emparellats** | Elements correctament vinculats |
| **Sense Pressupostar** | Elements del model sense partida al pressupost |
| **Sense Modelar** | Partides del pressupost sense element al model |
| **Resum Elements** | Resum consolidat de tots els elements |

### Codi de colors

| Color | Significat |
|-------|------------|
| Verd | Correcte - No hi ha problemes |
| Groc | Avís - Cal revisar |
| Vermell | Error - Requereix atenció |

## Resolució de problemes

### L'aplicació no s'obre

**Windows:**
- Prova a fer clic dret > "Executar com a administrador"
- Comprova que tens instal·lades les biblioteques Visual C++

**macOS:**
- Fes clic dret > "Obrir" per evitar el bloqueig de Gatekeeper
- Si no funciona, ves a Preferències del Sistema > Seguretat i Privadesa > permet l'aplicació

### No puc arrossegar fitxers

- Prova a fer clic a la zona i seleccionar el fitxer manualment
- Assegura't que el fitxer té l'extensió correcta (.ifc o .bc3)

### L'informe no s'obre

- Comprova la carpeta Descàrregues
- Assegura't que tens instal·lat Microsoft Excel o LibreOffice Calc

### Error durant el processament

- Verifica que els fitxers IFC i BC3 no estan corruptes
- Prova d'obrir els fitxers amb altres programes per assegurar-te que estan bé
- Si el problema persisteix, contacta amb l'equip tècnic

## Consells d'ús

1. **Exporta l'IFC des de Revit** amb propietats i quantitats
2. **Exporta el BC3 des de Presto** incloent els GUIDs de l'IFC
3. **Revisa primer les discrepàncies vermelles** - són les més crítiques
4. **Corregeix al model o pressupost** segons correspongui
5. **Torna a executar** fins a validació completa

## Ús per línia de comandes (avançat)

Per a usuaris tècnics, també es pot executar des de la línia de comandes:

```bash
# Anàlisi completa (per defecte)
python -m src.main --ifc model.ifc --bc3 pressupost.bc3

# Comprovació ràpida
python -m src.main --ifc model.ifc --bc3 pressupost.bc3 --phase quick

# Amb opcions addicionals
python -m src.main \
    --ifc model.ifc \
    --bc3 pressupost.bc3 \
    --phase full \
    --output informe.xlsx \
    --tolerance 0.02 \
    -v
```

### Opcions disponibles

| Opció | Descripció |
|-------|------------|
| `--ifc` | Fitxer IFC (obligatori) |
| `--bc3` | Fitxer BC3 (obligatori) |
| `--phase` | `quick` o `full` (per defecte: full) |
| `--output` | Nom del fitxer Excel de sortida |
| `--json` | Generar també un fitxer JSON |
| `--tolerance` | Tolerància numèrica (per defecte: 0.01) |
| `-v` | Mode verbose (més informació) |
| `-q` | Mode silenciós (només el path de l'informe) |

## Contacte

Per a dubtes o problemes tècnics, contacta amb l'equip de desenvolupament.
