import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="🛡️")
st.title("🛡️ Questlog")

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

# Hilfsfunktion für XP-Bereinigung (Löst das 10x Problem)
def clean_xp_value(val):
    if pd.isna(val) or val == "":
        return 0
    
    # Wenn es schon eine Zahl ist (int oder float)
    if isinstance(val, (int, float)):
        return int(val)
    
    # Wenn es ein String ist
    s_val = str(val).strip()
    
    # Fall: "4349.0" -> Das ".0" muss weg, nicht einfach der Punkt!
    if s_val.endswith(".0"):
        s_val = s_val[:-2]
        
    try:
        # Versuch 1: Als float parsen (behandelt "4349" und "4349.5")
        return int(float(s_val.replace(',', '.')))
    except:
        # Versuch 2: Tausenderpunkte entfernen (falls "4.349" gemeint ist als 4349)
        # Aber Vorsicht: Im Englischen ist . Dezimal. 
        # Wir gehen davon aus, dass in Google Sheets rohe Zahlen stehen.
        try:
            return int(float(s_val))
        except:
            return 0

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

# Button zum Neuladen
with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.6 (Fix: XP Berechnung & Quest Spalten)")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- TEIL 1: XP RECHNER ---
    try:
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Gib deinen Gamertag ein, um deinen Status zu prüfen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        found_row_index = -1
        best_stats = None
        
        # Suche in Spalten L (Index 11) bis Ende
        target_col_start = 11 
        
        for col_idx in range(target_col_start, len(df_xp.columns)):
            col_header = str(df_xp.columns[col_idx]).strip()
            
            if "Gamertag" in col_header:
                col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
                matches = col_data[col_data == input_clean].index
                
                if not matches.empty:
                    found_row_index = matches[0]
                    row = df_xp.iloc[found_row_index]
                    
                    if col_idx + 2 < len(df_xp.columns):
                        raw_xp = row.iloc[col_idx + 1] # Spalte M
                        raw_level = row.iloc[col_idx + 2] # Spalte N
                        
                        raw_stufe = ""
                        if col_idx + 3 < len(df_xp.columns):
                            raw_stufe = str(row.iloc[col_idx + 3])
                            
                        check_str = f"{raw_level} {raw_stufe}".lower()
                        is_game_over = "†" in check_str or "game" in check_str or "over" in check_str
                        
                        # XP BEREINIGUNG
                        xp_val = clean_xp_value(raw_xp)
                            
                        best_stats = {
                            "xp": xp_val,
                            "level": raw_level,
                            "is_game_over": is_game_over
                        }
                    break

        if best_stats and found_row_index != -1:
            # --- ECHTEN NAMEN HOLEN (Spalte D / Index 3) ---
            try:
                real_name_found = str(df_xp.iloc[found_row_index, 3])
            except:
                real_name_found = "Unbekannt"

            # --- ANZEIGE STATS ---
            display_level = str(best_stats["level"])
            try:
                # Level säubern (falls Kommazahl)
                display_level = str(int(float(str(display_level).replace(',', '.'))))
            except:
                pass 
            
            if "†" in str(best_stats["level"]): display_level = "💀"
                
            xp_num = best_stats["xp"]
            is_go = best_stats["is_game_over"]

            if not is_go:
                st.balloons()
                st.success(f"Willkommen zurück, **{gamertag_input}**!")
            
            c1, c2 = st.columns(2)
            c1.metric("Level", display_level)
            c2.metric("XP Total", xp_num)
            
            if not is_go:
                prog_val, prog_text = calculate_progress(xp_num)
                st.progress(prog_val, text=prog_text)
            else:
                st.markdown("""
                <div style="background-color: #ff4b4b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: white; font-size: 80px; margin: 0;">💀</h1>
                    <h2 style="color: white; margin: 0; font-weight: bold;">GAME OVER</h2>
                </div>
                """, unsafe_allow_html=True)

            # --- TEIL 2: QUESTS LADEN ---
            try:
                # header=None -> Zugriff per Index (0, 1, 2...)
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Quest-Namen stehen in Zeile 2 (Index 1)
            quest_names_row = df_quests.iloc[1]
            
            # --- SCHÜLER SUCHEN ---
            q_idx = -1
            
            # Namensaufbereitung
            search_name_clean = real_name_found.strip().lower()
            # Entferne Klassenbezeichnungen
            for kl in ["11t1", "11t2", "11t3", "11t4", "12t1", "13t1"]:
                search_name_clean = search_name_clean.replace(kl, "")

            search_tokens = [t for t in search_name_clean.split(" ") if len(t) > 2]
            if not search_tokens: search_tokens = [search_name_clean]

            # Suche erst ab Zeile 5 (Datenbereich)
            for idx in range(4, len(df_quests)):
                row = df_quests.iloc[idx]
                
                # Wir kombinieren Spalte A und B (Index 0 und 1) für den Namen
                row_txt = f"{str(row.iloc[0])} {str(row.iloc[1])}".lower()
                
                match_all = True
                for token in search_tokens:
                    if token not in row_txt:
                        match_all = False
                        break
                
                if match_all:
                    q_idx = idx
                    break
            
            if q_idx != -1:
                student_quest_row = df_quests.iloc[q_idx]
                
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
                
                # --- QUEST SCHLEIFE ---
                # Beginne bei Spalte D (Index 3). Schrittweite 2.
                # Spalte C (Index 3) -> Status
                # Spalte C+1 (Index 4) -> XP
                
                max_cols = min(len(quest_names_row), len(student_quest_row))
                
                for c in range(3, max_cols - 1, 2):
                    try:
                        q_name = str(quest_names_row.iloc[c])
                        
                        # Fix: Manchmal steht der Name eine Spalte davor oder ist leer
                        if q_name == "nan" or not q_name.strip():
                            continue
                        
                        # Filter
                        if any(x in q_name.lower() for x in ["summe", "game", "total", "questart"]): continue

                        # Werte holen
                        val_status = str(student_quest_row.iloc[c]).strip().lower()
                        val_xp_raw = student_quest_row.iloc[c+1]
                        
                        xp_val = clean_xp_value(val_xp_raw)
                        if xp_val == 0: xp_val = "?"

                        # Status bestimmen
                        is_completed = "abgeschlossen" in val_status and "nicht" not in val_status
                        
                        # Wenn XP > 0, ist es fertig (auch wenn Status komisch ist)
                        if isinstance(xp_val, int) and xp_val > 0:
                            is_completed = True

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
                    except Exception as loop_err:
                        # Debugging im Fehlerfall, aber leise weitermachen
                        continue
                
                if not found_any:
                    st.info("Keine Einträge in dieser Kategorie.")

            else:
                st.warning(f"Konnte Quests für '{real_name_found}' nicht laden.")
                st.caption(f"Gesucht nach Teilen von: {search_tokens}")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")


