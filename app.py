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

# Basierend auf deinen CSVs:
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.3 | Fix für XP Rechner 3.0")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ---------------------------------------------------------
    # TEIL 1: XP RECHNER LADEN
    # ---------------------------------------------------------
    try:
        # header=1 bedeutet, Zeile 2 ist der Header (Python Index 1)
        # Das entspricht deiner CSV Struktur (Vorname, Nachname...)
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        found_stats = None
        real_name_found = "Unbekannt"
        
        # --- FIX: HARDCODED SPALTEN FÜR XP RECHNER 3.0 ---
        # Basierend auf deiner CSV Analyse:
        # Spalte M (Index 12): Gamertag (Rangliste)
        # Spalte N (Index 13): XP
        # Spalte O (Index 14): Level
        # Spalte P (Index 15): Stufe
        # Spalte D (Index 3):  Echter Name (Klasse + Name)
        
        col_idx_gamertag = 12
        col_idx_xp = 13
        col_idx_level = 14
        col_idx_stufe = 15
        col_idx_realname = 3

        # Wir iterieren durch die Zeilen
        for idx, row in df_xp.iterrows():
            # Sicherheitscheck: Hat die Zeile genug Spalten?
            if len(row) > col_idx_level:
                # Gamertag aus Spalte M prüfen
                gt_cell = str(row.iloc[col_idx_gamertag]).strip().lower()
                
                if gt_cell == input_clean:
                    # GEFUNDEN!
                    try:
                        raw_xp = row.iloc[col_idx_xp]
                        raw_level = row.iloc[col_idx_level]
                        
                        # Game Over Check
                        raw_stufe = str(row.iloc[col_idx_stufe]) if len(row) > col_idx_stufe else ""
                        check_str = f"{raw_level} {raw_stufe}".lower()
                        is_game_over = "†" in check_str or "game" in check_str or "over" in check_str or "tot" in check_str

                        # XP bereinigen
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
                        
                        # Echten Namen speichern
                        real_name_found = str(row.iloc[col_idx_realname])
                        
                    except Exception as e:
                        st.error(f"Fehler beim Lesen der Werte in Zeile {idx}: {e}")
                    
                    break
        
        if found_stats:
            # --- STATUS ANZEIGE ---
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
                # Header=None, da wir Zeilen per Index ansprechen wollen
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Fixe Zeilen aus CSV Questbuch 4.0:
            # Zeile 2 (Index 1): Quest Namen (Grundregeln...)
            quest_names_row = df_quests.iloc[1]
            
            # Master XP Zeile: Oft Zeile 5 (Index 4). 
            # Falls die fehlt, versuchen wir später Fallback.
            quest_xp_master_row = df_quests.iloc[4] if len(df_quests) > 4 else None

            # --- NAMENSSUCHE ---
            # Wir suchen den Schüler in Spalte B (Index 1) basierend auf der CSV
            q_idx = -1
            
            # Name aus XP Rechner aufbereiten
            # Beispiel: "11T1 Müller Max" -> ["müller", "max"]
            search_parts = real_name_found.lower().replace("11t1", "").replace("11t2", "").split(" ")
            search_tokens = [t for t in search_parts if len(t) > 2]
            if not search_tokens: search_tokens = [real_name_found.lower()]

            # Suche ab Zeile 5 abwärts
            for idx in range(5, len(df_quests)):
                row = df_quests.iloc[idx]
                
                # Wir bauen einen String aus Spalte A und B zusammen, um sicher zu gehen
                # (CSV sah so aus als wäre es in Spalte B)
                name_check_str = f"{str(row.iloc[0])} {str(row.iloc[1])}".lower()
                
                match = True
                for token in search_tokens:
                    if token not in name_check_str:
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
                
                # --- QUEST SPALTEN LOGIK ---
                # Die Quests stehen in Spalte D (Index 3).
                # Struktur: [D: Name/Status] [E: XP] [F: Name/Status] [G: XP] ...
                # Also immer Schritte von 2: 3, 5, 7, 9...
                
                max_col = min(len(quest_names_row), len(student_row))
                
                for c in range(3, max_col - 1, 2):
                    try:
                        # 1. Quest Name aus Header (Zeile 2 / Index 1)
                        q_name = str(quest_names_row.iloc[c])
                        
                        if q_name == "nan" or not q_name.strip(): 
                            continue
                        
                        # Filter
                        q_check = q_name.lower()
                        if "summe" in q_check or "game" in q_check or "total" in q_check:
                            continue

                        # 2. Status aus Schülerzeile (Gleiche Spalte wie Name)
                        status_val = str(student_row.iloc[c]).strip().lower()
                        
                        # 3. XP Wert holen
                        # Priorität A: Aus der Spalte direkt rechts daneben beim Schüler (Spalte c + 1)
                        # (Das sah in der CSV so aus: "Abgeschlossen", "19")
                        xp_val = "?"
                        try:
                            xp_cell_student = student_row.iloc[c+1]
                            xp_val = int(float(str(xp_cell_student).replace(',', '.')))
                            
                            # Wenn Schüler 0 hat, ist die Quest vllt noch nicht fertig.
                            # Dann brauchen wir den Max-Wert aus der Master-Zeile (Index 4)
                            if xp_val == 0 and quest_xp_master_row is not None:
                                xp_master = quest_xp_master_row.iloc[c] # Oft steht XP im Master unter dem Namen
                                # Oder auch rechts daneben? In deiner CSV "RPG Maker" standen XP separat.
                                # Wir versuchen Master-Zeile, Spalte C (gleiche wie Name)
                                try:
                                    xp_val = int(float(str(xp_master).replace(',', '.')))
                                except:
                                    # Oder Master-Zeile, Spalte C+1
                                    xp_val = int(float(str(quest_xp_master_row.iloc[c+1]).replace(',', '.')))

                        except:
                            xp_val = "?"

                        # Logik: Abgeschlossen?
                        is_completed = "abgeschlossen" in status_val and "nicht" not in status_val
                        
                        # Alternativ: Wenn XP > 0 beim Schüler eingetragen sind, gilt es als fertig
                        try:
                            val_check = int(float(str(student_row.iloc[c+1]).replace(',', '.')))
                            if val_check > 0:
                                is_completed = True
                                xp_val = val_check # Nimm die echten Punkte
                        except:
                            pass

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
                st.caption(f"Gesucht in Spalten A/B nach: {search_parts}")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")
            st.info("Hinweis: Der Gamertag muss im Blatt 'XP Rechner 3.0' in Spalte M (Rangliste) stehen.")

except Exception as e:
    st.error(f"Ein Systemfehler ist aufgetreten: {e}")


