import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- SEITE KONFIGURIEREN ---
st.set_page_config(page_title="TZ Questlog", page_icon="📐")
st.title("📐 Technisches Zeichnen - Questlog")

# --- KONFIGURATION ---
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q"
blatt_mapping = "XP Rechner 3.0"
blatt_quests = "Questbuch 4.0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)

    # --- SCHRITT 1: DATEN LADEN ---
    try:
        # Wir laden Zeile 2 als Header (Index 1)
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1)
        # Leerzeichen in Spaltennamen entfernen
        df_xp.columns = df_xp.columns.str.strip()
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        # Wir suchen alle Spalten, die "Gamertag" heißen
        gamertag_cols = [c for c in df_xp.columns if "Gamertag" in str(c)]
        
        if not gamertag_cols:
            st.error("Kritischer Fehler: Keine Spalte 'Gamertag' gefunden.")
            st.stop()
            
        # --- DER SMART-SEARCH ALGORITHMUS ---
        best_match = None
        
        # Wir gehen alle Gamertag-Spalten durch (Links nach Rechts)
        for g_col in gamertag_cols:
            # Index der Spalte ermitteln
            col_idx = df_xp.columns.get_loc(g_col)
            
            # Suchen wir den Schüler in DIESER Spalte
            # Wir iterieren durch die Zeilen
            for idx, row in df_xp.iterrows():
                val = str(row.iloc[col_idx]).strip()
                
                if val.lower() == gamertag_input.strip().lower():
                    # TREFFER! Jetzt prüfen wir die Qualität des Treffers.
                    
                    # XP und Level stehen meist rechts daneben (+1 und +2)
                    try:
                        raw_xp = row.iloc[col_idx + 1]
                        raw_level = row.iloc[col_idx + 2]
                    except:
                        continue # Spalte existiert nicht, weiter
                    
                    # Prüfen: Ist es ein Game Over (†)?
                    is_game_over = "†" in str(raw_level) or "Game" in str(raw_level)
                    
                    match_data = {
                        "row": row,
                        "xp": raw_xp,
                        "level": raw_level,
                        "is_game_over": is_game_over
                    }
                    
                    # Logik: Wir bevorzugen Treffer, die KEIN Game Over sind.
                    if best_match is None:
                        best_match = match_data
                    elif best_match["is_game_over"] and not is_game_over:
                        # Wir haben einen besseren Treffer gefunden (kein Kreuz)!
                        best_match = match_data
        
        # --- ERGEBNIS AUSWERTEN ---
        if best_match:
            # Wir haben den Schüler gefunden!
            
            # Name holen (Fallback auf Spalte 3/D, da Name meist fix ist)
            real_name = "Schüler"
            # Suche Spalte mit "Name"
            for c in df_xp.columns:
                if "Klasse + Name" in str(c):
                    real_name = best_match["row"][c]
                    break
            
            # Werte Aufbereiten
            raw_level = best_match["level"]
            raw_xp = best_match["xp"]
            
            display_level = str(raw_level)
            level_num = 0
            xp_num = 0
            
            # Versuch, Level in Zahl zu wandeln
            try:
                level_num = int(raw_level)
            except:
                pass # Bleibt 0
                
            # Versuch, XP in Zahl zu wandeln
            try:
                xp_num = int(raw_xp)
            except:
                pass

            st.balloons()
            st.success(f"Willkommen, {real_name}!")
            
            col1, col2 = st.columns(2)
            col1.metric("Level", display_level)
            col2.metric("XP Total", xp_num)
            
            if level_num > 0:
                progress = min((xp_num % 1000) / 1000, 1.0)
                st.progress(progress, text="Fortschritt")
            elif "†" in display_level:
                st.error("💀 GAME OVER - Bitte beim Lehrer melden!")

            # --- SCHRITT 2: QUESTS LADEN ---
            try:
                # header=None ist wichtig, wir greifen über Index zu
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None)
            except:
                st.warning("Konnte Quests nicht laden.")
                st.stop()

            # Namen der Quests (Zeile 2 / Index 1)
            quest_names = df_quests.iloc[1] 
            # XP Werte (Zeile 5 / Index 4)
            quest_xps = df_quests.iloc[4]

            # Wir suchen die Zeile des Schülers im Questbuch (über den echten Namen)
            quest_row_index = -1
            
            # Wir scannen die ersten Spalten nach dem Namen
            for idx, row in df_quests.iterrows():
                # Wir bauen einen Such-String aus den ersten 4 Spalten
                row_str = " ".join([str(x) for x in row.values[:4]]).lower()
                if str(real_name).lower() in row_str:
                    quest_row_index = idx
                    break
            
            if quest_row_index != -1:
                student_quest_row = df_quests.iloc[quest_row_index]
                
                st.divider()
                st.subheader("Deine Quests")
                
                cols = st.columns(3)
                col_counter = 0
                found_quests = False
                
                # --- QUEST SCHLEIFE (Fix für Error '9') ---
                # Wir iterieren über die Spaltenindizes
                for c in range(3, df_quests.shape[1]):
                    try:
                        # 1. Quest Name prüfen
                        q_name = str(quest_names.iloc[c])
                        if q_name == "nan" or q_name.strip() == "":
                            continue
                            
                        # 2. Status beim Schüler prüfen
                        val = str(student_quest_row.iloc[c])
                        
                        if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                            found_quests = True
                            
                            # 3. XP Wert holen (sicher!)
                            try:
                                raw_xp_val = str(quest_xps.iloc[c])
                                xp_val = int(float(raw_xp_val))
                            except:
                                xp_val = "?"
                            
                            with cols[col_counter % 3]:
                                st.success(f"✅ {q_name}\n\n**+{xp_val} XP**")
                            col_counter += 1
                            
                    except Exception:
                        # Falls eine Spalte kaputt ist, überspringen wir sie einfach stillschweigend
                        continue
                
                if not found_quests:
                    st.info("Noch keine Quests abgeschlossen.")
            else:
                st.warning(f"Konnte '{real_name}' im Questbuch nicht finden.")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

except Exception as e:
    st.error("Ein kritischer Fehler ist aufgetreten:")
    st.code(str(e))

