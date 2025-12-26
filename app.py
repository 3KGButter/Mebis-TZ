import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURATION ---
st.set_page_config(page_title="Questlog", page_icon="🛡️", layout="centered")
st.title("🛡️ Questlog")

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
        return 1.0, "Maximales Level erreicht! 🏆"
    
    current_level_start = LEVEL_THRESHOLDS[current_level]
    next_level_start = LEVEL_THRESHOLDS[current_level + 1]
    
    xp_gained = current_xp - current_level_start
    xp_needed = next_level_start - current_level_start
    
    if xp_needed <= 0: return 1.0, "Level Up!"
    
    progress = max(0.0, min(1.0, xp_gained / xp_needed))
    return progress, f"{int(xp_gained)} / {int(xp_needed)} XP zum nächsten Level"

def clean_number(val):
    """
    Macht aus allem sicher eine Zahl.
    Löst das Problem 4349.0 -> 43490
    """
    if pd.isna(val) or str(val).strip() == "":
        return 0
    
    # Wenn es schon eine Zahl ist
    if isinstance(val, (int, float)):
        return int(val)
        
    s = str(val).strip()
    
    # Entferne ".0" am Ende (Das war der Hauptfehler!)
    if s.endswith(".0"):
        s = s[:-2]
    
    # Entferne Tausenderpunkte (Deutsch: 1.000 -> 1000)
    # Ersetze Komma durch Punkt
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
    st.caption("v5.1 - 'Look Right' Logic")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ----------------------------------------------------------------
    # 1. LOGIN & XP (XP Rechner 3.0)
    # ----------------------------------------------------------------
    try:
        # Wir laden header=1 (Zeile 2), da stehen die Spaltennamen
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
        
        # Wir suchen ab Spalte L (Index 11) nach "Gamertag"
        # Spaltenindizes: L=11, M=12, N=13
        start_col = 11
        
        for col_i in range(start_col, len(df_xp.columns)):
            col_header = str(df_xp.columns[col_i]).strip()
            
            if "Gamertag" in col_header:
                # Suche in dieser Spalte
                col_vals = df_xp.iloc[:, col_i].astype(str).str.strip().str.lower()
                matches = col_vals[col_vals == user_tag].index
                
                if not matches.empty:
                    found_idx = matches[0]
                    row = df_xp.iloc[found_idx]
                    
                    # Spalte rechts daneben (XP)
                    if col_i + 1 < len(df_xp.columns):
                        raw_xp = row.iloc[col_i + 1]
                        raw_lvl = row.iloc[col_i + 2] if col_i + 2 < len(df_xp.columns) else 0
                        
                        # Game Over Check
                        raw_info = str(row.iloc[col_i + 3]) if col_i + 3 < len(df_xp.columns) else ""
                        is_go = "†" in str(raw_lvl) or "game" in raw_info.lower() or "over" in raw_info.lower()
                        
                        stats = {
                            "xp": clean_number(raw_xp),
                            "level": raw_lvl,
                            "is_go": is_go
                        }
                    break
        
        if stats and found_idx != -1:
            # Name aus Spalte D (Index 3) holen
            try:
                real_name = str(df_xp.iloc[found_idx, 3])
            except:
                real_name = "Unbekannt"

            # Anzeige
            lvl_display = str(stats["level"])
            if "†" in lvl_display: lvl_display = "💀"
            else:
                try: lvl_display = str(int(float(str(lvl_display).replace(',','.'))))
                except: pass

            if stats["is_go"]:
                st.error("💀 GAME OVER")
            else:
                st.balloons()
                st.success(f"Willkommen, **{gamertag_inp}**!")
                
                c1, c2 = st.columns(2)
                c1.metric("Level", lvl_display)
                c2.metric("XP Total", stats["xp"])
                
                prog, txt = calculate_progress(stats["xp"])
                st.progress(prog, text=txt)

            # ----------------------------------------------------------------
            # 2. QUESTBUCH (Neue Logik)
            # ----------------------------------------------------------------
            try:
                # Header=None -> Wir arbeiten mit Koordinaten
                df_q = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Questbuch nicht gefunden.")
                st.stop()

            # Header Zeile ist Zeile 2 (Index 1)
            header_row = df_q.iloc[1]
            
            # --- SCHÜLERSUCHE ---
            q_row_idx = -1
            
            # Name säubern ("11T1 Antonia..." -> "antonia", "brummer")
            search_str = real_name.lower()
            for k in ["11t1", "11t2", "11t3", "11t4"]: search_str = search_str.replace(k.lower(), "")
            parts = [p for p in search_str.split() if len(p) > 2]
            if not parts: parts = [search_str]
            
            # Suche ab Zeile 5
            for i in range(4, len(df_q)):
                r = df_q.iloc[i]
                # Kombiniere Spalte A & B
                txt = f"{r.iloc[0]} {r.iloc[1]}".lower()
                
                match = True
                for p in parts:
                    if p not in txt:
                        match = False
                        break
                if match:
                    q_row_idx = i
                    break
            
            if q_row_idx != -1:
                student_row = df_q.iloc[q_row_idx]
                
                st.divider()
                show_done = st.toggle("✅ Erledigte anzeigen", value=True)
                
                cols = st.columns(3)
                cnt = 0
                found_any = False
                
                # --- QUEST ITERATION ---
                # Wir gehen durch die Header-Spalten ab D (Index 3)
                # Aber wir nehmen JEDE Spalte, prüfen ob ein Name drin steht.
                
                max_cols = min(len(header_row), len(student_row))
                
                # Wir merken uns besuchte Spalten, damit wir bei merged cells nicht doppelt zählen
                processed_cols = set()

                for c in range(3, max_cols - 1):
                    if c in processed_cols: continue
                    
                    q_name = str(header_row.iloc[c])
                    
                    # Nur wenn hier ein Questname steht
                    if q_name == "nan" or not q_name.strip(): continue
                    
                    if any(x in q_name.lower() for x in ["summe", "total", "questart", "xp", "gold"]): 
                        continue
                    
                    # JETZT DIE LOGIK:
                    # Wir prüfen die Spalte des Schülers (c) UND die rechts daneben (c+1)
                    # Suche nach XP > 0
                    
                    xp_val = 0
                    
                    # Check 1: Rechte Spalte (Standard für XP im neuen Sheet)
                    val_right = clean_number(student_row.iloc[c+1])
                    if val_right > 0:
                        xp_val = val_right
                        processed_cols.add(c+1) # Überspringe nächste Spalte im Loop
                    
                    # Check 2: Falls rechts nix war, vllt in der aktuellen Spalte?
                    if xp_val == 0:
                        val_here = clean_number(student_row.iloc[c])
                        if val_here > 0:
                            xp_val = val_here

                    is_done = xp_val > 0
                    
                    if show_done:
                        if is_done:
                            found_any = True
                            with cols[cnt % 3]:
                                st.success(f"**{q_name}**\n\n+{xp_val} XP")
                            cnt += 1
                    else:
                        if not is_done:
                            found_any = True
                            with cols[cnt % 3]:
                                st.markdown(f"""
                                <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                    <strong>{q_name}</strong><br>🔒 Offen
                                </div>
                                """, unsafe_allow_html=True)
                            cnt += 1
                
                if not found_any:
                    st.info("Keine Einträge gefunden.")

            else:
                st.warning(f"Konnte '{real_name}' im Questbuch nicht finden.")
                st.caption(f"Gesucht nach: {parts}")

        else:
            st.error("Gamertag nicht gefunden.")

except Exception as e:
    st.error(f"Fehler: {e}")


