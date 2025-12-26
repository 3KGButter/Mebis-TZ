import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
# Hier angepasst: Kurzer Titel, Icon nur im Browser-Tab
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
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        input_clean = gamertag_input.strip().lower()
        
        # --- SCHRITT 1: ECHTEN NAMEN FINDEN (Links, Spalte 0-10) ---
        # Nur für interne Quest-Suche nötig
        real_name_found = None
        
        # Wir suchen Spalten, die "Gamertag" und "Name" heißen im linken Bereich
        col_idx_gamertag_left = -1
        col_idx_name_left = -1
        
        for i in range(min(11, len(df_xp.columns))):
            col_name = str(df_xp.columns[i]).strip()
            if "Gamertag" in col_name:
                col_idx_gamertag_left = i
            if "Klasse + Name" in col_name:
                col_idx_name_left = i
        
        if col_idx_gamertag_left != -1 and col_idx_name_left != -1:
            for idx, row in df_xp.iterrows():
                val = str(row.iloc[col_idx_gamertag_left]).strip()
                if val.lower() == input_clean:
                    real_name_found = row.iloc[col_idx_name_left]
                    break
        
        if not real_name_found:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")
            st.stop()

        # --- SCHRITT 2: XP & LEVEL FINDEN (Rechts, ab Spalte L/11) ---
        # Wir suchen einfach überall nach dem Gamertag und nehmen das beste Ergebnis.
        best_stats = None
        
        # Wir scannen ab Spalte L (Index 11) bis zum Ende
        for col_idx in range(11, len(df_xp.columns)):
            col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
            matches = col_data[col_data == input_clean].index
            
            for row_idx in matches:
                try:
                    row = df_xp.iloc[row_idx]
                    
                    # Wir nehmen an: Gamertag -> XP (+1) -> Level (+2)
                    if col_idx + 2 < len(df_xp.columns):
                        raw_xp = row.iloc[col_idx + 1]
                        raw_level = row.iloc[col_idx + 2]
                    else:
                        continue

                    # Game Over Check (Suche in Level und Nachbarzellen nach Kreuz oder Text)
                    # Wir prüfen Level (+2) und Stufe (+3)
                    raw_stufe = ""
                    if col_idx + 3 < len(df_xp.columns):
                        raw_stufe = str(row.iloc[col_idx + 3])
                    
                    check_str = f"{raw_level} {raw_stufe}".lower()
                    is_game_over = "†" in check_str or "game" in check_str or "over" in check_str
                    
                    try:
                        xp_val = int(float(str(raw_xp).replace(',','.')))
                    except:
                        xp_val = 0
                        
                    stats = {
                        "xp": xp_val,
                        "level": raw_level,
                        "is_game_over": is_game_over
                    }
                    
                    # Entscheidung: Ist das der "beste" Eintrag?
                    if best_stats is None:
                        best_stats = stats
                    else:
                        # Bevorzuge Einträge, die NICHT Game Over sind
                        if not stats["is_game_over"] and best_stats["is_game_over"]:
                            best_stats = stats
                        # Wenn beide gleich sind (beide ok oder beide tot), nimm den mit MEHR XP
                        elif stats["is_game_over"] == best_stats["is_game_over"]:
                            if stats["xp"] > best_stats["xp"]:
                                best_stats = stats
                except:
                    continue

        if best_stats:
            # Formatierung
            display_level = str(best_stats["level"])
            try:
                display_level = str(int(float(display_level)))
            except:
                pass 
                
            xp_num = best_stats["xp"]
            is_go = best_stats["is_game_over"]

            # --- ANZEIGE ---
            if not is_go:
                st.balloons()
            
            st.success(f"Willkommen zurück, **{gamertag_input}**!")
            
            # Schlichte 2-Spalten-Optik (Rang entfernt, da fehleranfällig)
            c1, c2 = st.columns(2)
            c1.metric("Level", display_level)
            c2.metric("XP Total", xp_num)
            
            if not is_go:
                prog_val, prog_text = calculate_progress(xp_num)
                st.progress(prog_val, text=prog_text)
            else:
                st.error("💀 GAME OVER - Bitte beim Lehrer melden!")

            # --- QUESTS ---
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            except:
                st.warning("Quest-Daten nicht verfügbar.")
                st.stop()

            quest_names = df_quests.iloc[1] 
            quest_xps = df_quests.iloc[4]

            # Namenssuche im Questbuch
            q_idx = -1
            search_name = str(real_name_found).strip().lower()
            
            # Wir suchen in den ersten 4 Spalten nach dem Namen
            for idx, row in df_quests.iterrows():
                row_txt = " ".join([str(x) for x in row.values[:4]]).lower()
                if search_name in row_txt:
                    q_idx = idx
                    break
            
            if q_idx != -1:
                student_quest_row = df_quests.iloc[q_idx]
                
                st.divider()
                st.subheader("Deine Quests")
                
                tab1, tab2 = st.tabs(["✅ Erledigt", "❌ Offen"])
                
                with tab1:
                    cols = st.columns(3)
                    cnt = 0
                    found_any = False
                    
                    for c in range(3, df_quests.shape[1]):
                        try:
                            q_name = str(quest_names.iloc[c])
                            if q_name == "nan" or not q_name.strip(): continue
                            
                            val = str(student_quest_row.iloc[c])
                            
                            if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                                found_any = True
                                try:
                                    xp_val = int(float(str(quest_xps.iloc[c])))
                                except:
                                    xp_val = "?"
                                    
                                with cols[cnt % 3]:
                                    st.success(f"**{q_name}**\n\n+{xp_val} XP")
                                cnt += 1
                        except:
                            continue
                            
                    if not found_any:
                        if is_go:
                            st.markdown("""
                            <div style="text-align: center; margin-top: 20px;">
                                <h1 style="font-size: 80px;">💀</h1>
                                <h2 style="color: red;">GAME OVER</h2>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("Noch keine Quests abgeschlossen.")

                with tab2:
                    cols = st.columns(3)
                    cnt = 0
                    for c in range(3, df_quests.shape[1]):
                        try:
                            q_name = str(quest_names.iloc[c])
                            if q_name == "nan" or not q_name.strip(): continue
                            val = str(student_quest_row.iloc[c])
                            if not ("abgeschlossen" in val.lower() and "nicht" not in val.lower()):
                                try:
                                    xp_val = int(float(str(quest_xps.iloc[c])))
                                except:
                                    xp_val = "?"
                                with cols[cnt % 3]:
                                    st.markdown(f"""
                                    <div style="border:1px solid #ddd; padding:10px; border-radius:5px; opacity:0.6;">
                                        <strong>{q_name}</strong><br>🔒 {xp_val} XP
                                    </div>
                                    """, unsafe_allow_html=True)
                                cnt += 1
                        except:
                            continue

            else:
                st.warning(f"Konnte Quests für '{real_name_found}' nicht laden.")

        else:
            # Falls Name gefunden (Links), aber keine XP (Rechts)
            st.error(f"Für '{gamertag_input}' wurden noch keine XP berechnet.")

except Exception as e:
    st.error("Ein Fehler ist aufgetreten. Bitte Seite neu laden.")


