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

def clean_number(val):
    """
    Macht aus allem sicher eine Zahl.
    Löst das Problem, dass 4349.0 zu 43490 wurde.
    """
    if pd.isna(val) or str(val).strip() == "":
        return 0
    
    if isinstance(val, (int, float)):
        return int(val)
        
    s = str(val).strip()
    
    # Entferne .0 am Ende (das war der Fehlerverursacher!)
    if s.endswith(".0"):
        s = s[:-2]
        
    try:
        # Ersetze Komma durch Punkt für float-Konvertierung
        return int(float(s.replace(',', '.')))
    except:
        return 0

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 5.0 (Simple Logic)")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ------------------------------------------------------------------
    # TEIL 1: XP RECHNER
    # ------------------------------------------------------------------
    try:
        # header=1: Zeile 2 ist Überschrift
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Gib deinen Gamertag ein:")
    gamertag_input = st.text_input("Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        found_row_index = -1
        best_stats = None
        
        # Wir suchen in allen Spalten ab L (Index 11)
        # Sicherer Bereich: Bis zum Ende der Tabelle
        start_col = 11
        
        if len(df_xp.columns) > start_col:
            for col_idx in range(start_col, len(df_xp.columns)):
                col_header = str(df_xp.columns[col_idx]).strip()
                
                # Wenn "Gamertag" im Header steht, suchen wir hier
                if "Gamertag" in col_header:
                    col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
                    matches = col_data[col_data == input_clean].index
                    
                    if not matches.empty:
                        found_row_index = matches[0]
                        row = df_xp.iloc[found_row_index]
                        
                        # Prüfen ob genug Spalten rechts daneben sind (XP, Level)
                        if col_idx + 2 < len(df_xp.columns):
                            raw_xp = row.iloc[col_idx + 1]
                            raw_level = row.iloc[col_idx + 2]
                            
                            # Game Over Check
                            raw_stufe = ""
                            if col_idx + 3 < len(df_xp.columns):
                                raw_stufe = str(row.iloc[col_idx + 3])
                            
                            check_str = f"{raw_level} {raw_stufe}".lower()
                            is_game_over = "†" in check_str or "game" in check_str or "over" in check_str

                            # XP Zahl bereinigen
                            xp_val = clean_number(raw_xp)
                            
                            best_stats = {
                                "xp": xp_val,
                                "level": raw_level,
                                "is_game_over": is_game_over
                            }
                        break

        if best_stats and found_row_index != -1:
            # --- ECHTEN NAMEN FINDEN ---
            # Spalte D (Index 3) in der gleichen Zeile
            try:
                real_name_found = str(df_xp.iloc[found_row_index, 3])
            except:
                real_name_found = "Unbekannt"

            # --- ANZEIGE ---
            level_str = str(best_stats["level"])
            if "†" in level_str: level_str = "💀"
            else:
                try:
                    level_str = str(int(float(str(level_str).replace(',', '.'))))
                except: pass
                
            xp_num = best_stats["xp"]
            is_go = best_stats["is_game_over"]

            if not is_go:
                st.balloons()
                st.success(f"Hallo **{gamertag_input}**!")
            
            c1, c2 = st.columns(2)
            c1.metric("Level", level_str)
            c2.metric("XP Total", xp_num)
            
            if not is_go:
                prog_val, prog_text = calculate_progress(xp_num)
                st.progress(prog_val, text=prog_text)
            else:
                st.error("💀 GAME OVER")

            # ------------------------------------------------------------------
            # TEIL 2: QUESTS (Die simple Logik)
            # ------------------------------------------------------------------
            try:
                # header=None -> Wir arbeiten mit Indizes
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Zeile 2 (Index 1) sind die Questnamen
            quest_names_row = df_quests.iloc[1]
            
            # --- SCHÜLER SUCHEN ---
            q_idx = -1
            
            # Name putzen: "11T1 Antonia Brummer" -> "antonia", "brummer"
            clean_search = real_name_found.lower()
            for k in ["11t1", "11t2", "11t3", "11t4"]: 
                clean_search = clean_search.replace(k.lower(), "")
            
            parts = [p for p in clean_search.split() if len(p) > 2]
            if not parts: parts = [clean_search]

            # Wir suchen ab Zeile 5
            for idx in range(4, len(df_quests)):
                row = df_quests.iloc[idx]
                # Kombiniere Spalte A und B
                row_name = f"{row.iloc[0]} {row.iloc[1]}".lower()
                
                match = True
                for p in parts:
                    if p not in row_name:
                        match = False
                        break
                if match:
                    q_idx = idx
                    break
            
            if q_idx != -1:
                student_row = df_quests.iloc[q_idx]
                
                st.divider()
                # Einfacher Toggle
                show_done = st.toggle("✅ Erledigte anzeigen", value=True)
                
                cols = st.columns(3)
                cnt = 0
                found_any = False
                
                # --- QUEST LOOP ---
                # Start bei Spalte D (Index 3). Schrittweite 2.
                # Spalte C: Name/Status
                # Spalte C+1: XP-Punkte
                
                max_cols = min(len(quest_names_row), len(student_row))
                
                for c in range(3, max_cols - 1, 2):
                    try:
                        # 1. Name der Quest
                        q_name = str(quest_names_row.iloc[c])
                        if q_name == "nan" or not q_name.strip(): continue
                        
                        # Filter
                        if any(x in q_name.lower() for x in ["summe", "game", "total", "questart"]): continue

                        # 2. XP Wert holen (Rechte Spalte neben dem Namen)
                        xp_raw = student_row.iloc[c+1]
                        xp_val = clean_number(xp_raw)
                        
                        # 3. Logik: XP > 0 bedeutet erledigt.
                        is_completed = xp_val > 0
                        
                        if show_done:
                            if is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.success(f"**{q_name}**\n\n+{xp_val} XP")
                                cnt += 1
                        else:
                            # Zeige offene
                            if not is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                        <strong>{q_name}</strong><br>🔒 Offen
                                    </div>
                                    """, unsafe_allow_html=True)
                                cnt += 1
                    except:
                        continue
                
                if not found_any:
                    st.info("Keine Einträge gefunden.")

            else:
                st.warning(f"Konnte Daten für '{real_name_found}' im Questbuch nicht finden.")

        else:
            st.error("Gamertag nicht gefunden.")

except Exception as e:
    st.error(f"Fehler: {e}")


