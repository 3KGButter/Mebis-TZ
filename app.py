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

# Tabellenblatt-Namen
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.2 | 25/26")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ---------------------------------------------------------
    # TEIL 1: XP RECHNER LADEN (Dynamische Header-Suche)
    # ---------------------------------------------------------
    try:
        # Wir laden alles ohne Header, um flexibel zu bleiben
        df_xp_raw = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=None, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        # --- HEADER SUCHEN ---
        # Wir suchen die Zeile, in der "Gamertag" in Spalte L (Index 11) vorkommt.
        # Da du sagst, es ist Zeile 2, wird die Schleife dort fündig.
        header_row_index = -1
        
        # Sicherheitshalber suchen wir in den ersten 15 Zeilen
        for i in range(min(15, len(df_xp_raw))):
            row_vals = df_xp_raw.iloc[i].astype(str).values
            # Prüfen ob Spalte L (Index 11) existiert und "Gamertag" enthält
            if len(row_vals) > 11 and "gamertag" in str(row_vals[11]).lower():
                header_row_index = i
                break
        
        if header_row_index == -1:
            st.error("Konnte die Spalte 'Gamertag' (Bereich Rangliste) nicht finden. Bitte prüfen, ob sie in Spalte L steht.")
            st.stop()

        # Datenbereich definieren (Alles nach der Header-Zeile)
        df_xp_data = df_xp_raw.iloc[header_row_index + 1:].reset_index(drop=True)
        
        found_stats = None
        real_name_found = "Unbekannt"
        
        # Suche im Datenbereich
        for idx, row in df_xp_data.iterrows():
            if len(row) > 11:
                # Spalte L (Index 11) ist der Gamertag
                gt_cell = str(row.iloc[11]).strip().lower()
                
                if gt_cell == input_clean:
                    try:
                        # Spalte M (12) = XP, Spalte N (13) = Level
                        raw_xp = row.iloc[12] 
                        raw_level = row.iloc[13] 
                        
                        # Spalte O (14) = Stufe/Info (für Game Over Check)
                        raw_stufe = str(row.iloc[14]) if len(row) > 14 else ""
                        check_str = f"{raw_level} {raw_stufe}".lower()
                        is_game_over = "†" in check_str or "game" in check_str or "over" in check_str or "tot" in check_str

                        # XP Zahl säubern (Tausenderpunkte/Kommas entfernen)
                        try:
                            xp_str = str(raw_xp).replace('.', '').replace(',', '.')
                            xp_val = int(float(xp_str))
                        except:
                            xp_val = 0
                        
                        found_stats = {
                            "xp": xp_val,
                            "level": raw_level,
                            "is_game_over": is_game_over
                        }
                        
                        # Echten Namen aus Spalte D (Index 3) holen ("Klasse + Name")
                        if len(row) > 3:
                            real_name_found = str(row.iloc[3])
                        
                    except Exception as parse_err:
                        st.error(f"Fehler beim Lesen der Datenzeile: {parse_err}")
                    
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
            # TEIL 2: QUESTBUCH LADEN (Matrix-Logik)
            # ---------------------------------------------------------
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Laut CSV Analyse:
            # Zeile 2 (Index 1): Quest Namen (in Spalte D, F, H...)
            quest_names_row = df_quests.iloc[1]
            
            # Schülersuche (Namen in Spalte A und B)
            q_idx = -1
            
            # Name säubern und splitten (z.B. "11T1 Müller Max" -> ["müller", "max"])
            search_parts = real_name_found.lower().replace("11t1", "").replace("11t2", "").split(" ")
            search_tokens = [t for t in search_parts if len(t) > 2]
            if not search_tokens: search_tokens = [real_name_found.lower()]

            # Suche ab Zeile 5, wo die Schüler beginnen
            start_search_row = 5 
            
            for idx in range(start_search_row, len(df_quests)):
                row = df_quests.iloc[idx]
                # Spalte A (Nachname) + Spalte B (Vorname)
                full_name_str = f"{str(row.iloc[0])} {str(row.iloc[1])}".lower()
                
                match = True
                for token in search_tokens:
                    if token not in full_name_str:
                        match = False
                        break
                if match:
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
                
                # --- WICHTIG: ITERATION DURCH SPALTEN ---
                # Die Quests beginnen ab Spalte D (Index 3).
                # Muster: [QuestName/Status] [XP-Wert] [QuestName/Status] [XP-Wert] ...
                # Wir springen also immer in 2er Schritten: 3, 5, 7, 9...
                
                max_col = df_quests.shape[1]
                
                for c in range(3, max_col - 1, 2):
                    try:
                        # 1. Name der Quest aus der Header-Zeile (Zeile 2 / Index 1)
                        q_name = str(quest_names_row.iloc[c])
                        
                        if q_name == "nan" or not q_name.strip(): 
                            continue
                        
                        # Filter
                        q_check = q_name.lower()
                        if "summe" in q_check or "game" in q_check or "total" in q_check:
                            continue

                        # 2. Status aus der Schüler-Zeile (Gleiche Spalte wie Name)
                        status_val = str(student_row.iloc[c]).strip().lower()
                        
                        # 3. XP aus der Schüler-Zeile (Spalte RECHTS daneben)
                        xp_val_raw = student_row.iloc[c + 1]
                        
                        try:
                            # Versuch, XP aus der Nachbarspalte zu lesen
                            xp_val = int(float(str(xp_val_raw).replace(',', '.')))
                        except:
                            # Falls dort nichts steht, suchen wir in Zeile 5 (Master XP Zeile)
                            # (Falls es die noch gibt, zur Sicherheit)
                            try:
                                xp_val = int(float(str(df_quests.iloc[4, c+1]).replace(',', '.')))
                            except:
                                xp_val = "?"

                        # Logik: Abgeschlossen?
                        is_completed = "abgeschlossen" in status_val and "nicht" not in status_val
                        
                        # Alternativ: Wenn XP > 0 eingetragen sind, gilt es auch als abgeschlossen
                        if isinstance(xp_val, int) and xp_val > 0 and xp_val != "?":
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
                        st.info("Noch keine Quests abgeschlossen.")
                    else:
                        st.info("Keine offenen Quests in dieser Ansicht.")

            else:
                st.warning(f"Konnte Quest-Daten für '{real_name_found}' nicht finden.")
                st.caption(f"Gesucht nach Teilen von: {search_parts}")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")
            st.info("Bitte prüfe, ob dein Gamertag im Blatt 'XP Rechner 3.0' in Spalte L steht.")
    
except Exception as e:
    st.error(f"Ein Systemfehler ist aufgetreten: {e}")


