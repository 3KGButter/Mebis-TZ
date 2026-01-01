import streamlit as st
import pandas as pd
import os

# --- KONFIGURATION ---
st.set_page_config(page_title="Questlog", page_icon="🛡️", layout="centered")
st.title("🛡️ Questlog")

# Hier den exakten Dateinamen deiner Excel-Datei eintragen
LOCAL_EXCEL_FILE = "XP Rechner 4.1 25_26.xlsx"

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
    
    current_level_start = LEVEL_THRESHOLDS[current_level]
    if current_level >= 16:
        return 1.0, "Maximales Level erreicht! 🏆"
        
    next_level_start = LEVEL_THRESHOLDS[current_level + 1]
    xp_gained = current_xp - current_level_start
    xp_needed = next_level_start - current_level_start
    
    if xp_needed <= 0: return 1.0, "Level Up!"
    progress = max(0.0, min(1.0, xp_gained / xp_needed))
    return progress, f"{int(xp_gained)} / {int(xp_needed)} XP zum nächsten Level"

def clean_number(val):
    if pd.isna(val) or str(val).strip() == "": return 0
    if isinstance(val, (int, float)): return int(val)
    s = str(val).strip()
    if s.endswith(".0"): s = s[:-2]
    s = s.replace('.', '').replace(',', '.')
    try: return int(float(s))
    except: return 0

def is_checkbox_checked(val):
    if pd.isna(val): return False
    if isinstance(val, bool): return val
    if isinstance(val, (int, float)): return val >= 1
    s = str(val).strip().upper()
    return s in ["TRUE", "WAHR", "1", "CHECKED", "YES", "ON"]

# --- DATEN LADEN (LOKAL) ---
@st.cache_data
def load_excel_data(sheet_name, header_row=0):
    if not os.path.exists(LOCAL_EXCEL_FILE):
        return None
    try:
        # engine='openpyxl' ist wichtig für .xlsx Dateien
        return pd.read_excel(LOCAL_EXCEL_FILE, sheet_name=sheet_name, header=header_row, engine='openpyxl')
    except Exception as e:
        st.error(f"Fehler beim Lesen der Datei: {e}")
        return None

# --- SIDEBAR ---
with st.sidebar:
    if st.button("🔄 Daten neu laden"):
        st.cache_data.clear()
        st.rerun()
    st.info("Modus: Lokale Excel-Datei")

# ----------------------------------------------------------------
# 1. LOGIN & LEVEL (XP Rechner 3.0)
# ----------------------------------------------------------------
# Header ist in Zeile 2 (Index 1)
df_xp = load_excel_data("XP Rechner 3.0", header_row=1)

if df_xp is None:
    st.error(f"Datei '{LOCAL_EXCEL_FILE}' nicht gefunden! Bitte in denselben Ordner legen.")
    st.stop()

gamertag_inp = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

