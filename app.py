import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="Questlog", page_icon="🛡️")
st.title("🛡️ Questlog")

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

# --- WICHTIG: DER FIX FÜR DEN 10x XP FEHLER ---
def clean_xp_value(val):
    """
    Verwandelt Zelleninhalt sicher in eine Zahl.
    Verhindert, dass 4349.0 zu 43490 wird.
    """
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return 0
    
    # 1. Wenn es schon eine Zahl ist, nimm sie direkt (Fix für 10x Problem)
    if isinstance(val, (int, float)):
        return int(val)
    
    s_val = str(val).strip()
    
    # 2. Wenn es wie eine Float aussieht (4349.0), entferne das .0 am Ende
    if s_val.endswith(".0"):
        s_val = s_val[:-2]
        
    # 3. Jetzt sicher Punkte/Kommas behandeln
    try:
        # Standard: Komma zu Punkt (Deutsch -> Englisch)
        return int(float(s_val.replace(',', '.')))
    except:
        # Fallback: Alles bereinigen
        try:
            # Entfernt Tausenderpunkte (1.000 -> 1000)
            clean_str = s_val.replace('.', '').replace(',', '.')
            return int(float(clean_str))
        except:
            return 0

# --- DATENBANK VERBINDUNG ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

# Button zum Neuladen
with st.sidebar:
    if st.button("🔄 Daten aktualisieren"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Version 4.7 (Stable)")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # ------------------------------------------------------------------
    # TEIL 1: XP RECHNER (GAMERTAG & LEVEL)
    # ------------------------------------------------------------------
    try:
        # Wir laden mit header=1 (Zeile 2 ist Header), wie im funktionierenden Original
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Gib deinen Gamertag ein, um deinen Status zu prüfen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        found_row_index = -1
        best_stats = None
        
        # Suche in Spalten L (ca. Index 11) bis Ende nach dem Gamertag
        target_col_start = 11 
        
        # Sicherheitscheck, falls Tabelle kleiner ist
        start_scan = min(target_col_start, len(df_xp.columns)-1)

        for col_idx in range(start_scan, len(df_xp.columns)):
            col_header = str(df_xp.columns[col_idx]).strip()
            
            # Wir suchen Spalten, die "Gamertag" im Header haben
            if "Gamertag" in col_header:
                col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
                matches = col_data[col_data == input_clean].index
                
                if not matches.empty:
                    found_row_index = matches[0]
                    row = df_xp.iloc[found_row_index]
                    
                    # Wenn wir Gamertag gefunden haben, stehen XP und Level meist rechts daneben
                    if col_idx + 2 < len(df_xp.columns):
                        raw_xp = row.iloc[col_idx + 1]   # Spalte M (XP)
                        raw_level = row.iloc[col_idx + 2] # Spalte N (Level)
                        
                        raw_stufe = ""
                        if col_idx + 3 < len(df_xp.columns):
                            raw_stufe = str(row.iloc[col_idx + 3])
                            
                        check_str = f"{raw_level} {raw_stufe}".lower()
                        is_game_over = "†" in check_str or "game" in check_str or "over" in check_str
                        
                        # HIER: Neue sichere Bereinigung nutzen
                        xp_val = clean_xp_value(raw_xp)
                            
                        best_stats = {
                            "xp": xp_val,
                            "level": raw_level,
                            "is_game_over": is_game_over
                        }
                    break

        if best_stats and found_row_index != -1:
            # --- NAME FINDEN ---
            # Wir nehmen den Namen aus Spalte D (Index 3) der gleichen Zeile
            try:
                real_name_found = str(df_xp.iloc[found_row_index, 3])
            except:
                real_name_found = "Unbekannt"

            # --- ANZEIGE OBEN ---
            display_level = str(best_stats["level"])
            # Level auch sicher säubern, falls "9.0" drin steht
            if "†" in display_level:
                display_level = "💀"
            else:
                try:
                    display_level = str(int(float(str(display_level).replace(',', '.'))))
                except:
                    pass 
                
            xp_num = best_stats["xp"]
            is_go = best_stats["is_game_over"]

            if not is_go:
                st.balloons()
                st.success(f"Willkommen zurück, **{gamertag_input}**!")
            
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

            # ------------------------------------------------------------------
            # TEIL 2: QUESTBUCH LADEN (ROBUST)
            # ------------------------------------------------------------------
            try:
                # header=None ist wichtig, damit wir per Index zugreifen können
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten konnten nicht geladen werden.")
                st.stop()

            # Quest-Namen sind in Zeile 2 (Index 1)
            quest_names_row = df_quests.iloc[1]
            
            # --- SCHÜLER SUCHEN ---
            q_idx = -1
            
            # Name vorbereiten
            search_name_clean = real_name_found.strip().lower()
            # Klassenbezeichnungen entfernen
            for kl in ["11t1", "11t2", "11t3", "11t4", "12t1", "13t1"]:
                search_name_clean = search_name_clean.replace(kl, "")
            
            # Teile Name auf (z.B. "Antonia" und "Brummer")
            search_tokens = [t for t in search_name_clean.split(" ") if len(t) > 2]
            if not search_tokens: search_tokens = [search_name_clean]

            # Wir suchen ab Zeile 5 nach unten
            for idx in range(4, len(df_quests)):
                row = df_quests.iloc[idx]
                
                # Kombiniere Spalte A und B (Index 0 und 1) für den Namen
                # In deiner CSV ist Spalte A oft leer, B hat den Namen
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
                
                # --- QUEST SCHLEIFE ---
                # Wir gehen durch die Spalten. Start bei Index 3 (Spalte D).
                # Immer +2 Schritte (D, F, H...)
                
                # Sicherstellen, dass wir nicht über das Ende hinauslaufen
                max_cols = min(len(quest_names_row), len(student_quest_row))
                
                for c in range(3, max_cols - 1, 2):
                    try:
                        # 1. Name holen
                        q_name = str(quest_names_row.iloc[c])
                        
                        # Wenn leer, prüfen ob Name vielleicht in Spalte davor steht (Merged Cells Problem)
                        if q_name == "nan" or not q_name.strip():
                             continue
                        
                        # Filter für "Summe" etc.
                        if any(x in q_name.lower() for x in ["summe", "game", "total", "questart"]): continue

                        # 2. Werte holen (Status und XP)
                        # Status steht in Spalte c
                        val_status = str(student_quest_row.iloc[c]).strip().lower()
                        # XP steht in Spalte c+1 (rechts daneben)
                        val_xp_raw = student_quest_row.iloc[c+1]
                        
                        xp_val = clean_xp_value(val_xp_raw)
                        if xp_val == 0: xp_val = "?"

                        # 3. Status Logik
                        is_completed = "abgeschlossen" in val_status and "nicht" not in val_status
                        
                        # Wenn Punkte > 0 sind, ist es erledigt (auch wenn Status leer ist)
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
                        st.info("Keine offenen Quests in dieser Kategorie.")

            else:
                st.warning(f"Konnte Quests für '{real_name_found}' nicht finden.")
                # Debugging Info (nur für dich, kann später weg):
                st.caption(f"Gesucht nach Tokens: {search_tokens}")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

except Exception as e:
    st.error(f"Ein Fehler ist aufgetreten: {e}")


