import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="📐")
st.title("Questlog")

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
    if xp_needed_for_level <= 0:
        return 1.0, "Level Up!"
    progress_percent = xp_gained_in_level / xp_needed_for_level
    progress_percent = max(0.0, min(1.0, progress_percent))
    text = f"{int(xp_gained_in_level)} / {int(xp_needed_for_level)} XP zum nächsten Level"
    return progress_percent, text

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

# Button zum Neuladen
with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
except Exception as e:
    st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
    st.stop()

st.info("Logge dich ein, um deinen Status zu sehen.")
gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

if gamertag_input:
    input_clean = gamertag_input.strip().lower()

    # --- SCHRITT 1: GAMERTAG SUCHEN (NUR BEREICH L bis P) ---
    found_row_index = -1
    best_stats = None

    target_col_start = 11
    target_col_end = min(17, len(df_xp.columns))

    for col_idx in range(target_col_start, target_col_end):
        col_header = str(df_xp.columns[col_idx]).strip()
        if "Gamertag" in col_header:
            col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
            matches = col_data[col_data == input_clean].index
            if not matches.empty:
                found_row_index = matches[0]
                row = df_xp.iloc[found_row_index]
                if col_idx + 2 < len(df_xp.columns):
                    raw_xp = row.iloc[col_idx + 1]
                    raw_level = row.iloc[col_idx + 2]
                    raw_stufe = ""
                    if col_idx + 3 < len(df_xp.columns):
                        raw_stufe = str(row.iloc[col_idx + 3])
                    check_str = f"{raw_level} {raw_stufe}".lower()
                    is_game_over = "†" in check_str or "game" in check_str or "over" in check_str
                    try:
                        xp_val = int(float(str(raw_xp).replace(',', '.')))
                    except:
                        xp_val = 0
                    best_stats = {
                        "xp": xp_val,
                        "level": raw_level,
                        "is_game_over": is_game_over
                    }
                break

    if best_stats and found_row_index
