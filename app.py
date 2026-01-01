import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURATION ---
st.set_page_config(page_title="Questlog", page_icon="ðŸ›¡ï¸", layout="centered")
st.title("ðŸ›¡ï¸ Questlog")

# Level-Tabelle
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
        return 1.0, "Maximales Level erreicht! ðŸ†"
    
    current_level_start = LEVEL_THRESHOLDS[current_level]
    next_level_start = LEVEL_THRESHOLDS[current_level + 1]
    
    xp_gained = current_xp - current_level_start
    xp_needed = next_level_start - current_level_start
    
    if xp_needed <= 0: return 1.0, "Level Up!"
    
    progress = max(0.0, min(1.0, xp_gained / xp_needed))
    return progress, f"{int(xp_gained)} / {int(xp_needed)} XP zum nächsten Level"

def clean_number(val):
    """Macht aus allem sicher eine Zahl."""
    if pd.isna(val) or str(val).strip() == "":
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip()
    if s.endswith(".0"): s = s[:-2]
    s = s.replace('.', '').replace(',', '.')
    try:
        return int(float(s))
    except:
        return 0

def is_checkbox_checked(val):
    """PrÃ¼ft auf Checkboxen (True, 1, WAHR, CHECKED)."""
    if pd.isna(val): return False
    if isinstance(val, bool): return val
    if isinstance(val, (int, float)): return val >= 1
    s = str(val).strip().upper()
    return s in ["TRUE", "WAHR", "1", "CHECKED", "YES", "ON"]