if gamertag_inp:
    user_tag = gamertag_inp.strip().lower()
    found_idx = -1
    stats = None
    
    # Suche ab Spalte L (Index 11)
    for col_i in range(11, len(df_xp.columns)):
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
                    
                    raw_info = ""
                    if col_i + 3 < len(df_xp.columns):
                        raw_info = str(row.iloc[col_i + 3])
                        
                    is_go = "†" in str(raw_lvl) or "game" in raw_info.lower() or "over" in raw_info.lower()
                    stats = {"xp": clean_number(raw_xp), "level": raw_lvl, "is_go": is_go}
                break
    
    if stats and found_idx != -1:
        try:
            real_name = str(df_xp.iloc[found_idx, 3]) # Spalte D = Name
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
            st.success(f"Hallo **{gamertag_inp}**!")
            c1, c2 = st.columns(2)
            c1.metric("Level", lvl_display)
            c2.metric("XP Total", stats["xp"])
            prog, txt = calculate_progress(stats["xp"])
            st.progress(prog, text=txt)

        # ----------------------------------------------------------------
        # 2. QUESTBUCH (Questbuch 4.0)
        # ----------------------------------------------------------------
        # header=None, damit wir Zeilen per Index 0,1,2... ansprechen
        df_q = load_excel_data("Questbuch 4.0", header_row=None)
        
        if df_q is not None:
            # Zeile 2 (Index 1) = Questnamen
            header_row = df_q.iloc[1]
            # Zeile 5 (Index 4) = Master XP
            master_xp_row = df_q.iloc[4]
            
            # Schüler suchen (ab Zeile 7 / Index 6)
            q_row_idx = -1
            
            # Namenssuche (bisschen tolerant bei Leerzeichen)
            search_parts = [p for p in real_name.lower().replace("11t1","").split() if len(p) > 2]
            if not search_parts: search_parts = [real_name.lower()]
            
            for i in range(6, len(df_q)):
                r = df_q.iloc[i]
                # Kombiniere Spalte A-D für Suche
                txt = " ".join([str(x) for x in r.iloc[0:4]]).lower()
                if all(p in txt for p in search_parts):
                    q_row_idx = i
                    break
            
            if q_row_idx != -1:
                student_row = df_q.iloc[q_row_idx]
                
                st.divider()
                show_done = st.toggle("✅ Erledigte anzeigen", value=True)
                cols = st.columns(3)
                cnt = 0
                found_any = False
                
                # Wir merken uns, welche Spalten wir schon hatten
                processed_cols = set()

                # --- DER QUEST SCANNER ---
                # Wir gehen jede Spalte durch.
                for c in range(0, len(header_row)):
                    if c in processed_cols: continue
                    
                    q_name = str(header_row.iloc[c])
                    q_name_clean = q_name.strip().lower()
                    
                    # 1. STOP LOGIK: Wenn CP oder Gesamtsumme kommt -> Abbrechen
                    if q_name_clean == "cp" or "gesamtsumme" in q_name_clean or "game-over?" in q_name_clean:
                        break
                    
                    # 2. FILTER: Leere Spalten oder Metadaten überspringen
                    if q_name == "nan" or not q_name.strip(): continue
                    if q_name_clean in ["quest", "kachel", "code", "levelaufstieg?", "bezeichnung"]: continue
                    if any(s in q_name_clean for s in ["questart", "summe", "total", "gold"]): continue
                    
                    # --- DATEN ZIEHEN ---
                    # Master XP steht in derselben Spalte (C) in Zeile 5
                    master_xp = 0
                    try: master_xp = clean_number(master_xp_row.iloc[c])
                    except: pass
                    
                    # Status (Schüler) steht in derselben Spalte (C)
                    status_text = ""
                    status_raw = None
                    try: 
                        status_raw = student_row.iloc[c]
                        status_text = str(status_raw).strip().upper()
                    except: pass
                    
                    # XP (Schüler) stehen in Spalte C+1 (Rechts daneben)
                    student_xp = 0
                    try: student_xp = clean_number(student_row.iloc[c+1])
                    except: pass
                    
                    # --- ENTSCHEIDUNG ---
                    is_completed = False
                    
                    # 1. Punkte > 0 in C+1
                    if student_xp > 0: 
                        is_completed = True
                    # 2. Status "ABGESCHLOSSEN" in C
                    elif "ABGESCHLOSSEN" in status_text and "NICHT" not in status_text:
                        is_completed = True
                    # 3. Checkbox in C (Wichtig für Arbeitsprobe)
                    elif is_checkbox_checked(status_raw):
                        is_completed = True
                    
                    # --- ANZEIGE WERT ---
                    display_xp = student_xp
                    
                    # FIX: Wenn fertig, aber 0 Punkte -> Master XP nutzen
                    if is_completed and display_xp == 0:
                        display_xp = master_xp
                        # Zwang für Arbeitsprobe (falls Master XP dort auch 0 ist)
                        if display_xp == 0 and ("ARBEITSPROBE" in q_name.upper() or "BOSS" in q_name.upper()):
                            display_xp = 2500
                    
                    # Wenn offen, zeige Master XP als "Soll"
                    if not is_completed and display_xp == 0:
                        display_xp = master_xp
                    
                    # --- RENDER ---
                    should_show = False
                    # Zeige, wenn (Erledigt AN & ist fertig) ODER (Erledigt AUS & ist offen)
                    if show_done and is_completed: should_show = True
                    if not show_done and not is_completed: should_show = True
                    
                    # Nur rendern, wenn es auch Punkte gibt
                    if should_show and display_xp > 0:
                        found_any = True
                        with cols[cnt % 3]:
                            if is_completed:
                                st.success(f"**{q_name}**\n\n+{display_xp} XP")
                            else:
                                st.markdown(f"""
                                <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                    <strong>{q_name}</strong><br>🔒 {display_xp} XP
                                </div>""", unsafe_allow_html=True)
                        cnt += 1
                    
                    # Markiere C und C+1 als erledigt
                    processed_cols.add(c)
                    processed_cols.add(c+1)

                if not found_any:
                    st.info("Keine Einträge gefunden.")
            else:
                st.warning(f"Konnte '{real_name}' nicht finden.")
    else:
        st.error("Gamertag nicht gefunden.")
