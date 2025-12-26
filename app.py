import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="TZ Questlog", page_icon="📐")
st.title("📐 Technisches Zeichnen - Questlog")

# --- KONFIGURATION ---
# Dein Link ist jetzt fest hinterlegt:
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"

# Die Namen der Tabellenblätter (exakt so wie unten in Google Sheets)
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- SCHRITT 1: GAMERTAG & ECHTNAME LADEN ---
    try:
        # header=1 bedeutet: Wir überspringen Zeile 1 ("aus Klassenliste kopieren")
        # und nehmen Zeile 2 als echte Überschriften.
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1)
        
        # Spaltennamen bereinigen (Leerzeichen entfernen)
        df_xp.columns = df_xp.columns.str.strip()
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}'. Existiert das Blatt?")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        # --- SPALTEN SUCHEN ---
        col_gamertag = None
        col_realname = None
        
        # Wir suchen die Spalte "Gamertag"
        for col in df_xp.columns:
            if "gamertag" in str(col).lower():
                col_gamertag = col
                break 
        
        # Wir suchen die Spalte mit dem Namen (meist "Klasse + Name")
        for col in df_xp.columns:
            if "klasse + name" in str(col).lower():
                col_realname = col
                break
        
        # Fallback, falls Name nicht gefunden wird (wir nehmen Spalte D / Index 3)
        if not col_realname and len(df_xp.columns) > 3:
             col_realname = df_xp.columns[3]

        if not col_gamertag:
            st.error("Konnte Spalte 'Gamertag' nicht finden.")
            st.stop()

        # --- SCHÜLER SUCHEN ---
        # Wir machen alles klein (.lower()), damit Groß-/Kleinschreibung egal ist
        student_entry = df_xp[df_xp[col_gamertag].astype(str).str.strip().str.lower() == gamertag_input.strip().lower()]

        if not student_entry.empty:
            # Wir haben den Schüler gefunden!
            real_name = student_entry.iloc[0][col_realname]
            
            # --- DATEN AUSLESEN (LEVEL & XP) ---
            # Hier fangen wir das "Game Over" Kreuz (†) ab
            raw_level = student_entry.iloc[0].get('Level', 0)
            raw_xp = student_entry.iloc[0].get('XP', 0)
            
            level_num = 0
            display_level = str(raw_level) # Standard: Zeige an, was in der Zelle steht (z.B. †)

            # Versuch: Ist das Level eine Zahl?
            try:
                level_num = int(raw_level)
                display_level = str(level_num)
            except:
                # Wenn es keine Zahl ist (z.B. †), bleibt level_num 0
                pass

            # Versuch: Sind die XP eine Zahl?
            xp_num = 0
            try:
                xp_num = int(raw_xp)
            except:
                pass

            st.balloons()
            st.success(f"Willkommen, {real_name}!")
            
            # --- DASHBOARD ANZEIGE ---
            col1, col2 = st.columns(2)
            col1.metric("Level", display_level) # Zeigt Zahl oder † an
            col2.metric("XP Total", xp_num)
            
            # Fortschrittsbalken (nur wenn Level > 0, also kein Game Over)
            if level_num > 0:
                # Beispiel: Fortschritt innerhalb von 1000 XP Schritten
                progress = min((xp_num % 1000) / 1000, 1.0)
                st.progress(progress, text="Fortschritt zum nächsten Level")
            elif "†" in display_level or "Game" in str(display_level):
                st.error("💀 GAME OVER - Bitte beim Lehrer melden!")

            # --- SCHRITT 2: QUESTS LADEN ---
            try:
                # Hier nehmen wir KEINEN Header, weil Zeile 2 und 5 wichtig sind
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None)
            except:
                st.warning(f"Konnte Quests ('{blatt_quests}') nicht laden.")
                st.stop()

            # Zeilen definieren (Python zählt ab 0)
            quest_names = df_quests.iloc[1] # Zeile 2
            quest_xps = df_quests.iloc[4]   # Zeile 5

            # Wir suchen die Zeile des Schülers im Questbuch (über den echten Namen)
            quest_row_index = -1
            
            # Wir scannen die Zeilen nach dem Namen
            for idx, row in df_quests.iterrows():
                # Wir bauen einen Such-String aus den ersten 3 Spalten der Zeile
                row_str = " ".join([str(x) for x in row.values[:3]]).lower()
                if str(real_name).lower() in row_str:
                    quest_row_index = idx
                    break
            
            if quest_row_index != -1:
                student_quest_row = df_quests.iloc[quest_row_index]
                
                st.divider()
                st.subheader("Deine Quests")
                
                cols = st.columns(3)
                col_counter = 0
                found_quests = False
                
                # Wir gehen durch alle Spalten ab Spalte D (Index 3)
                for c in range(3, len(df_quests.columns)):
                    q_name = str(quest_names[c])
                    val = str(student_quest_row[c])
                    
                    # Ist es eine gültige Quest? (Name nicht leer)
                    if q_name != "nan" and q_name != "":
                        # Ist sie abgeschlossen?
                        if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                            found_quests = True
                            
                            # XP Wert holen (falls möglich)
                            try:
                                xp_val = int(float(str(quest_xps[c])))
                            except:
                                xp_val = "?"
                            
                            # Grüne Erfolgs-Box anzeigen
                            with cols[col_counter % 3]:
                                st.success(f"✅ {q_name}\n\n**+{xp_val} XP**")
                            col_counter += 1
                
                if not found_quests:
                    st.info("Noch keine Quests abgeschlossen.")
            else:
                st.warning("Keine Quests für diesen Namen gefunden.")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden. Tippfehler?")

except Exception as e:
    st.error("Ein kritischer Fehler ist aufgetreten:")
    st.code(str(e))
