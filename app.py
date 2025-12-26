import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="TZ Questlog", page_icon="📐")
st.title("📐 Technisches Zeichnen - Questlog")

# --- KONFIGURATION ---
# WICHTIG: Hier nur den Basis-Link rein (ohne /edit#gid=...)
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q/edit?gid=353646049#gid=353646049"

# Namen der Blätter exakt wie unten in Google Sheets
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- SCHRITT 1: GAMERTAG & ECHTNAME LADEN ---
    # Wir laden erst das Mapping-Blatt, um zu prüfen, wer der User ist
    try:
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping)
    except Exception:
        st.error(f"Fehler 404: Konnte das Blatt '{blatt_mapping}' nicht finden.")
        st.stop()

    # Login Screen
    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. ElArg")

    if gamertag_input:
        # Wir suchen den Gamertag im XP Rechner
        # Wir suchen eine Spalte, die "Gamertag" heißt (oder ähnlich)
        col_gamertag = None
        col_realname = None
        
        # Automatische Spaltensuche
        for col in df_xp.columns:
            if "gamertag" in str(col).lower():
                col_gamertag = col
            if "name" in str(col).lower() and "user" not in str(col).lower(): # Name, aber nicht Username
                col_realname = col

        if not col_gamertag:
            st.error("Konnte Spalte 'Gamertag' im XP Rechner nicht finden.")
            st.stop()

        # Suchen des Schülers
        student_entry = df_xp[df_xp[col_gamertag].astype(str).str.strip().str.lower() == gamertag_input.strip().lower()]

        if not student_entry.empty:
            # TREFFER! Wir haben den Gamertag gefunden.
            real_name = student_entry.iloc[0][col_realname]
            level = student_entry.iloc[0].get('Level', 0)
            xp_total = student_entry.iloc[0].get('XP', 0)
            
            st.balloons()
            st.success(f"Willkommen, {gamertag_input}! (Level {level})")
            
            # --- SCHRITT 2: QUESTBUCH LADEN ---
            # Jetzt holen wir die Details aus dem Questbuch mit dem ECHTEN NAMEN
            try:
                # header=None, weil wir Zeile 2 und 5 manuell brauchen
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None)
            except:
                st.error(f"Konnte Blatt '{blatt_quests}' nicht finden.")
                st.stop()

            # A. Quest-Struktur verstehen (Zeile 2 = Namen, Zeile 5 = XP)
            quest_names = df_quests.iloc[1] # Zeile 2
            quest_xps = df_quests.iloc[4]   # Zeile 5

            # B. Den Schüler im Questbuch suchen (via Echtname)
            # Wir suchen in Spalte A oder B (Index 0 oder 1) nach dem Namen
            quest_row_index = -1
            
            # Wir scannen die ersten 100 Zeilen nach dem Namen
            for idx, row in df_quests.iterrows():
                # Wir prüfen die ersten paar Spalten auf den Namen
                row_str = " ".join([str(x) for x in row.values[:3]]).lower()
                if str(real_name).lower() in row_str:
                    quest_row_index = idx
                    break
            
            if quest_row_index != -1:
                # Wir haben die Zeile des Schülers im Questbuch!
                student_quest_row = df_quests.iloc[quest_row_index]
                
                st.divider()
                st.subheader("Deine Quests")
                
                # Wir gehen durch die Spalten und prüfen auf "Abgeschlossen"
                cols = st.columns(3)
                col_counter = 0
                
                # Wir starten ab Spalte 3 (D), wo die Quests meist beginnen
                found_quests = False
                for c in range(3, len(df_quests.columns)):
                    q_name = str(quest_names[c])
                    val = str(student_quest_row[c]) # Was steht beim Schüler drin?
                    
                    # Wenn beim Schüler "Abgeschlossen" steht
                    if "abgeschlossen" in val.lower():
                        found_quests = True
                        # XP Wert holen
                        try:
                            xp_val = int(float(str(quest_xps[c])))
                        except:
                            xp_val = "?"
                        
                        # Schöne Karte anzeigen
                        with cols[col_counter % 3]:
                            st.markdown(f"""
                            <div style="background-color: #d4edda; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                                <strong>✅ {q_name}</strong><br>
                                <span style="color: green;">+{xp_val} XP</span>
                            </div>
                            """, unsafe_allow_html=True)
                        col_counter += 1
                
                if not found_quests:
                    st.info("Noch keine Quests im Questbuch als 'Abgeschlossen' markiert.")
                    
            else:
                st.warning(f"Konnte Datensatz für '{real_name}' im Questbuch nicht finden. (Namensschreibweise anders?)")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

except Exception as e:
    st.error("Kritischer Fehler beim Verbinden:")
    st.code(str(e))
    st.markdown("⚠️ **Checkliste für 404 Fehler:**")
    st.markdown("1. Ist der Link oben in Zeile 10 wirklich **ohne** `/edit...` am Ende?")
    st.markdown(f"2. Heißt das erste Blatt wirklich exakt `{blatt_mapping}`?")
    st.markdown(f"3. Heißt das zweite Blatt wirklich exakt `{blatt_quests}`?")
