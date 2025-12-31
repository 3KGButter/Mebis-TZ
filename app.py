import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- KONFIGURATION ---
st.set_page_config(page_title="Questlog", page_icon="🛡️", layout="centered")

# Google Sheets URL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
SHEET_XP_RECHNER = "XP Rechner 3.0"
SHEET_QUESTBUCH = "Questbuch 4.0"

# Level-Schwellenwerte
LEVEL_THRESHOLDS = {
    1: 0, 2: 42, 3: 143, 4: 332, 5: 640, 6: 1096, 7: 1728, 8: 2567,
    9: 3640, 10: 4976, 11: 6602, 12: 8545, 13: 10831, 14: 13486, 15: 16536, 16: 20003
}

# --- HILFSFUNKTIONEN ---
def calculate_level_progress(xp):
    """Berechnet aktuelles Level und Fortschritt zum nächsten Level."""
    current_level = 1
    for level, threshold in LEVEL_THRESHOLDS.items():
        if xp >= threshold:
            current_level = level
    
    if current_level >= 16:
        return current_level, 1.0, "Max Level erreicht! 🏆"
    
    current_threshold = LEVEL_THRESHOLDS[current_level]
    next_threshold = LEVEL_THRESHOLDS[current_level + 1]
    xp_in_level = xp - current_threshold
    xp_needed = next_threshold - current_threshold
    progress = xp_in_level / xp_needed
    
    return current_level, progress, f"{xp_in_level} / {xp_needed} XP"

def safe_int(value, default=0):
    """Konvertiert sicher zu Integer."""
    if pd.isna(value):
        return default
    try:
        return int(float(str(value).replace(',', '.')))
    except:
        return default

def is_quest_completed(value):
    """Prüft ob Quest abgeschlossen ist (Checkbox, Text, oder Punkte > 0)."""
    if pd.isna(value):
        return False
    if isinstance(value, (int, float)) and value > 0:
        return True
    if isinstance(value, bool):
        return value
    value_str = str(value).upper().strip()
    return value_str in ["TRUE", "WAHR", "1", "CHECKED", "ABGESCHLOSSEN", "✓"]

# --- HAUPTAPP ---
st.title("🛡️ Questlog")

