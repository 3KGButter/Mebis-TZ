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
    """Macht aus 4349.0 -> 4349 und fängt Fehler ab."""
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
    st.caption("v9.0 - Safe Header Loop")

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

    st.info("Bitte Gamertag eingeben:")
    gamertag_inp = st.text_input("Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_inp:
        user_tag = gamertag_inp.strip().lower()
        
        found_idx = -1
        stats = None
        real_name = "Unbekannt"
        
        # Suche ab Spalte L (Index 11)
        start_col = 11
        # Wir begrenzen die Suche nicht, falls Spalten hinzugefügt wurden
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
                        is_go = "†" in str(raw_lvl) or "game" in raw_info.lower() or "over" in raw_info.lower()
                        
                        stats = {
                            "xp": clean_number(raw_xp),
                            "level": raw_lvl,
                            "is_go": is_go
                        }
                    break
        
        if stats and found_idx != -1:
            try:
                # Name aus Spalte D (Index 3)
                real_name = str(df_xp.iloc[found_idx, 3])
            except: pass

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
                df_q = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Questbuch nicht gefunden.")
                st.stop()

            # --- HEADER UND MASTER DATEN ---
            # Zeile 2 (Index 1) sind die Questnamen
            header_row = df_q.iloc[1]
            # Zeile 5 (Index 4) sind die Master XP Werte
            master_xp_row = df_q.iloc[4]
            
            # --- SCHÜLERSUCHE ---
            q_row_idx = -1
            search_str = real_name.lower()
            for k in ["11t1", "11t2", "11t3", "11t4"]: search_str = search_str.replace(k.lower(), "")
            parts = [p for p in search_str.split() if len(p) > 2]
            if not parts: parts = [search_str]
            
            # Wir suchen ab Zeile 5 (Index 4) nach unten
            for i in range(4, len(df_q)):
                r = df_q.iloc[i]
                # Kombiniere Spalte A-D für die Suche, um sicher zu sein
                txt = " ".join([str(x) for x in r.iloc[0:4]]).lower()
                
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
                
                if show_done:
                    st.subheader("✅ Erledigte Quests")
                else:
                    st.subheader("❌ Offene Quests")

                cols = st.columns(3)
                cnt = 0
                found_any = False
                processed_cols = set()

                # CRITICAL FIX: Wir nutzen die Länge des Headers, NICHT des Schülers
                max_cols = len(header_row)
                
                for c in range(3, max_cols):
                    if c in processed_cols: continue
                    
                    q_name = str(header_row.iloc[c])
                    
                    # Filter
                    if q_name == "nan" or not q_name.strip(): continue
                    if any(x in q_name.lower() for x in ["summe", "total", "questart", "xp", "gold", "variable"]): continue
                    
                    # --- DATEN HOLEN ---
                    
                    # 1. Master XP (Zeile 5) - Wir schauen rechts (c+1) oder hier (c)
                    master_xp = 0
                    try:
                        if c+1 < len(master_xp_row):
                            master_xp = clean_number(master_xp_row.iloc[c+1])
                        if master_xp == 0:
                            master_xp = clean_number(master_xp_row.iloc[c])
                    except: pass
                    
                    # 2. Schüler Status & XP
                    # Wir verwenden try/except Blocks für jeden Zugriff, falls die Zeile zu kurz ist
                    status_text = ""
                    student_xp = 0
                    
                    try:
                        if c < len(student_row):
                            status_text = str(student_row.iloc[c]).lower()
                    except: pass
                    
                    try:
                        if c+1 < len(student_row):
                            student_xp = clean_number(student_row.iloc[c+1])
                    except: pass

                    # --- LOGIK ---
                    is_completed = False
                    
                    # A: Text sagt "abgeschlossen" (und nicht "nicht")
                    if "abgeschlossen" in status_text and "nicht" not in status_text:
                        is_completed = True
                    
                    # B: Schüler hat Punkte (>0)
                    if student_xp > 0:
                        is_completed = True
                        
                    # Welchen XP Wert zeigen wir an?
                    display_xp = student_xp if student_xp > 0 else master_xp
                    
                    # Markiere benutzte Spalten (damit wir c+1 nicht nochmal als Quest lesen)
                    # Wir nehmen an, dass XP immer rechts steht, wenn Master XP rechts gefunden wurde
                    if master_xp > 0 and c+1 < max_cols:
                         processed_cols.add(c+1)

                    # --- ANZEIGE ---
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


