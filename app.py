import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="🛡️", layout="centered")
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
    
    xp_gained = current_xp - current_level_start
    xp_needed = next_level_start - current_level_start
    
    if xp_needed <= 0: return 1.0, "Level Up!"
    
    progress = max(0.0, min(1.0, xp_gained / xp_needed))
    return progress, f"{int(xp_gained)} / {int(xp_needed)} XP zum nächsten Level"

def clean_number(val):
    """Macht aus allem sicher eine Zahl (z.B. '4349.0' -> 4349)."""
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

# --- VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_xp = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("🔄 Aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("v28.0 - Name(c) & Master(c) vs XP(c+1)")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ----------------------------------------------------------------
    # 1. LOGIN & XP (XP Rechner 3.0)
    # ----------------------------------------------------------------
    try:
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_xp, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_xp}': {e}")
        st.stop()

    st.info("Bitte Gamertag eingeben:")
    gamertag_inp = st.text_input("Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_inp:
        user_tag = gamertag_inp.strip().lower()
        
        found_idx = -1
        stats = None
        
        # Suche Gamertag ab Spalte L (Index 11)
        start_col = 11
        for col_i in range(start_col, len(df_xp.columns)):
            col_header = str(df_xp.columns[col_i]).strip()
            if "Gamertag" in col_header:
                col_vals = df_xp.iloc[:, col_i].astype(str).str.strip().str.lower()
                matches = col_vals[col_vals == user_tag].index
                if not matches.empty:
                    found_idx = matches[0]
                    row = df_xp.iloc[found_idx]
                    # XP sind 1 Spalte rechts, Level 2 Spalten rechts
                    if col_i + 2 < len(df_xp.columns):
                        raw_xp = row.iloc[col_i + 1]
                        raw_lvl = row.iloc[col_i + 2] if col_i + 2 < len(df_xp.columns) else 0
                        raw_info = str(row.iloc[col_i + 3]) if col_i + 3 < len(df_xp.columns) else ""
                        is_go = "†" in str(raw_lvl) or "game" in raw_info.lower() or "over" in raw_info.lower()
                        
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
            if "†" in lvl_display: lvl_display = "💀"
            else:
                try: lvl_display = str(int(float(str(lvl_display).replace(',','.'))))
                except: pass

            if stats["is_go"]:
                st.error("💀 GAME OVER")
            else:
                st.success(f"Willkommen, **{gamertag_inp}**!")
                c1, c2 = st.columns(2)
                c1.metric("Level", lvl_display)
                c2.metric("XP Total", stats["xp"])
                prog, txt = calculate_progress(stats["xp"])
                st.progress(prog, text=txt)

            # ----------------------------------------------------------------
            # 2. QUESTBUCH (Die "D2/D5 -> E7" Logik)
            # ----------------------------------------------------------------
            try:
                df_q = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Questbuch nicht gefunden.")
                st.stop()

            # --- HEADER (Zeile 2 / Index 1) ---
            header_row = df_q.iloc[1]
            
            # --- MASTER XP (Zeile 5 / Index 4) ---
            master_xp_row = df_q.iloc[4]
            
            # --- SCHÜLERSUCHE ---
            q_row_idx = -1
            search_str = real_name.lower()
            for k in ["11t1", "11t2", "11t3", "11t4"]: 
                search_str = search_str.replace(k.lower(), "")
            parts = [p for p in search_str.split() if len(p) > 2]
            if not parts: parts = [search_str]
            
            # Suche ab Zeile 7 (Index 6)
            start_row_search = 6
            for i in range(start_row_search, len(df_q)):
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
                show_done = st.toggle("✅ Erledigte anzeigen", value=True)
                
                if show_done:
                    st.subheader("✅ Erledigte Quests")
                else:
                    st.subheader("❌ Offene Quests")

                cols = st.columns(3)
                cnt = 0
                found_any = False
                processed_cols = set()

                max_cols = len(header_row)
                
                # --- QUEST SCANNER ---
                # Wir laufen JEDE Spalte ab. Wenn wir einen Namen finden, prüfen wir c+1.
                
                for c in range(0, max_cols):
                    if c in processed_cols: continue
                    
                    q_name = str(header_row.iloc[c])
                    q_name_clean = q_name.strip().lower()
                    
                    # 1. STOP LOGIK (CP, Gesamtsumme, Game-Over)
                    if "gesamtsumme" in q_name_clean or "game-over?" in q_name_clean or q_name_clean == "cp":
                        break
                    
                    # 2. FILTER: Leere Spalten oder Metadaten überspringen
                    if q_name == "nan" or not q_name.strip(): continue
                    if q_name_clean in ["quest", "quest ", "kachel", "code", "levelaufstieg?", "bezeichnung"]: continue
                    if any(s in q_name_clean for s in ["questart", "summe", "total", "gold"]): continue
                    
                    # JETZT SIND WIR SICHER: Spalte 'c' ist eine Quest (z.B. Spalte D)
                    
                    # --- DATEN HOLEN ---
                    
                    # A. Master XP aus Zeile 5, Spalte C (D5)
                    master_xp = 0
                    try:
                        master_xp = clean_number(master_xp_row.iloc[c])
                    except: pass
                    
                    # B. Schüler XP aus Zeile Student, Spalte C+1 (E7 - Rechts daneben!)
                    student_xp = 0
                    try:
                        # Safe Read, falls Zeile kürzer
                        if c+1 < len(student_row):
                            student_xp = clean_number(student_row.iloc[c+1])
                    except: pass

                    # --- LOGIK: ERLEDIGT? ---
                    # Einfachste Regel der Welt: Hast du Punkte (>0)? Dann fertig.
                    is_completed = student_xp > 0
                    
                    # --- ANZEIGE WERT ---
                    display_xp = student_xp if is_completed else master_xp
                    
                    # --- RENDER ---
                    # Zeige nur an, wenn es auch Punkte zu holen gibt
                    if display_xp > 0:
                        if show_done:
                            if is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.success(f"**{q_name}**\n\n+{display_xp} XP")
                                cnt += 1
                        else:
                            if not is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                        <strong>{q_name}</strong><br>🔒 {display_xp} XP
                                    </div>
                                    """, unsafe_allow_html=True)
                                cnt += 1
                    
                    # Spalte c ist verarbeitet. Spalte c+1 (XP) ignorieren wir im nächsten Loop,
                    # da sie keinen Header hat (wegen Merged Cells oder leer).
                    processed_cols.add(c)
                    processed_cols.add(c+1)

                if not found_any:
                    if show_done:
                        st.info("Noch keine Quests erledigt.")
                    else:
                        st.success("Keine offenen Quests mehr!")

            else:
                st.warning(f"Konnte Daten für '{real_name}' im Questbuch nicht finden.")

        else:
            st.error("Gamertag nicht gefunden.")

except Exception as e:
    st.error(f"Fehler: {e}")