# Sidebar
with st.sidebar:
    st.caption("v4.0 - Clean Edition")
    if st.button("🔄 Aktualisieren", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    # Google Sheets Verbindung
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # --- SCHRITT 1: GAMERTAG EINGABE ---
    st.info("👤 Bitte gib deinen Gamertag ein:")
    gamertag_input = st.text_input("Gamertag:", placeholder="z.B. BrAnt")
    
    if not gamertag_input:
        st.stop()
    
    gamertag = gamertag_input.strip().lower()
    
    # --- SCHRITT 2: XP RECHNER LADEN ---
    with st.spinner("Lade Spielerdaten..."):
        df_xp = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=SHEET_XP_RECHNER, ttl=0)
    
    # Suche Gamertag in Spalte D (Index 3)
    df_xp['Gamertag_Lower'] = df_xp.iloc[:, 3].astype(str).str.strip().str.lower()
    player_data = df_xp[df_xp['Gamertag_Lower'] == gamertag]
    
    if player_data.empty:
        st.error(f"❌ Gamertag '{gamertag_input}' nicht gefunden!")
        st.info("💡 Tipp: Achte auf die richtige Schreibweise (z.B. BrAnt, JuBur)")
        st.stop()
    
    # Spielerdaten extrahieren
    player_row = player_data.iloc[0]
    player_name = str(player_row.iloc[2])  # Spalte C = Name
    player_xp = safe_int(player_row.iloc[4])  # Spalte E = XP
    player_level_raw = player_row.iloc[5]  # Spalte F = Level
    player_stufe = str(player_row.iloc[6])  # Spalte G = Stufe
    
    # Game Over Check
    is_game_over = "💀" in str(player_level_raw) or "game over" in player_stufe.lower()
    
    # Level anzeigen
    if is_game_over:
        st.error("💀 GAME OVER")
        st.stop()
    
    # Erfolgreicher Login
    st.success(f"Willkommen, **{gamertag_input}**! ({player_name})")
    
    # XP & Level Anzeige
    level, progress, progress_text = calculate_level_progress(player_xp)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Level", level)
    with col2:
        st.metric("XP", player_xp)
    with col3:
        st.metric("Stufe", player_stufe)
    
    st.progress(progress, text=progress_text)
    
    # --- SCHRITT 3: QUESTBUCH LADEN ---
    st.divider()
    
    with st.spinner("Lade Quests..."):
        df_quests = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=SHEET_QUESTBUCH, ttl=0)
    
    # Quest-Namen (Zeile 2 = Index 1)
    quest_names = df_quests.iloc[1, 2:].tolist()  # Ab Spalte C
    # XP-Werte (Zeile 5 = Index 4)
    quest_xp_values = df_quests.iloc[4, 2:].tolist()  # Ab Spalte C
    
    # Suche Schüler im Questbuch (ab Zeile 7 = Index 6)
    name_parts = [part for part in player_name.lower().split() if len(part) > 2]
    student_row_idx = None
    
    for idx in range(6, len(df_quests)):
        row_text = " ".join([str(x) for x in df_quests.iloc[idx, 0:4]]).lower()
        if all(part in row_text for part in name_parts):
            student_row_idx = idx
            break
    
    if student_row_idx is None:
        st.warning(f"⚠️ Keine Quest-Daten für '{player_name}' gefunden.")
        st.stop()
    
    student_quest_row = df_quests.iloc[student_row_idx, 2:].tolist()  # Ab Spalte C
    
    # --- SCHRITT 4: QUESTS ANZEIGEN ---
    show_completed = st.toggle("✅ Erledigte Quests anzeigen", value=True)
    
    if show_completed:
        st.subheader("✅ Erledigte Quests")
    else:
        st.subheader("🔒 Offene Quests")
    
    # Quests filtern und anzeigen
    completed_quests = []
    open_quests = []
    
    for i, (quest_name, master_xp) in enumerate(zip(quest_names, quest_xp_values)):
        # Filter leere/ungültige Quests
        if pd.isna(quest_name) or str(quest_name).strip() == "":
            continue
        
        quest_name_clean = str(quest_name).strip()
        
        # Stopp-Bedingungen
        if any(word in quest_name_clean.lower() for word in ["cp", "gesamtsumme", "game-over"]):
            break
        
        # Überspringe System-Spalten
        if quest_name_clean.lower() in ["quest", "kachel", "code"]:
            continue
        
        # Hole Student-Daten
        if i < len(student_quest_row):
            student_value = student_quest_row[i]
            is_completed = is_quest_completed(student_value)
            earned_xp = safe_int(student_value)
            
            # XP Logik
            display_xp = earned_xp if earned_xp > 0 else safe_int(master_xp)
            
            quest_data = {
                "name": quest_name_clean,
                "xp": display_xp,
                "completed": is_completed
            }
            
            if is_completed:
                completed_quests.append(quest_data)
            else:
                open_quests.append(quest_data)
    
    # Ausgabe
    quests_to_show = completed_quests if show_completed else open_quests
    
    if not quests_to_show:
        if show_completed:
            st.info("Noch keine Quests abgeschlossen.")
        else:
            st.success("🎉 Alle Quests abgeschlossen!")
    else:
        cols = st.columns(3)
        for idx, quest in enumerate(quests_to_show):
            with cols[idx % 3]:
                if quest["completed"]:
                    st.success(f"**{quest['name']}**\n\n✨ +{quest['xp']} XP")
                else:
                    st.markdown(f"""
                    <div style="border:2px solid #444; padding:15px; border-radius:10px; 
                                background-color:#1a1a1a; opacity:0.7;">
                        <strong>{quest['name']}</strong><br>
                        🔒 {quest['xp']} XP
                    </div>
                    """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Fehler beim Laden der Daten: {e}")
    st.info("💡 Bitte Verbindung prüfen oder Admin kontaktieren.")
