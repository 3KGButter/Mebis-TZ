import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="🛡️", layout="centered")
st.title("🛡️ Questlog & XP Tracker")

# --- LEVEL KONFIGURATION ---
LEVEL_THRESHOLDS = {
    1: 0, 2: 42, 3: 143, 4: 332, 5: 640, 6: 1096, 7: 1728, 8: 2567,
    9: 3640, 10: 4976, 11: 6602, 12: 8545, 13: 10831, 14: 13486, 15: 16536, 16: 20003
}

def calculate_progress(current_xp):
    current_level = 1
    for lvl, threshold in LEVEL_THRESHOLDS.items():
        if current_xp >= threshold:
            current_level = lvl
        else:
            break
            
    if current_level >= 16:
        return 1.0, "Maximales Level erreicht! 🏆"
    
    current_level_start = LEVEL_THRESHOLDS[current_level]
    next_level_start = LEVEL_THRESHOLDS[current_level + 1]
    
    xp_gained_in_level = current_xp - current_level_start
    xp_needed_for_level = next_level_start - current_level_start
    
    if xp_needed_for_level <= 0: return 1.0, "Level Up!"
    
    progress_percent = xp_gained_in_level / xp_needed_for_level
    progress_percent = max(0.0, min(1.0, progress_percent))
    
    text = f"{int(xp_gained_in_level)} / {int(xp_needed_for_level)} XP zum nächsten Level"
    return progress_percent, text

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.5 | Multi-Spalten Scan")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ---------------------------------------------------------
    # TEIL 1: XP RECHNER (Intelligenter Scan)
    # ---------------------------------------------------------
    try:
        # Alles laden ohne Header
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=None, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        real_name_found = None
        found_stats = None

        # --- SCHRITT A: ECHTEN NAMEN FINDEN (Linker Bereich) ---
        # Wir suchen in Spalte E (Index 4), wo die Gamertags der Klassenliste stehen
        # Spalte D (Index 3) ist der Name "Klasse + Name"
        
        # Wir suchen ab Zeile 2 (Index 2)
        start_row_data = 2
        
        col_idx_mapping_tag = 4  # Spalte E
        col_idx_mapping_name = 3 # Spalte D
        
        for idx, row in df_xp.iloc[start_row_data:].iterrows():
            if len(row) > col_idx_mapping_tag:
                cell_val = str(row.iloc[col_idx_mapping_tag]).strip().lower()
                if cell_val == input_clean:
                    real_name_found = str(row.iloc[col_idx_mapping_name])
                    break
        
        if not real_name_found:
            st.error(f"Gamertag '{gamertag_input}' nicht in der Klassenliste (Spalte E) gefunden.")
            st.stop()
            
        # --- SCHRITT B: XP & LEVEL FINDEN (Rechter Bereich) ---
        # Da es mehrere Ranglisten gibt (Spalte L, R, Y...), scannen wir den ganzen
        # Bereich ab Spalte K (Index 10) nach dem Gamertag.
        
        search_area_start_col = 10
        
        # Wir iterieren über das Grid (etwas rechenintensiver, aber sicher)
        # Wir beschränken uns auf die ersten 200 Zeilen, um Performance zu sparen
        for idx in range(start_row_data, min(len(df_xp), 200)):
            row = df_xp.iloc[idx]
            
            # Suche in allen Spalten ab Index 10
            for col_idx in range(search_area_start_col, len(row)):
                cell_val = str(row.iloc[col_idx]).strip().lower()
                
                if cell_val == input_clean:
                    # GEFUNDEN!
                    # Struktur ist immer: Gamertag | XP | Level | Stufe
                    # Also: col_idx | +1 | +2 | +3
                    try:
                        if col_idx + 3 < len(row):
                            raw_xp = row.iloc[col_idx + 1]
                            raw_level = row.iloc[col_idx + 2]
                            raw_stufe = str(row.iloc[col_idx + 3])
                            
                            # Game Over Check
                            check_str = f"{raw_level} {raw_stufe}".lower()
                            is_game_over = "†" in check_str or "game" in check_str or "over" in check_str or "tot" in check_str

                            # XP Zahl bereinigen
                            try:
                                xp_str = str(raw_xp).replace('.', '').replace(',', '.')
                                xp_val = int(float(xp_str))
                            except:
                                xp_val = 0
                                
                            # Level bereinigen (falls '†' drin steht)
                            level_val = raw_level
                            if "†" in str(level_val): level_val = "💀"

                            found_stats = {
                                "xp": xp_val,
                                "level": level_val,
                                "is_game_over": is_game_over
                            }
                            break # Spalten-Loop brechen
                    except:
                        pass
            
            if found_stats:
                break # Zeilen-Loop brechen

        if found_stats:
            # --- ANZEIGE ---
            if not found_stats["is_game_over"]:
                st.balloons()
                st.success(f"Willkommen zurück, **{gamertag_input}**!")
            
            c1, c2 = st.columns(2)
            c1.metric("Level", str(found_stats["level"]))
            c2.metric("XP Total", found_stats["xp"])
            
            if found_stats["is_game_over"]:
                 st.markdown("""
                <div style="background-color: #ff4b4b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: white; font-size: 80px; margin: 0;">💀</h1>
                    <h2 style="color: white; margin: 0; font-weight: bold;">GAME OVER</h2>
                </div>
                """, unsafe_allow_html=True)
            else:
                prog_val, prog_text = calculate_progress(found_stats["xp"])
                st.progress(prog_val, text=prog_text)

            # ---------------------------------------------------------
            # TEIL 2: QUESTBUCH LADEN
            # ---------------------------------------------------------
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Quest-Namen Zeile 2 (Index 1)
            quest_names_row = df_quests.iloc[1]
            
            # Schülersuche im Questbuch
            q_idx = -1
            
            # Name aufbereiten: "11T1 Antonia Brummer" -> ["antonia", "brummer"]
            # Wir entfernen gängige Klassenbezeichnungen um "clean" zu suchen
            name_clean = real_name_found.lower()
            for k in ["11t1", "11t2", "11t3", "11t4", "12t1", "12t2", "13t1"]:
                name_clean = name_clean.replace(k, "")
            
            search_tokens = [t for t in name_clean.split(" ") if len(t) > 2]
            if not search_tokens: search_tokens = [real_name_found.lower()]

            # Suche ab Zeile 3
            for idx in range(2, len(df_quests)):
                row = df_quests.iloc[idx]
                
                # Name steht meist in Spalte B (Index 1)
                # Wir checken Spalte A und B zusammen
                name_cell_full = f"{str(row.iloc[0])} {str(row.iloc[1])}".lower()
                
                match = True
                for token in search_tokens:
                    if token not in name_cell_full:
                        match = False
                        break
                
                if match and len(name_cell_full.strip()) > 3:
                    q_idx = idx
                    break
            
            if q_idx != -1:
                student_row = df_quests.iloc[q_idx]
                
                st.divider()
                c_switch, c_text = st.columns([1, 4])
                with c_switch:
                    show_done = st.toggle("Erledigte anzeigen", value=False)
                
                if show_done:
                    st.subheader("✅ Erledigte Quests")
                else:
                    st.subheader("❌ Offene Quests")

                cols = st.columns(3)
                cnt = 0
                found_any = False
                
                # --- QUEST LOGIK (Doppelspalten) ---
                max_col = min(len(quest_names_row), len(student_row))
                
                # Starte bei Spalte D (Index 3), springe immer 2 weiter
                for c in range(3, max_col - 1, 2):
                    try:
                        # 1. Name aus Header
                        q_name = str(quest_names_row.iloc[c])
                        if q_name == "nan" or not q_name.strip(): continue
                        
                        # Filter
                        if any(x in q_name.lower() for x in ["summe", "game", "total"]): continue

                        # 2. Status aus Schüler-Zeile
                        status_val = str(student_row.iloc[c]).strip().lower()
                        
                        # 3. XP aus Schüler-Zeile (Nachbarspalte)
                        xp_val_raw = student_row.iloc[c + 1]
                        try:
                            xp_val = int(float(str(xp_val_raw).replace(',', '.')))
                        except:
                            xp_val = "?"

                        # Status bestimmen
                        is_completed = "abgeschlossen" in status_val and "nicht" not in status_val
                        # Zusatz: Wenn XP > 0, dann auch fertig
                        if isinstance(xp_val, int) and xp_val > 0: is_completed = True

                        if show_done:
                            if is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.success(f"**{q_name}**\n\n+{xp_val} XP")
                                cnt += 1
                        else:
                            if not is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                        <strong>{q_name}</strong><br>🔒 {xp_val} XP
                                    </div>
                                    """, unsafe_allow_html=True)
                                cnt += 1
                    except:
                        continue
                
                if not found_any:
                    st.info("Keine Einträge in dieser Ansicht.")

            else:
                st.warning(f"Konnte Quest-Log für '{real_name_found}' nicht laden.")
                st.caption(f"Wir haben im Questbuch nach diesen Namensteilen gesucht: {search_tokens}")

        else:
            # Fall: Name in der Liste gefunden, aber keine Stats in den Ranglisten
            st.warning(f"Gamertag '{gamertag_input}' gefunden, aber keine XP-Daten in den Ranglisten.")
            st.info("Mögliche Gründe:\n- Du hast noch keine 0 XP überschritten.\n- Du stehst in keiner der rechten Ranglisten.")

    else:
        # Kein Input
        pass

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")


