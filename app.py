import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="📐", layout="wide")
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
    
    if xp_needed_for_level <= 0: return 1.0, "Level Up!"
    
    progress_percent = xp_gained_in_level / xp_needed_for_level
    progress_percent = max(0.0, min(1.0, progress_percent))
    
    text = f"{int(xp_gained_in_level)} / {int(xp_needed_for_level)} XP zum nächsten Level"
    return progress_percent, text

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

# --- SIDEBAR ---
with st.sidebar:
    st.header("Einstellungen")
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    
    st.write("---")
    debug_mode = st.checkbox("🔧 Diagnose-Modus", value=False)
    if debug_mode:
        st.info("Der Diagnose-Modus zeigt dir genau, wo die App sucht.")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        # ttl=0 holt immer frische Daten
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    if debug_mode:
        st.write(f"📊 Tabelle geladen: {len(df_xp)} Zeilen, {len(df_xp.columns)} Spalten.")
        st.write("Vorschau der Rohdaten (erste 5 Zeilen):")
        st.dataframe(df_xp.head())

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        # --- PHASE 1: ECHTEN NAMEN FINDEN (LINKS < SPALTE 11) ---
        real_name_found = None
        
        # Wir suchen in den ersten 11 Spalten
        # Wir suchen die Spalte "Gamertag " (mit Leerzeichen am Ende, wie in Excel oft üblich)
        col_idx_gamertag_left = -1
        col_idx_name_left = -1
        
        for i in range(min(11, len(df_xp.columns))):
            col_header = str(df_xp.columns[i])
            if "Gamertag" in col_header:
                col_idx_gamertag_left = i
            if "Klasse + Name" in col_header:
                col_idx_name_left = i
        
        if col_idx_gamertag_left != -1 and col_idx_name_left != -1:
            for idx, row in df_xp.iterrows():
                val = str(row.iloc[col_idx_gamertag_left]).strip()
                if val.lower() == input_clean:
                    real_name_found = row.iloc[col_idx_name_left]
                    break
        
        if not real_name_found:
            st.error(f"Gamertag '{gamertag_input}' nicht in den Stammdaten (linker Bereich) gefunden.")
            if debug_mode:
                st.warning(f"Habe in Spalte {col_idx_gamertag_left} gesucht.")
            st.stop()

        # --- PHASE 2: TIEFENSUCHE (DEEP SEARCH) AB SPALTE 24 ---
        # Wir ignorieren Spaltennamen und suchen den Text einfach überall ab Spalte Y.
        best_stats = None
        found_locations = []

        start_scan_idx = 24 # Spalte Y
        
        # Gehe JEDE Spalte durch
        for col_idx in range(start_scan_idx, len(df_xp.columns)):
            
            # Hole die ganze Spalte als Text
            # (astype(str) verhindert Abstürze bei Zahlen)
            column_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
            
            # Gibt es hier unseren Gamertag?
            matches = column_data[column_data == input_clean].index
            
            for row_idx in matches:
                # TREFFER!
                # Wir gehen davon aus: 
                # Spalte -1 = Rang
                # Spalte +0 = Gamertag (Hier sind wir)
                # Spalte +1 = XP
                # Spalte +2 = Level
                # Spalte +3 = Stufe (Game Over Info)
                
                try:
                    row = df_xp.iloc[row_idx]
                    
                    # XP lesen (Rechts +1)
                    if col_idx + 1 < len(df_xp.columns):
                        raw_xp = row.iloc[col_idx + 1]
                    else:
                        raw_xp = 0
                        
                    # Level lesen (Rechts +2)
                    if col_idx + 2 < len(df_xp.columns):
                        raw_level = row.iloc[col_idx + 2]
                    else:
                        raw_level = 0
                        
                    # Rang lesen (Links -1)
                    if col_idx > 0:
                        raw_rang = row.iloc[col_idx - 1]
                    else:
                        raw_rang = "?"
                    
                    # Stufe lesen (Rechts +3) für Game Over
                    if col_idx + 3 < len(df_xp.columns):
                        raw_stufe = str(row.iloc[col_idx + 3])
                    else:
                        raw_stufe = ""

                    # Daten aufbereiten
                    check_string = f"{raw_level} {raw_stufe}".lower()
                    is_game_over = "†" in check_string or "game" in check_string or "over" in check_string
                    
                    try:
                        current_xp = int(raw_xp)
                    except:
                        current_xp = 0

                    match_data = {
                        "xp": current_xp,
                        "raw_level": raw_level,
                        "raw_rang": raw_rang,
                        "is_game_over": is_game_over,
                        "debug_loc": f"Z{row_idx}/S{col_idx}"
                    }
                    
                    found_locations.append(match_data)

                except Exception as e:
                    if debug_mode:
                        st.warning(f"Fehler beim Lesen bei Z{row_idx}/S{col_idx}: {e}")
                    continue

        # Auswertung der Treffer
        for cand in found_locations:
            if best_stats is None:
                best_stats = cand
            else:
                # Logik: Nimm den mit mehr XP, außer er ist Game Over und hat 0
                if cand["xp"] > best_stats["xp"]:
                    best_stats = cand
                elif cand["xp"] == 0 and cand["is_game_over"]:
                    best_stats = cand

        # Debug Ausgabe
        if debug_mode:
            st.write(f"🔍 Gefundene Einträge für '{input_clean}':")
            for loc in found_locations:
                st.json(loc)

        if best_stats:
            # Werte formatieren
            raw_lvl = best_stats["raw_level"]
            display_level = str(raw_lvl)
            try:
                display_level = str(int(float(raw_lvl)))
            except:
                pass 

            xp_num = best_stats["xp"]
            
            # Rang formatieren
            display_rang = str(best_stats["raw_rang"])
            if display_rang.replace('.','',1).isdigit():
                 display_rang = f"#{int(float(display_rang))}"

            # --- ANZEIGE ---
            if not best_stats["is_game_over"]:
                st.balloons()
            
            st.success(f"Willkommen zurück, **{gamertag_input}**!") 
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Klassen-Rang", display_rang)
            col2.metric("Level", display_level)
            col3.metric("XP Total", xp_num)
            
            if not best_stats["is_game_over"]:
                prog_val, prog_text = calculate_progress(xp_num)
                st.progress(prog_val, text=prog_text)
            else:
                st.error("💀 GAME OVER - Bitte beim Lehrer melden!")

            # --- QUESTS LADEN ---
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Konnte Quests nicht laden.")
                st.stop()

            quest_names = df_quests.iloc[1] 
            quest_xps = df_quests.iloc[4]

            quest_row_index = -1
            search_name = str(real_name_found).strip().lower()
            
            # Questbuch Suche
            for idx, row in df_quests.iterrows():
                row_str = " ".join([str(x) for x in row.values[:4]]).lower()
                if search_name in row_str:
                    quest_row_index = idx
                    break
            
            if quest_row_index != -1:
                student_quest_row = df_quests.iloc[quest_row_index]
                
                st.divider()
                st.subheader("Deine Quests")
                
                tab1, tab2 = st.tabs(["✅ Erledigt", "❌ Offen"])
                
                erledigt_cols = tab1.columns(3)
                erledigt_count = 0
                offen_cols = tab2.columns(3)
                offen_count = 0
                found_quests_any = False
                
                for c in range(3, df_quests.shape[1]):
                    try:
                        q_name = str(quest_names.iloc[c])
                        if q_name == "nan" or q_name.strip() == "":
                            continue
                            
                        val = str(student_quest_row.iloc[c])
                        
                        try:
                            xp_val = int(float(str(quest_xps.iloc[c])))
                        except:
                            xp_val = "?"

                        if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                            found_quests_any = True
                            with erledigt_cols[erledigt_count % 3]:
                                st.success(f"**{q_name}**\n\n+{xp_val} XP")
                            erledigt_count += 1
                        else:
                            with offen_cols[offen_count % 3]:
                                st.markdown(f"""
                                <div style="border:1px solid #ccc; padding:10px; border-radius:5px; opacity: 0.6;">
                                    <strong>{q_name}</strong><br>
                                    🔒 {xp_val} XP
                                </div>
                                """, unsafe_allow_html=True)
                            offen_count += 1
                    except:
                        continue
                
                if not found_quests_any:
                    if best_stats["is_game_over"]:
                        tab1.markdown("""
                        <div style="text-align: center; margin-top: 20px;">
                            <h1 style="font-size: 80px;">💀</h1>
                            <h2 style="color: red; font-weight: bold;">GAME OVER</h2>
                            <p style="font-size: 18px;">Keine Quests abgeschlossen.</p>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        tab1.info("Noch keine Quests abgeschlossen. Leg los!")
            else:
                st.warning(f"Konnte Quest-Log für '{real_name_found}' nicht synchronisieren.")

        else:
            st.error(f"Gamertag '{gamertag_input}' im Bereich ab Spalte Y nicht gefunden.")
            if debug_mode:
                st.write("Tipp: Prüfe im Excel-File, ob der Gamertag wirklich rechts ab Spalte Y (Index 24) steht.")

except Exception as e:
    st.error(f"Ein technischer Fehler ist aufgetreten: {str(e)}")


