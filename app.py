import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURATION ---
st.set_page_config(page_title="FOS Tech Zeichnen - Questlog", page_icon="🛡️", layout="centered")

# CSS für schönere Progress-Bars und Karten
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .quest-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #4a4a4a;
        margin-bottom: 10px;
    }
    .xp-badge {
        background-color: #FFC107;
        color: black;
        padding: 2px 8px;
        border-radius: 5px;
        font-weight: bold;
        float: right;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Dein Questlog")

# Level-Logik (aus deiner Tabelle übernommen)
LEVEL_THRESHOLDS = {
    1: 0, 2: 42, 3: 143, 4: 332, 5: 640, 6: 1096, 7: 1728, 8: 2567,
    9: 3640, 10: 4976, 11: 6602, 12: 8545, 13: 10831, 14: 13486, 15: 16536, 16: 20003
}

def get_level_info(current_xp):
    """Berechnet Level und Fortschritt."""
    current_level = 1
    for lvl, threshold in LEVEL_THRESHOLDS.items():
        if current_xp >= threshold:
            current_level = lvl
        else:
            break
            
    if current_level >= 16:
        return current_level, 1.0, 0, 0, "Max Level! 🏆"
        
    xp_start = LEVEL_THRESHOLDS[current_level]
    xp_next = LEVEL_THRESHOLDS[current_level + 1]
    
    needed = xp_next - xp_start
    gained = current_xp - xp_start
    
    # Schutz vor Division durch Null
    if needed <= 0: return current_level, 1.0, 0, 0, "Level Up!"

    progress = max(0.0, min(1.0, gained / needed))
    return current_level, progress, int(gained), int(needed), f"{int(gained)} / {int(needed)} XP zum nächsten Level"

def clean_xp_value(val):
    """Macht aus Excel-Daten saubere Integers."""
    if pd.isna(val) or str(val).strip() == "":
        return 0
    try:
        # Kommas entfernen/ersetzen falls String
        s = str(val).replace(',', '.').strip()
        return int(float(s))
    except:
        return 0

# --- SIDEBAR ---
with st.sidebar:
    st.write("### Tech Zeichnen FOS")
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.info("Gib deinen Gamertag ein, um deinen aktuellen Stand zu prüfen.")

# --- DATEN LADEN ---
URL = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Wir laden beide Blätter komplett ohne Header, um flexibel zu bleiben
    df_xp_rechner = conn.read(spreadsheet=URL, worksheet="XP Rechner 3.0", header=None)
    df_questbuch = conn.read(spreadsheet=URL, worksheet="Questbuch 4.0", header=None)
except Exception as e:
    st.error(f"Verbindungsfehler: {e}")
    st.stop()

# --- LOGIN ---
gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt").strip()

if gamertag_input:
    found_user = False
    xp_total = 0
    real_name = ""
    
    # --- SUCHE IM XP RECHNER ---
    # Wir suchen den Gamertag überall im Blatt
    # Umwandlung in Strings und Kleinschreibung für Suche
    mask = df_xp_rechner.apply(lambda x: x.astype(str).str.strip().str.lower() == gamertag_input.lower())
    coords = list(zip(*mask.to_numpy().nonzero()))
    
    if coords:
        found_user = True
        # Nimm den ersten Treffer
        r_idx, c_idx = coords[0]
        
        # 1. VERSUCH: XP finden (Zelle rechts vom Gamertag)
        try:
            xp_total = clean_xp_value(df_xp_rechner.iloc[r_idx, c_idx + 1])
        except:
            xp_total = 0
            
        # 2. VERSUCH: Echten Namen finden (für Questbuch)
        # Wir gehen davon aus, dass der Name in derselben Zeile weiter links steht (Spalte D/E meistens)
        # Im "XP Rechner" Blatt ist Spalte D (Index 3) oft "Klasse + Name"
        try:
            # Wir schauen in Zeile r_idx, Spalte 3 (D)
            potential_name = df_xp_rechner.iloc[r_idx, 3]
            if pd.notna(potential_name):
                real_name = str(potential_name)
        except:
            pass
            
    if found_user:
        lvl, prog, gain, need, prog_txt = get_level_info(xp_total)
        
        # Header Bereich
        c1, c2 = st.columns([1, 3])
        with c1:
            st.metric("Level", lvl)
        with c2:
            st.metric("XP Gesamt", xp_total)
            st.progress(prog, text=prog_txt)

        if lvl >= 16:
            st.balloons()

        # --- QUESTBUCH MATCHING ---
        st.divider()
        st.subheader("📜 Quest-Log")
        
        if not real_name:
            st.warning("Konnte deinen echten Namen nicht zuordnen, daher keine Quest-Details möglich.")
        else:
            # Suche Schüler im Questbuch (ab Zeile 7 / Index 6)
            q_header_row = df_questbuch.iloc[1]  # Zeile 2: Namen der Quests
            q_max_xp_row = df_questbuch.iloc[4]  # Zeile 5: Max XP
            
            student_row = None
            
            # Namenssuche Logik: Wir zerlegen den gefundenen Namen und suchen Matches
            search_parts = real_name.lower().replace(",", "").split()
            
            for idx in range(6, len(df_questbuch)):
                # Prüfe die ersten 5 Spalten jeder Zeile auf Namensübereinstimmung
                row_str = " ".join([str(x) for x in df_questbuch.iloc[idx, 0:5]]).lower()
                if all(part in row_str for part in search_parts if len(part) > 2): # >2 ignoriert kurze Kürzel
                    student_row = df_questbuch.iloc[idx]
                    break
            
            if student_row is not None:
                quests_open = []
                quests_done = []
                
                # Wir gehen durch die Spalten. Start ab Spalte 2 (C). 
                # Muster: Spalte i = Status, Spalte i+1 = XP
                num_cols = len(q_header_row)
                
                for i in range(2, num_cols - 1, 2):
                    q_name = str(q_header_row[i]).strip()
                    
                    # Filter: Leere Spalten oder Summenspalten überspringen
                    if q_name == "nan" or not q_name or "Summe" in q_name or "Quest" in q_name:
                        continue
                        
                    # Daten holen
                    try:
                        xp_got = clean_xp_value(student_row[i+1]) # Die echten Punkte des Schülers
                    except: xp_got = 0
                    
                    try:
                        # Max XP steht in Zeile 5 (Index 4), meist in der XP Spalte (i+1)
                        xp_max = clean_xp_value(q_max_xp_row[i+1])
                    except: xp_max = 0
                    
                    # --- ENTSCHEIDUNGSLOGIK ---
                    # Nur wenn XP > 0 sind, gilt es als erledigt.
                    if xp_got > 0:
                        quests_done.append((q_name, xp_got))
                    else:
                        # Quest ist offen (oder hat 0 Punkte gegeben)
                        # Wir zeigen Max XP an, damit der Schüler weiß, was es zu holen gibt
                        quests_open.append((q_name, xp_max))

                # --- ANZEIGE ---
                t_open, t_done = st.tabs([f"Offen ({len(quests_open)})", f"Erledigt ({len(quests_done)})"])
                
                with t_open:
                    if not quests_open:
                        st.balloons()
                        st.success("Keine offenen Quests mehr! Super!")
                    else:
                        for name, max_p in quests_open:
                            # HTML Card für Optik
                            st.markdown(f"""
                            <div class="quest-card">
                                <strong>{name}</strong>
                                <span class="xp-badge">Möglich: {max_p} XP</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                with t_done:
                    for name, got_p in quests_done:
                        st.success(f"✅ **{name}** (+{got_p} XP)")

            else:
                st.warning(f"Konnte Daten für '{real_name}' im Questbuch nicht finden.")
    else:
        st.error("Gamertag nicht gefunden.")
