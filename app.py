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
    
    if xp_needed_for_level <= 0: return 1.0, "Level Up!"
    
    progress_percent = xp_gained_in_level / xp_needed_for_level
    progress_percent = max(0.0, min(1.0, progress_percent))
    
    text = f"{int(xp_gained_in_level)} / {int(xp_needed_for_level)} XP zum nächsten Level"
    return progress_percent, text

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
# Namen an deine neue Excel angepasst
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

# Button zum Neuladen
with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    try:
        # ttl=0 für Live-Daten
        # header=1 passt für XP Rechner (Zeile 2 sind Überschriften)
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        # --- SCHRITT 1: GAMERTAG SUCHEN (RECHTS: RANGO & XP) ---
        # Wir suchen in Spalte L (Index 11) nach dem Gamertag für die Punkte
        found_stats_row = -1
        best_stats = None
        
        # Spalte L ist Index 11 in Python (0-basiert), Excel Spalte 12
        target_col_idx = 11 
        
        # Sicherstellen, dass die Spalte existiert
        if len(df_xp.columns) > target_col_idx:
            # Spalte als String holen und säubern
            col_data = df_xp.iloc[:, target_col_idx].astype(str).str.strip().str.lower()
            matches = col_data[col_data == input_clean].index
            
            if not matches.empty:
                found_stats_row = matches[0]
                row = df_xp.iloc[found_stats_row]
                
                # Daten auslesen (Spalte M=XP, N=Level, O=Stufe)
                # Indizes relativ zur ganzen Tabelle: L=11, M=12, N=13, O=14
                try:
                    raw_xp = row.iloc[12] # Spalte M
                    raw_level = row.iloc[13] # Spalte N
                    raw_stufe = str(row.iloc[14]) if len(row) > 14 else ""
                    
                    check_str = f"{raw_level} {raw_stufe}".lower()
                    is_game_over = "†" in check_str or "game" in check_str or "over" in check_str or "tot" in check_str
                    
                    xp_val = int(float(str(raw_xp).replace('.', '').replace(',', '.')))
                except:
                    xp_val = 0
                    raw_level = 0
                    is_game_over = False
                        
                best_stats = {
                    "xp": xp_val,
                    "level": raw_level,
                    "is_game_over": is_game_over
                }

        # --- SCHRITT 2: ECHTEN NAMEN HOLEN (LINKS: STAMMDATEN) ---
        # WICHTIG: Die linke Liste ist nicht gleich sortiert wie die rechte!
        # Wir suchen den Gamertag nochmal in Spalte E (Index 4), um den Namen aus Spalte D (Index 3) zu holen.
        
        real_name_found = "Unbekannt"
        if best_stats:
            try:
                # Suche in Spalte E (Index 4)
                col_tags_left = df_xp.iloc[:, 4].astype(str).str.strip().str.lower()
                matches_left = col_tags_left[col_tags_left == input_clean].index
                
                if not matches_left.empty:
                    # Name aus Spalte D (Index 3)
                    real_name_found = str(df_xp.iloc[matches_left[0], 3])
                else:
                    st.warning("Gamertag rechts gefunden, aber nicht in der linken Namensliste.")
            except:
                pass

        if best_stats:
            # --- ANZEIGE ---
            display_level = str(best_stats["level"])
            try:
                display_level = str(int(float(display_level)))
            except:
                pass 
                
            xp_num = best_stats["xp"]
            is_go = best_stats["is_game_over"]

            if not is_go:
                st.balloons()
                st.success(f"Willkommen zurück, Abenteurer **{gamertag_input}**!")
            
            c1, c2 = st.columns(2)
            c1.metric("Level", display_level)
            c2.metric("XP Total", xp_num)
            
            if not is_go:
                prog_val, prog_text = calculate_progress(xp_num)
                st.progress(prog_val, text=prog_text)
            else:
                st.markdown("""
                <div style="background-color: #ff4b4b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: white; font-size: 80px; margin: 0;">💀</h1>
                    <h2 style="color: white; margin: 0; font-weight: bold;">GAME OVER</h2>
                </div>
                """, unsafe_allow_html=True)

            # --- SCHRITT 3: QUESTS LADEN ---
            try:
                # header=None ist wichtig für die Struktur-Analyse
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Questnamen stehen in Zeile 2 (Index 1)
            quest_names = df_quests.iloc[1] 
            
            # Wir suchen den Schüler
            q_idx = -1
            # Bereinigung des Namens (z.B. "11T1 " entfernen für Vergleich)
            search_name_clean = real_name_found.strip().lower()
            # Teile Name auf (z.B. "Antonia Brummer" -> ["antonia", "brummer"])
            search_tokens = [t for t in search_name_clean.split(" ") if len(t) > 2] # Nur Teile > 2 Zeichen
            
            # Fallback falls Name sehr kurz
            if not search_tokens: search_tokens = [search_name_clean]

            # Wir suchen ab Zeile 3 nach dem Schüler
            for idx in range(2, len(df_quests)):
                row = df_quests.iloc[idx]
                # In Spalte B (Index 1) steht meist der Name
                row_txt = str(row.iloc[1]).lower() + " " + str(row.iloc[0]).lower()
                
                match_all = True
                for token in search_tokens:
                    if token not in row_txt:
                        match_all = False
                        break
                
                if match_all:
                    q_idx = idx
                    break
            
            if q_idx != -1:
                student_quest_row = df_quests.iloc[q_idx]
                
                st.divider()
                
                c_switch, c_text = st.columns([1, 4])
                with c_switch:
                    show_done = st.toggle("Erledigte anzeigen", value=False)
                
                if show_done:
                    st.subheader("✅ Erledigte Quests")
                else:
                    st.subheader("❌ Offene Quests")

                cols = st.columns(3)
                cnt = 0
                found_any = False
                
                # --- QUEST SCHLEIFE ANGEPASST ---
                # Struktur ist: Name (Spalte i) | XP (Spalte i+1)
                # Wir springen in 2er Schritten: 3, 5, 7, 9...
                
                max_cols = min(len(quest_names), len(student_quest_row))
                
                for c in range(3, max_cols - 1, 2):
                    try:
                        q_name = str(quest_names.iloc[c])
                        
                        if q_name == "nan" or not q_name.strip(): continue
                        
                        q_check = q_name.lower()
                        if "summe" in q_check or "game" in q_check or "over" in q_check or "total" in q_check:
                            continue
                        
                        # Status aus aktueller Spalte
                        val_status = str(student_quest_row.iloc[c]).lower()
                        
                        # XP aus NÄCHSTER Spalte (c+1)
                        val_xp_raw = student_quest_row.iloc[c+1]
                        
                        try:
                            xp_val = int(float(str(val_xp_raw).replace(',', '.')))
                        except:
                            xp_val = "?"
                        
                        # Ist es fertig?
                        # 1. Wenn "abgeschlossen" im Text
                        is_completed = "abgeschlossen" in val_status and "nicht" not in val_status
                        
                        # 2. ODER: Wenn Punkte eingetragen sind (>0)
                        if isinstance(xp_val, int) and xp_val > 0:
                            is_completed = True

                        if show_done:
                            if is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.success(f"**{q_name}**\n\n+{xp_val} XP")
                                cnt += 1
                        else:
                            if not is_completed:
                                found_any = True
                                with cols[cnt % 3]:
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                        <strong>{q_name}</strong><br>🔒 {xp_val} XP
                                    </div>
                                    """, unsafe_allow_html=True)
                                cnt += 1
                    except:
                        continue
                        
                if not found_any:
                    if show_done:
                        st.info("Noch keine Quests erledigt.")
                    else:
                        if is_go:
                            st.markdown("""
                            <div style="text-align: center; margin-top: 20px;">
                                <h1 style="font-size: 80px;">💀</h1>
                                <h2 style="color: red;">GAME OVER</h2>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.balloons()
                            st.success("Alles erledigt! Du bist auf dem neuesten Stand.")

            else:
                st.warning(f"Konnte Quests für '{real_name_found}' nicht laden.")
                st.caption(f"Gesucht nach: {search_tokens} in Spalte B.")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht in der Rangliste gefunden.")
            st.info("Hinweis: Der Gamertag muss im Blatt 'XP Rechner 3.0' in Spalte L (Rangliste) stehen.")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")

