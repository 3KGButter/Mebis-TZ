import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="TZ Questlog", page_icon="📐")
st.title("📐 Technisches Zeichnen - Questlog")

# --- KONFIGURATION ---
# WICHTIG: Hier deinen Link einfügen (ohne /edit am Ende)
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q/edit?gid=353646049#gid=353646049"

# Namen der Blätter exakt wie unten in Google Sheets
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- SCHRITT 1: GAMERTAG & ECHTNAME LADEN ---
    try:
        # FIX: header=1 bedeutet, wir nehmen die ZWEITE Zeile als Überschrift (Index 1)
        # Das überspringt die Zeile mit "aus Klassenliste kopieren..."
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1)
        
        # Falls pandas leere Spaltennamen generiert hat, bereinigen wir das
        df_xp.columns = df_xp.columns.str.strip()
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    # Login Screen
    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        # Wir suchen die Spalten dynamisch
        col_gamertag = None
        col_realname = None
        
        # Wir suchen nach "Gamertag" und einer Spalte, die den vollen Namen enthält
        # In deiner Datei heißt die Namens-Spalte oft "Klasse + Name..."
        for col in df_xp.columns:
            c_str = str(col).lower()
            if "gamertag" in c_str:
                col_gamertag = col
                # Wir brechen ab, sobald wir den ersten Gamertag finden (Spalte E)
                break 
        
        # Für den echten Namen suchen wir die Spalte D
        # Da wir header=1 nutzen, sollte sie "Klasse + Name" oder ähnlich heißen
        for col in df_xp.columns:
            if "klasse + name" in str(col).lower():
                col_realname = col
                break
        
        # Fallback: Falls wir die Namensspalte nicht finden, nehmen wir Spalte Index 3 (D)
        if not col_realname and len(df_xp.columns) > 3:
             col_realname = df_xp.columns[3]

        if not col_gamertag:
            st.error("Konnte Spalte 'Gamertag' auch in Zeile 2 nicht finden.")
            st.write("Gefundene Spalten:", list(df_xp.columns))
            st.stop()

        # Suchen des Schülers (Groß-/Kleinschreibung egal)
        # Wir wandeln die Spalte in Text um, entfernen Leerzeichen und vergleichen
        student_entry = df_xp[df_xp[col_gamertag].astype(str).str.strip().str.lower() == gamertag_input.strip().lower()]

        if not student_entry.empty:
            # TREFFER!
            real_name = student_entry.iloc[0][col_realname]
            
            # Wir versuchen Level und XP zu finden. 
            # In deiner Tabelle kommen "Level" und "XP" mehrfach vor (für die Ranglisten rechts).
            # Wir nehmen einfach die Spalten, die "Level" und "XP" heißen (pandas nimmt automatisch das erste Vorkommen links)
            level = student_entry.iloc[0].get('Level', 0)
            xp_total = student_entry.iloc[0].get('XP', 0)
            
            # Falls "Level" leer ist (NaN), machen wir eine 0 draus
            if pd.isna(level): level = 0
            if pd.isna(xp_total): xp_total = 0

            st.balloons()
            st.success(f"Willkommen, {real_name}! (Level {int(level)})")
            
            # --- SCHRITT 2: QUESTBUCH LADEN ---
            try:
                # header=None, weil wir Zeile 2 und 5 manuell brauchen
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None)
            except:
                st.error(f"Konnte Blatt '{blatt_quests}' nicht finden.")
                st.stop()

            # A. Quest-Struktur verstehen (Zeile 2 = Namen, Zeile 5 = XP)
            # Python Index startet bei 0 -> Zeile 2 ist Index 1
            quest_names = df_quests.iloc[1] 
            quest_xps = df_quests.iloc[4]

            # B. Den Schüler im Questbuch suchen (via Echtname)
            quest_row_index = -1
            
            # Wir scannen die ersten 200 Zeilen
            # Der Name steht im Questbuch in Spalte B (Index 1) -> "Name"
            for idx, row in df_quests.iterrows():
                # Wir vergleichen den gefundenen Realnamen mit dem Namen im Questbuch
                if str(real_name).lower() in str(row[1]).lower(): # Spalte B prüfen
                    quest_row_index = idx
                    break
            
            if quest_row_index != -1:
                student_quest_row = df_quests.iloc[quest_row_index]
                
                st.divider()
                st.subheader("Deine Quests")
                
                # Layout für Quests
                cols = st.columns(3)
                col_counter = 0
                found_quests = False
                
                # Wir starten ab Spalte 3 (D), wo die Quests beginnen
                for c in range(3, len(df_quests.columns)):
                    q_name = str(quest_names[c])
                    val = str(student_quest_row[c]) # Was steht beim Schüler?
                    
                    # Nur wenn es eine echte Quest ist (hat einen Namen)
                    if q_name != "nan" and q_name != "":
                        # Wenn "Abgeschlossen"
                        if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                            found_quests = True
                            
                            # XP Wert holen
                            try:
                                xp_val = int(float(str(quest_xps[c])))
                            except:
                                xp_val = "?"
                            
                            with cols[col_counter % 3]:
                                st.success(f"✅ {q_name}\n\n**+{xp_val} XP**")
                            col_counter += 1
                
                if not found_quests:
                    st.info("Noch keine Quests abgeschlossen.")
            else:
                st.warning(f"Konnte '{real_name}' im Questbuch nicht finden.")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

except Exception as e:
    st.error("Ein Fehler ist aufgetreten:")
    st.code(str(e))
