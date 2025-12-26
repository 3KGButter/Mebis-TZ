import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="📐", layout="centered")
st.title("🛡️ Questlog & XP Tracker")

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

# Die Namen deiner Tabellenblätter (laut CSV)
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.4 | Fix für Spaltenindex L=11")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ---------------------------------------------------------
    # TEIL 1: XP RECHNER LADEN
    # ---------------------------------------------------------
    try:
        # header=None: Wir laden ALLES und greifen hart per Index zu.
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=None, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        found_stats = None
        real_name_found = "Unbekannt"
        
        # --- KORRIGIERTE SPALTEN-INDIZES (0-basiert) ---
        # Laut deiner CSV "XP Rechner 3.0.csv":
        # Spalte L (Index 11) = Gamertag (Rangliste)
        # Spalte M (Index 12) = XP
        # Spalte N (Index 13) = Level
        # Spalte O (Index 14) = Stufe / Info
        # Spalte D (Index 3)  = Echter Name (Klasse + Name)
        
        col_idx_gamertag = 11
        col_idx_xp = 12
        col_idx_level = 13
        col_idx_stufe = 14
        col_idx_realname = 3

        # Wir suchen ab Zeile 3 (Index 2), da vorher Header sind
        start_row = 2 

        for idx, row in df_xp.iloc[start_row:].iterrows():
            if len(row) > col_idx_stufe:
                # Gamertag prüfen (Spalte L / 11)
                gt_cell = str(row.iloc[col_idx_gamertag]).strip().lower()
                
                if gt_cell == input_clean:
                    # GEFUNDEN!
                    try:
                        raw_xp = row.iloc[col_idx_xp]
                        raw_level = row.iloc[col_idx_level]
                        
                        # Game Over Check
                        raw_stufe = str(row.iloc[col_idx_stufe])
                        check_str = f"{raw_level} {raw_stufe}".lower()
                        is_game_over = "†" in check_str or "game" in check_str or "over" in check_str or "tot" in check_str

                        # XP Zahl säubern
                        try:
                            # Entferne Tausenderpunkte, ersetze Komma durch Punkt
                            xp_str = str(raw_xp).replace('.', '').replace(',', '.')
                            xp_val = int(float(xp_str))
                        except:
                            xp_val = 0
                        
                        found_stats = {
                            "xp": xp_val,
                            "level": raw_level,
                            "is_game_over": is_game_over
                        }
                        
                        # Echten Namen merken (fürs Questbuch)
                        real_name_found = str(row.iloc[col_idx_realname])
                        
                    except Exception as e:
                        st.error(f"Lesefehler in Zeile {idx}: {e}")
                    
                    break
        
        if found_stats:
            # --- ANZEIGE OBEN ---
            if not found_stats["is_game_over"]:
                st.balloons()
                st.success(f"Willkommen zurück, **{gamertag_input}**!")
            
            c1, c2 = st.columns(2)
            c1.metric("Level", str(found_stats["level"]))
            c2.metric("XP Total", found_stats["xp"])
            
            if found_stats["is_game_over"]:
                 st.markdown("""
                <div style="background-color: #ff4b4b; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
                    <h1 style="color: white; font-size: 80px; margin: 0;">💀</h1>
                    <h2 style="color: white; margin: 0; font-weight: bold;">GAME OVER</h2>
                </div>
                """, unsafe_allow_html=True)
            else:
                prog_val, prog_text = calculate_progress(found_stats["xp"])
                st.progress(prog_val, text=prog_text)

            # ---------------------------------------------------------
            # TEIL 2: QUESTBUCH LADEN
            # ---------------------------------------------------------
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Laut CSV "Questbuch 4.0":
            # Zeile 2 (Index 1): Quest-Namen (Grundregeln etc.)
            quest_names_row = df_quests.iloc[1]
            
            # Schülersuche
            q_idx = -1
            
            # Name aufbereiten (Klasse entfernen)
            # z.B. "11T1 Antonia Brummer" -> ["antonia", "brummer"]
            search_parts = real_name_found.lower().replace("11t1", "").replace("11t2", "").replace("11t3", "").replace("11t4", "").split(" ")
            search_tokens = [t for t in search_parts if len(t) > 2]
            if not search_tokens: search_tokens = [real_name_found.lower()]

            # Suche im Questbuch ab Zeile 5 (wo die Schüler stehen)
            for idx in range(2, len(df_quests)):
                row = df_quests.iloc[idx]
                
                # Name steht in Spalte B (Index 1) laut CSV
                name_cell = str(row.iloc[1]).lower()
                
                # Manchmal auch Spalte A? Wir checken beides sicherheitshalber
                name_cell_full = f"{str(row.iloc[0])} {name_cell}".lower()
                
                match = True
                for token in search_tokens:
                    if token not in name_cell_full:
                        match = False
                        break
                
                if match and len(name_cell) > 2: # Name muss min. 2 Zeichen haben
                    q_idx = idx
                    break
            
            if q_idx != -1:
                student_row = df_quests.iloc[q_idx]
                
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
                
                # --- QUEST LOGIK ---
                # Quests starten ab Spalte D (Index 3).
                # Muster: [D: Name/Status] [E: XP] [F: Name/Status] [G: XP] ...
                # Schrittweite 2: 3, 5, 7, 9...
                
                max_col = min(len(quest_names_row), len(student_row))
                
                for c in range(3, max_col - 1, 2):
                    try:
                        # 1. Quest Name aus Header Zeile 2 (Index 1)
                        q_name = str(quest_names_row.iloc[c])
                        
                        if q_name == "nan" or not q_name.strip(): 
                            continue
                        
                        # Filter
                        q_check = q_name.lower()
                        if "summe" in q_check or "game" in q_check or "total" in q_check:
                            continue

                        # 2. Status aus Schüler-Zeile (Spalte c)
                        status_val = str(student_row.iloc[c]).strip().lower()
                        
                        # 3. XP aus Schüler-Zeile (Spalte c+1 -> rechts daneben)
                        xp_val_raw = student_row.iloc[c + 1]
                        
                        try:
                            xp_val = int(float(str(xp_val_raw).replace(',', '.')))
                        except:
                            xp_val = "?"

                        # Logik: Abgeschlossen?
                        is_completed = "abgeschlossen" in status_val and "nicht" not in status_val
                        
                        # Zusatzregel: Wenn Punkte eingetragen sind (>0), ist es auch fertig
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
                    st.info("Keine Einträge in dieser Ansicht.")

            else:
                st.warning(f"Konnte Quest-Daten für '{real_name_found}' nicht finden.")
                # Debug Info falls Suche fehlschlägt
                st.caption(f"Gesucht nach Tokens: {search_tokens}")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")
            st.info("Tipp: Der Gamertag muss im Blatt 'XP Rechner 3.0' in Spalte L (Rangliste) stehen.")
    
except Exception as e:
    st.error(f"Ein Systemfehler ist aufgetreten: {e}")