# --- VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_xp = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("ðŸ”„ Aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("v30.0 - Final Logic (C=Name/Status, C+1=XP)")
    debug_mode = st.checkbox("🔍 Debug-Modus", value=False)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ----------------------------------------------------------------
    # 1. LOGIN & LEVEL (XP Rechner 3.0)
    # ----------------------------------------------------------------
    try:
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_xp, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_xp}': {e}")
        st.stop()

        # Defensive checks: ensure the sheet has the expected shape (at least header + columns A-G)
        if df_xp is None or df_xp.shape[0] < 2 or df_xp.shape[1] < 5:
            st.error(f"Die Tabelle '{blatt_xp}' hat unerwartete Struktur: rows={0 if df_xp is None else df_xp.shape[0]}, cols={0 if df_xp is None else df_xp.shape[1]}")
            if 'debug_mode' in locals() and debug_mode:
                try:
                    st.write(df_xp.head())
                except:
                    pass
            st.stop()

    st.info("Bitte Gamertag eingeben:")
    gamertag_inp = st.text_input("Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_inp:
        user_tag = gamertag_inp.strip().lower()
        found_idx = -1
        stats = None
        
        start_col = 11
        for col_i in range(start_col, len(df_xp.columns)):
            col_header = str(df_xp.columns[col_i]).strip()
            if "Gamertag" in col_header:
                col_vals = df_xp.iloc[:, col_i].astype(str).str.strip().str.lower()
                matches = col_vals[col_vals == user_tag].index
                if not matches.empty:
                    found_idx = matches[0]
                    row = df_xp.iloc[found_idx]
                    if col_i + 2 < len(df_xp.columns):
                        raw_xp = row.iloc[col_i + 1]
                        raw_lvl = row.iloc[col_i + 2] if col_i + 2 < len(df_xp.columns) else 0
                        raw_info = str(row.iloc[col_i + 3]) if col_i + 3 < len(df_xp.columns) else ""
                        is_go = "â€ " in str(raw_lvl) or "game" in raw_info.lower() or "over" in raw_info.lower()
                        stats = {
                            "xp": clean_number(raw_xp),
                            "level": raw_lvl,
                            "is_go": is_go
                        }
                    break
        
        if stats and found_idx != -1:
            try:
                real_name = str(df_xp.iloc[found_idx, 3])
            except:
                real_name = "Unbekannt"

            lvl_display = str(stats["level"])
            if "â€ " in lvl_display: lvl_display = "ðŸ’€"
            else:
                try: lvl_display = str(int(float(str(lvl_display).replace(',','.'))))
                except: pass

            if stats["is_go"]:
                st.error("ðŸ’€ GAME OVER")
            else:
                st.success(f"Willkommen, **{gamertag_inp}**!")
                c1, c2 = st.columns(2)
                c1.metric("Level", lvl_display)
                c2.metric("XP Total", stats["xp"])
                prog, txt = calculate_progress(stats["xp"])
                prog = max(0.0, min(prog, 1.0))
                st.progress(prog)
                st.write(txt)

            # ----------------------------------------------------------------
            # 2. QUESTBUCH
            # ----------------------------------------------------------------
            try:
                df_q = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Questbuch nicht gefunden.")
                st.stop()

                # Defensive checks for Questbuch: need at least rows up to index 6 and columns from C
                if df_q is None or df_q.shape[0] < 7 or df_q.shape[1] < 3:
                    st.error(f"Die Tabelle '{blatt_quests}' hat unerwartete Struktur: rows={0 if df_q is None else df_q.shape[0]}, cols={0 if df_q is None else df_q.shape[1]}")
                    if 'debug_mode' in locals() and debug_mode:
                        try:
                            st.write(df_q.head())
                        except:
                            pass
                    st.stop()

            # --- HEADERS ---
            header_row = df_q.iloc[1]   # Zeile 2: Namen
            master_xp_row = df_q.iloc[4] # Zeile 5: Soll-XP
            
            # --- SCHÃœLERSUCHE ---
            q_row_idx = -1
            search_str = real_name.lower()
            for k in ["11t1", "11t2", "11t3", "11t4"]: 
                search_str = search_str.replace(k.lower(), "")
            parts = [p for p in search_str.split() if len(p) > 2]
            if not parts: parts = [search_str]
            
            # Suche ab Zeile 7 (Index 6)
            for i in range(6, len(df_q)):
                r = df_q.iloc[i]
                txt = " ".join([str(x) for x in r.iloc[0:4]]).lower()
                match = True
                for p in parts:
                    if p not in txt: match = False; break
                if match:
                    q_row_idx = i; break
            
            if q_row_idx != -1:
                student_row = df_q.iloc[q_row_idx]
                
                st.divider()
                # Initialize quest view state
                if "quest_view_state" not in st.session_state:
                    st.session_state.quest_view_state = "open"
                
                # Toggle buttons for Offene/Erledigte
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("⌛ Offene Quests", use_container_width=True, key="btn_open"):
                        st.session_state.quest_view_state = "open"
                with col2:
                    if st.button("✅ Erledigte Quests", use_container_width=True, key="btn_done"):
                        st.session_state.quest_view_state = "done"
                
                show_done = st.session_state.quest_view_state == "done"
                quest_view = "✅ Erledigte Quests" if show_done else "⌛ Offene Quests"
                
                st.subheader(quest_view)

                cnt = 0
                found_any = False
                processed_cols = set()

                # Collect quests first, then render according to `show_done`.
                completed_quests = []
                open_quests = []

                max_cols = len(header_row)
                
                # --- QUEST LOOP ---
                for c in range(0, max_cols):
                    if c in processed_cols: continue
                    
                    q_name = str(header_row.iloc[c])
                    q_name_clean = q_name.strip().lower()
                    
                    # 1. STOP LOGIK
                    if q_name_clean == "cp" or "gesamtsumme" in q_name_clean or "game-over?" in q_name_clean:
                        break
                    if "game" in q_name_clean and "over" in q_name_clean:
                        break
                    
                    # 2. FILTER LOGIK
                    if q_name == "nan" or not q_name.strip(): continue
                    if q_name_clean in ["quest", "quest ", "kachel", "code", "levelaufstieg?", "bezeichnung"]: continue
                    if any(s in q_name_clean for s in ["questart", "summe", "total", "gold"]): continue
                    
                    # --- DATEN HOLEN (Spalte C = Name/Master/Status, Spalte C+1 = XP) ---
                    
                    # A. Master XP (Zeile 5, Spalte C)
                    master_xp = 0
                    try:
                        master_xp = clean_number(master_xp_row.iloc[c])
                    except: pass
                    
                    # B. SchÃ¼ler Daten
                    status_text = ""
                    status_raw = None
                    student_xp = 0
                    
                    # Status lesen (Spalte C)
                    try:
                        if c < len(student_row):
                            status_raw = student_row.iloc[c]
                            status_text = str(status_raw).strip().upper()
                    except: pass
                    
                    # XP lesen (Spalte C+1 -> RECHTS!)
                    try:
                        if c+1 < len(student_row):
                            student_xp = clean_number(student_row.iloc[c+1])
                    except: pass

                    # --- ENTSCHEIDUNG ---
                    is_completed = False
                    
                    # 1. Punkte > 0
                    if student_xp > 0:
                        is_completed = True
                    # Strict rule: only numeric XP > 0 marks completion.
                    # Previously text/checkbox could mark completion even if XP == 0.
                    
                    # --- XP ANZEIGE ---
                    display_xp = student_xp
                    # When strict, do not treat text/checkbox as completion.
                    # If student_xp == 0, show master_xp as 'Soll' for open quests.
                    if not is_completed and display_xp == 0:
                        display_xp = master_xp

                    # --- AUSGABE (Sammeln) ---
                    quest_entry = {"name": q_name, "xp": display_xp, "completed": is_completed}
                    if is_completed:
                        completed_quests.append(quest_entry)
                    else:
                        open_quests.append(quest_entry)
                    
                    # Spalte C verarbeitet. C+1 (XP) Ã¼berspringen wir explizit.
                    processed_cols.add(c)
                    processed_cols.add(c+1)

                # Wähle die passende Liste zum Anzeigen
                quests_to_show = completed_quests if show_done else open_quests

                if debug_mode:
                    st.write(f"Debug: show_done={show_done}, completed={len(completed_quests)}, open={len(open_quests)}")
                    st.write("Beispiel abgeschl.:", completed_quests[:3])
                    st.write("Beispiel offen:", open_quests[:3])

                if not quests_to_show:
                    if show_done:
                        st.info("Noch keine Quests erledigt.")
                    else:
                        st.success("Keine offenen Quests mehr!")
                else:
                    cols = st.columns(3)
                    for idx, quest in enumerate(quests_to_show):
                        with cols[idx % 3]:
                            if quest["completed"]:
                                st.success(f"**{quest['name']}**\n\n✨ +{quest['xp']} XP")
                            else:
                                st.markdown(f"""
                                <div style="border:2px solid #ccc; padding:20px; border-radius:10px; 
                                            background-color:#f5f5f5; color:#333; margin-bottom:15px;">
                                    <strong>{quest['name']}</strong><br>
                                    🔒 {quest['xp']} XP
                                </div>
                                """, unsafe_allow_html=True)

            else:
                st.warning(f"Konnte Daten fÃ¼r '{real_name}' im Questbuch nicht finden.")

        else:
            st.error("Gamertag nicht gefunden.")

except Exception as e:
    st.error(f"Fehler: {e}")

