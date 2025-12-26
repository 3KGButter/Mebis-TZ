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

# WICHTIG: Angepasst auf deine 4.1 Datei
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

# Button zum Neuladen
with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.1 | 25/26")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- SCHRITT 1: XP RECHNER LADEN ---
    try:
        # header=1 bedeutet: Zeile 2 ist die Überschrift (genau wie in deinem alten Code)
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        found_row_index = -1
        best_stats = None
        
        # Wir suchen in Spalte L (Index 11) bis P (Index 15)
        # Laut deiner CSV ist Gamertag in Spalte L
        target_col_start = 11 
        target_col_end = min(17, len(df_xp.columns))
        
        for col_idx in range(target_col_start, target_col_end):
            col_header = str(df_xp.columns[col_idx]).strip()
            
            # Prüfen ob wir in der Gamertag-Spalte sind
            if "Gamertag" in col_header:
                col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
                matches = col_data[col_data == input_clean].index
                
                if not matches.empty:
                    found_row_index = matches[0]
                    row = df_xp.iloc[found_row_index]
                    
                    # Daten auslesen (Spalte M=XP, N=Level, etc.)
                    if col_idx + 2 < len(df_xp.columns):
                        raw_xp = row.iloc[col_idx + 1] # Spalte rechts daneben (M)
                        raw_level = row.iloc[col_idx + 2] # Spalte daneben (N)
                        
                        raw_stufe = ""
                        if col_idx + 3 < len(df_xp.columns):
                            raw_stufe = str(row.iloc[col_idx + 3])
                            
                        check_str = f"{raw_level} {raw_stufe}".lower()
                        is_game_over = "†" in check_str or "game" in check_str or "over" in check_str
                        
                        try:
                            xp_str = str(raw_xp).replace('.', '').replace(',', '.')
                            xp_val = int(float(xp_str))
                        except:
                            xp_val = 0
                            
                        best_stats = {
                            "xp": xp_val,
                            "level": raw_level,
                            "is_game_over": is_game_over
                        }
                    break

        if best_stats and found_row_index != -1:
            # --- ECHTEN NAMEN HOLEN ---
            # Da die Listen alphabetisch synchron sind, holen wir den Namen aus Spalte D (Index 3)
            # der gleichen Zeile.
            try:
                real_name_found = str(df_xp.iloc[found_row_index, 3])
            except:
                real_name_found = "Unbekannt"

            # --- ANZEIGE STATS ---
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
                # Wir laden ohne Header (None), um Zeilen per Index anzusprechen
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            # Header Zeile ist Zeile 2 (Index 1) im Excel
            quest_names = df_quests.iloc[1] 
            
            # --- SCHÜLER SUCHEN IM QUESTBUCH ---
            q_idx = -1
            
            # Name säubern (Klasse entfernen für bessere Trefferquote)
            # z.B. "11T1 Antonia Brummer" -> Suche nach "Antonia" und "Brummer"
            search_name_clean = real_name_found.strip().lower()
            
            # Entferne Klassenbezeichnungen aus dem Suchstring, falls vorhanden
            for kl in ["11t1", "11t2", "11t3", "11t4", "12t1", "13t1"]:
                search_name_clean = search_name_clean.replace(kl.lower(), "")

            search_tokens = [t for t in search_name_clean.split(" ") if len(t) > 2]
            if not search_tokens: search_tokens = [search_name_clean]

            # Suche ab Zeile 3
            for idx in range(2, len(df_quests)):
                row = df_quests.iloc[idx]
                
                # Prüfe Spalte B (Index 1) auf Namensbestandteile
                # (Zur Sicherheit auch Spalte A, falls Vorname/Nachname getrennt)
                row_txt = f"{str(row.iloc[0])} {str(row.iloc[1])}".lower()
                
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
                
                # --- QUEST LOGIK (ANGEPASST AN NEUES EXCEL) ---
                # Die Quests beginnen ab Spalte D (Index 3).
                # Struktur: [Spalte D: Status] [Spalte E: XP] [Spalte F: Status] ...
                # Wir springen immer 2 Spalten weiter!
                
                max_cols = min(len(quest_names), len(student_quest_row))
                
                for c in range(3, max_cols - 1, 2):
                    try:
                        q_name = str(quest_names.iloc[c])
                        
                        if q_name == "nan" or not q_name.strip(): continue
                        
                        q_check = q_name.lower()
                        if "summe" in q_check or "game" in q_check or "over" in q_check or "total" in q_check:
                            continue
                        
                        # 1. Status prüfen (Spalte c)
                        val_status = str(student_quest_row.iloc[c]).strip().lower()
                        
                        # 2. XP prüfen (Spalte c + 1 -> rechts daneben)
                        val_xp_raw = student_quest_row.iloc[c+1]
                        
                        try:
                            xp_val = int(float(str(val_xp_raw).replace(',', '.')))
                        except:
                            xp_val = "?"

                        # Abgeschlossen Logik
                        is_completed = "abgeschlossen" in val_status and "nicht" not in val_status
                        
                        # Zusatz-Check: Wenn XP > 0 drin stehen, gilt es auch als erledigt
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
                st.caption(f"Wir haben im Questbuch nach diesen Namensteilen gesucht: {search_tokens}")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht in der Rangliste (Spalte L) gefunden.")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")


