# Copilot Instructions - Mebis-TZ Questlog

## Project Overview
Streamlit-basierte Gamification-App für Schüler. Liest Spielerdaten aus Google Sheets und zeigt XP-Fortschritt + Quest-Status an. 

**Key Files:**
- [app.py](../app.py): Einzelne Monolith-Datei, ~284 Zeilen, alle Logik enthalten

## Architecture & Data Flow

### Google Sheets Integration
**Two-Sheet System:**
1. **"XP Rechner 3.0"**: Spieler-Master-Daten
   - Spalten: A=Vorname, B=Nachname, C=Klasse, D=Gamertag, E=XP, F=Level, G=Stufe
   - Gamertag-Lookup (Spalte D, ab Zeile 2) ist Primary Key
   - "💀" in Level oder "game over" in Stufe = Ende-Status

2. **"Questbuch 4.0"**: Quest-Zuordnungen pro Schüler
   - Zeile 2 (Index 1): Quest-Namen ab Spalte C
   - Zeile 5 (Index 4): XP pro Quest
   - Ab Zeile 7 (Index 6): Schüler-Zuordnungen (Spalte B = Name)
   - Student-Daten ab Spalte C, parallel zu Quest-Namen

**Critical Implementation Details:**
- **No auto-headers**: `header=None` in `conn.read()` - indices sind 0-basiert
- **Gamertag Search**: Case-insensitive Suche in Index 3 (Spalte D), ab Zeile 1 (Index 1)
- **Student Name Match**: Substring-Suche nach Nachname (lowercase) in Questbuch
- **TTL=0**: Keine Caches - Echtzeit-Updates notwendig

### Level System
- **LEVEL_THRESHOLDS**: Dict mit 16 Levels (0-indexed keys)
- **Progress Calculation**: 
  - Aktuelles Level = höchster Threshold < aktuelles XP
  - Max Level 16 = 1.0 progress
  - Progress: `(xp_in_level) / (next_threshold - current_threshold)`

### Quest Display Logic
**Completion Detection** (`is_quest_completed`):
- Bool `True` oder Strings: "TRUE", "WAHR", "1", "CHECKED", "ABGESCHLOSSEN", "✓"
- Numerisch > 0
- NaN = False

**XP Assignment**:
1. Wenn Quest komplett und Value=0 → nutze Master-XP aus Zeile 5
2. Sonst: Value aus Student-Zeile (wenn > 0)
3. Fallback: Master-XP
4. Überspringe Quests mit 0 XP

**Stop Conditions** (Quest-Loop):
- Quest-Name enthält: "CP", "GESAMTSUMME", "GAME-OVER" (case-insensitive)
- Überspringe System-Spalten: "QUEST", "KACHEL", "CODE", "QUEST-ART"

## Conventions & Patterns

### Error Handling
- Wrapped in `try/except` mit `st.error()` + optional Debug-Exception
- `safe_int()`: Fallback zu 0, toleriert Kommas als Dezimaltrennzeichen
- Debug-Mode: Checkbox in Sidebar, zeigt DataFrame-Snapshots

### Data Validation
- `pd.isna()` vor Type-Casting
- String-Konversionen immer `.strip()` + `.lower()` für Vergleiche
- Range-Checks: `len(player_data) > 6` vor Index-Zugriff

### UI/UX Patterns
- **Gating**: `st.stop()` nach Success-Message für Nutzer-Flow (nach Gamertag-Validierung)
- **Toggles**: `st.checkbox()` für Show/Hide (erledigte Quests). `st.toggle()` wurde ersetzt, da es nicht in allen Streamlit-Versionen verfügbar ist.
- **Cards**: 3-Spalten-Grid mit Custom HTML für offene Quests
- **Info-Boxes**: `st.info()`, `st.warning()`, `st.error()` für kontextuelle Meldungen

### German Language
- UI vollständig auf Deutsch (Meldungen, Spalten, Hilfe-Texte)
- Numerische Format-Konventionen beachten (bei Float-Parsing)

## Developer Workflows

### Running
```bash
streamlit run app.py
# Secrets: Create .streamlit/secrets.toml with GSheets auth token
```

### Dependencies
- `streamlit`: Core UI
- `pandas`: DataFrame-Processing
- `st-gsheets-connection`: Google Sheets connector (abstracts OAuth)

### Debugging
- Enable Debug-Modus via Sidebar Checkbox
- Zeigt XP-Rechner/Questbuch Raw-DataFrames (erste 10 Zeilen)
- Zeigt Suche-Ergebnisse (gefundene Zeile, Player-Row)
- `st.exception(e)` im Except-Block bei aktivem Debug

### Common Maintenance Tasks
- **Neue Quest hinzufügen**: Spalte in Questbuch + XP in Zeile 5
- **Neuer Schüler**: Zeile in XP Rechner + Zeile in Questbuch
- **Level anpassen**: LEVEL_THRESHOLDS Dict aktualisieren (dann UI refreshen)
- **Gamertag-Typos**: Verfügbare-Tags Expander unter Fehler-Box hilft Schülern

## Integration Points
- **Google Sheets API**: Via `st.secrets["connections"]["gsheets"]` (Streamlit-Cloud managed)
- **No External APIs**: Nur GSheets, keine Webhooks/Callbacks
- **State Management**: Keine Session-State - stateless pro Request
