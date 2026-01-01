import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURATION ---
st.set_page_config(page_title="FOS Tech Zeichnen - Questlog", page_icon="🛡️", layout="centered")

# CSS für etwas schönere Optik (optional)
st.markdown("""
    <style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .big-font {
        font-size:20px !important;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Dein Questlog")

# Level-Logik basierend auf deiner CSV (XP Summiert Spalte)
LEVEL_THRESHOLDS = {
    1: 0, 2: 42, 3: 143, 4: 332, 5: 640, 6: 1096, 7: 1728, 8: 2567,
    9: 3640, 10: 4976, 11: 6602, 12: 8545, 13: 10831, 14: 13486, 15: 16536, 16: 20003
}

def get_level_info(current_xp):
    """Berechnet Level und Fortschritt zum nächsten Level."""
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
    
    progress = max(0.0, min(1.0, gained / needed))
    return current_level, progress, int(gained), int(needed), f"{int(gained)} / {int(needed)} XP zum nächsten Level"

def clean_xp_value(val):
    """Hilft, XP Zahlen aus dem Excel sauber zu lesen."""
    if pd.isna(val): return 0
    try:
        # Falls es ein String ist, Komma zu Punkt etc.
        if isinstance(val, str):
            val = val.replace(',', '.').strip()
            if val == "": return 0
        return int(float(val))
    except:
        return 0

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c3/Python-logo-notext.svg", width=50) # Platzhalter Logo
    st.write("### Tech Zeichnen FOS")
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.info("Logge dich mit deinem Gamertag ein, um deinen Fortschritt zu sehen.")

# --- DATEN LADEN ---
# URL zu deinem Google Sheet
URL = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. Lade XP Rechner (für Login & Gesamt-XP)
    df_xp_rechner = conn.read(spreadsheet=URL, worksheet="XP Rechner 3.0", header=9) # Header scheint in Zeile 10 zu sein (Index 9)
    
    # 2. Lade Questbuch (für Details)
    # Wir laden ohne Header, um Zeilen manuell zu parsen
    df_questbuch = conn.read(spreadsheet=URL, worksheet="Questbuch 4.0", header=None)

except Exception as e:
    st.error(f"Fehler bei der Verbindung zu Google Sheets: {e}")
    st.stop()

# --- LOGIN BEREICH ---
gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt").strip()

if gamertag_input:
    # Suche im XP Rechner nach dem Gamertag
    # Strategie: Wir suchen im gesamten DataFrame nach dem String
    found_user = False
    user_data = {}
    
    # Wir suchen erst in der Hauptliste (Spalten A-E ca.)
    # Spalte 'Gamertag ' (mit Leerzeichen im CSV Header beachten)
    # Wir bereinigen erst die Spaltennamen
    df_xp_rechner.columns = [str(c).strip() for c in df_xp_rechner.columns]
    
    if "Gamertag" in df_xp_rechner.columns:
        # Suche in der Hauptspalte
        match = df_xp_rechner[df_xp_rechner["Gamertag"].astype(str).str.lower() == gamertag_input.lower()]
        if not match.empty:
            # Volltreffer in der Hauptliste
            row = match.iloc[0]
            # Name zusammenbauen für Questbuch Suche
            real_name = str(row.get("Klasse + Name (gedreht für Vergleich Mebis-Daten)", ""))
            # Falls das leer ist, versuchen wir Vorname + Nachname
            if not real_name or real_name == "nan":
                 real_name = f"{row.get('Vorname', '')} {row.get('Nachname', '')}"
            
            # Jetzt brauchen wir die XP. Im CSV Snippet war die XP Spalte in der Hauptliste leer oder hieß "XP Bereich"
            # Wir suchen daher den Gamertag nochmal in den Ranglisten rechts, da stehen die XP sicher.
            found_user = True
    
    # Fallback / XP Suche in den Ranglisten (ab Spalte K/10)
    # Wir iterieren über alle Zellen. Wenn Zelle == Gamertag, dann ist Zelle rechts davon = XP
    xp_found = 0
    level_found = 1
    
    # Wir wandeln alles in Strings und Lowercase für die Suche
    mask = df_xp_rechner.apply(lambda x: x.astype(str).str.strip().str.lower() == gamertag_input.lower())
    coords = list(zip(*mask.to_numpy().nonzero())) # Findet (row, col) Koordinaten
    
    if coords:
        found_user = True
        # Nimm den ersten Treffer (meistens am aktuellsten oder links)
        r_idx, c_idx = coords[0]
        
        # Versuche Namen zu finden (in der gleichen Zeile ganz links, Spalte D/3)
        # Das ist eine Annahme, dass die Zeilenstruktur konsistent ist
        try:
            potential_name = df_xp_rechner.iloc[r_idx, 3] # Spalte 3 ist "Klasse + Name"
            if str(potential_name) != "nan":
                real_name = potential_name
        except:
            pass # Name schon oben gesetzt hoffentlich
            
        # Versuche XP zu finden (Spalte rechts vom Gamertag)
        try:
            raw_xp = df_xp_rechner.iloc[r_idx, c_idx + 1]
            xp_found = clean_xp_value(raw_xp)
        except:
            xp_found = 0
            
    if found_user:
        st.success(f"Willkommen zurück, **{gamertag_input}**!")
        
        # Level Berechnung
        lvl, prog, gain, need, prog_text = get_level_info(xp_found)
        
        # --- DASHBOARD ---
        col1, col2, col3 = st.columns(3)
        col1.metric("Level", f"{lvl}")
        col2.metric("XP Gesamt", f"{xp_found}")
        col3.metric("Nächstes Level", f"{need} XP nötig")
        
        st.write(f"**Fortschritt:** {prog_text}")
        st.progress(prog)
        
        if lvl >= 16:
            st.balloons()

        # --- QUESTBUCH ANALYSE ---
        st.divider()
        st.subheader("📜 Dein Questbuch")
        
        # Wir müssen den Schüler im Questbuch Blatt finden
        # Zeile 2 (Index 1) sind die Questnamen
        # Zeile 5 (Index 4) sind die Max XP
        # Ab Zeile 7 (Index 6) sind die Schüler
        
        q_header = df_questbuch.iloc[1]
        q_max_xp = df_questbuch.iloc[4]
        
        # Suche nach dem Namen in Spalte A oder B (Index 0 oder 1)
        # Wir suchen "Vorname Nachname" oder Teile davon
        student_row_idx = -1
        
        # Bereinige den Suchnamen
        search_name = str(real_name).lower().replace(",", "").replace("  ", " ")
        name_parts = search_name.split()
        
        # Suche ab Zeile 7
        for idx in range(6, len(df_questbuch)):
            row_str = " ".join([str(x) for x in df_questbuch.iloc[idx, 0:5]]).lower() # Check die ersten paar Spalten
            # Prüfe ob alle Namensteile (z.B. "Antonia", "Brummer") in der Zeile vorkommen
            if all(part in row_str for part in name_parts):
                student_row_idx = idx
                break
        
        if student_row_idx != -1:
            student_data = df_questbuch.iloc[student_row_idx]
            
            quests_open = []
            quests_done = []
            
            # Wir iterieren durch die Spalten.
            # Struktur scheint zu sein: Spalte I = Quest Name, Spalte I = Status, Spalte I+1 = Erhaltene XP
            # Aber im CSV Snippet: Questname steht im Header (Zeile 2).
            # Daten: Status | XP | Status | XP
            
            num_cols = len(q_header)
            # Wir starten ab Spalte 2 (Index 2), da links Namen stehen
            # Wir gehen in 2er Schritten: i (Status), i+1 (XP)
            
            for i in range(2, num_cols - 1, 2):
                q_name = str(q_header[i]).strip()
                
                # Filter ungültige Spalten
                if q_name == "nan" or q_name == "" or "Summe" in q_name:
                    continue
                
                # Daten lesen
                status = str(student_data[i]).strip().upper()
                try:
                    xp_got = clean_xp_value(student_data[i+1])
                except:
                    xp_got = 0
                
                try:
                    xp_max = clean_xp_value(q_max_xp[i+1]) # XP Max steht meist über der XP Spalte
                    if xp_max == 0: xp_max = clean_xp_value(q_max_xp[i]) # Oder über der Status Spalte?
                except:
                    xp_max = 0

                # Status prüfen
                is_finished = False
                if "ABGESCHLOSSEN" in status: is_finished = True
                if xp_got > 0: is_finished = True
                if status == "TRUE": is_finished = True
                
                quest_obj = {
                    "name": q_name,
                    "xp": xp_got if is_finished else xp_max,
                    "status": status
                }
                
                if is_finished:
                    quests_done.append(quest_obj)
                else:
                    quests_open.append(quest_obj)
            
            # --- ANZEIGE TABS ---
            tab1, tab2 = st.tabs([f"Offene Quests ({len(quests_open)})", f"Erledigt ({len(quests_done)})"])
            
            with tab1:
                if not quests_open:
                    st.success("Alles erledigt! Wahnsinn! 🎉")
                else:
                    for q in quests_open:
                        st.warning(f"**{q['name']}**\n\nBelohnung: {q['xp']} XP")
            
            with tab2:
                for q in quests_done:
                    st.success(f"**{q['name']}**\n\n+{q['xp']} XP erhalten")
                    
        else:
            st.warning(f"Konnte keine Quest-Daten für '{real_name}' finden. Bitte prüfe, ob dein Name im Questbuch korrekt steht.")

    else:
        st.error("Gamertag nicht gefunden. Tippfehler?")
        st.caption("Tipp: Achte auf Groß-/Kleinschreibung, auch wenn ich versuche das zu ignorieren.")
