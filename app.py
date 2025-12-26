import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="TZ Questlog", page_icon="📐")
st.title("📐 Technisches Zeichnen - Questlog")

# --- KONFIGURATION ---
# 1. HIER DEINEN LINK EINFÜGEN:
url = "https://docs.google.com/spreadsheets/d/DEINE_LANGE_ID_HIER/edit"

# 2. Das Blatt mit der Struktur (Zeile 2 Namen, Zeile 5 XP)
blatt_name = "Questbuch 4.0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Wir laden das Blatt OHNE Header, damit wir Zeile 2 und 5 manuell greifen können
    df = conn.read(spreadsheet=url, worksheet=blatt_name, header=None)
    
    # --- DATEN STRUKTURIEREN ---
    # Zeile 2 in Excel ist Index 1 in Python (0, 1, 2...) -> Quest Namen
    quest_names_row = df.iloc[1] 
    # Zeile 5 in Excel ist Index 4 in Python -> XP Werte
    xp_values_row = df.iloc[4]

    # Wir erstellen ein "Wörterbuch" der Quests: {SpaltenIndex: {'name': 'Lochblech', 'xp': 170}}
    quest_map = {}
    
    # Wir gehen durch alle Spalten (ab Spalte D bzw Index 3, da vorne meist Namen stehen)
    for col_idx in range(3, len(df.columns)):
        q_name = str(quest_names_row[col_idx])
        q_xp = str(xp_values_row[col_idx])
        
        # Nur wenn ein Name da ist und XP eine Zahl ist, ist es eine Quest
        if q_name != "nan" and q_name != "" and q_xp.replace('.','',1).isdigit():
            quest_map[col_idx] = {
                "name": q_name,
                "xp": int(float(q_xp)) # Sicherstellen, dass es eine Zahl ist
            }

    # --- LOGIN ---
    st.info("Logge dich ein, um deine Quests zu prüfen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. ElArg")

    if gamertag_input:
        found_student = False
        
        # Wir suchen ab Zeile 10 nach dem Schüler (um Header zu überspringen)
        # Wir suchen in den ersten 5 Spalten nach dem Gamertag
        start_row = 10 
        
        for index, row in df.iloc[start_row:].iterrows():
            # Wir prüfen die ersten paar Spalten, ob der Tag drin steht
            row_start = [str(x).strip().lower() for x in row.values[:5]]
            
            if gamertag_input.strip().lower() in row_start:
                found_student = True
                
                # --- BERECHNUNG ---
                total_xp = 0
                completed_quests = []
                open_quests = []
                
                # Wir gehen durch unsere Quest-Map und schauen, was in der Zeile steht
                for col_idx, quest_info in quest_map.items():
                    cell_value = str(row[col_idx]).strip()
                    
                    if cell_value == "Abgeschlossen":
                        total_xp += quest_info['xp']
                        completed_quests.append(quest_info)
                    else:
                        open_quests.append(quest_info)

                # --- LEVEL BERECHNUNG ---
                # (Hier deine vereinfachte Logik, kannst du anpassen)
                level = 1
                if total_xp >= 42: level = 2
                if total_xp >= 101: level = 3
                if total_xp >= 189: level = 4
                if total_xp >= 308: level = 5
                if total_xp >= 456: level = 6
                if total_xp >= 650: level = 7
                if total_xp >= 1000: level = 8
                if total_xp >= 1600: level = 10 # Beispiel

                # --- ANZEIGE ---
                st.balloons()
                st.subheader(f"Hallo {gamertag_input}! 👋")
                
                c1, c2 = st.columns(2)
                c1.metric("Level", level)
                c2.metric("Aktuelle XP", total_xp)
                
                st.progress(min(total_xp / 2000, 1.0), text="Fortschritt im Kurs")

                # --- QUEST LOG ---
                st.divider()
                tab1, tab2 = st.tabs(["✅ Erledigte Quests", "❌ Offene Quests"])
                
                with tab1:
                    if completed_quests:
                        for q in completed_quests:
                            st.success(f"**{q['name']}** (+{q['xp']} XP)")
                    else:
                        st.write("Noch keine Quests erledigt. Auf geht's!")
                
                with tab2:
                    if open_quests:
                        for q in open_quests:
                            st.caption(f"🔒 {q['name']} ({q['xp']} XP)")
                    else:
                        st.write("Alles erledigt! Du bist ein Meister!")
                
                break # Suche beenden

        if not found_student:
            st.error(f"Gamertag '{gamertag_input}' im Blatt '{blatt_name}' nicht gefunden.")
            st.warning("Tipp: Steht der Gamertag wirklich in den ersten 5 Spalten von Questbuch 4.0?")

except Exception as e:
    st.error("Fehler beim Laden der Tabelle!")
    st.code(str(e))
