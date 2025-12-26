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
        df_xp.columns = df_xp.columns.str.strip()
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

    if gamertag_input:
        # Wir suchen alle Spalten, die "Gamertag" heißen
        gamertag_cols = [c for c in df_xp.columns if "Gamertag" in str(c)]
        
        if not gamertag_cols:
            st.error("Kritischer Fehler: Keine Spalte 'Gamertag' gefunden.")
            st.stop()
            
        # --- DER SMART-SEARCH ALGORITHMUS ---
        best_match = None
        
        # Wir gehen alle Gamertag-Spalten durch
        for g_col in gamertag_cols:
            col_idx = df_xp.columns.get_loc(g_col)
            
            # --- WICHTIGE ÄNDERUNG ---
            # Wir ignorieren den gelben Bereich (links).
            # Die blaue Tabelle beginnt ab Spalte L (der 12. Spalte -> Index 11).
            # Alles davor (Index < 11) wird übersprungen.
            if col_idx < 11:
                continue
            
            # Suche in dieser gültigen Spalte (Blauer Bereich)
            for idx, row in df_xp.iterrows():
                val = str(row.iloc[col_idx]).strip()
                
                if val.lower() == gamertag_input.strip().lower():
                    # TREFFER!
                    try:
                        # Im blauen Bereich: Gamertag | XP | Level | Stufe
                        # Also XP = Spalte + 1, Level = Spalte + 2
                        raw_xp = row.iloc[col_idx + 1]
                        raw_level = row.iloc[col_idx + 2]
                    except:
                        continue 
                    
                    is_game_over = "†" in str(raw_level) or "Game" in str(raw_level)
                    
                    # XP sicher als Zahl holen
                    try:
                        current_xp = int(raw_xp)
                    except:
                        current_xp = 0

                    match_data = {
                        "row": row,
                        "xp": current_xp,
                        "raw_level": raw_level,
                        "is_game_over": is_game_over
                    }
                    
                    # Da wir jetzt im richtigen Bereich sind, nehmen wir den Treffer.
                    # Falls der Schüler mehrfach auftaucht (z.B. Gesamtliste UND Klassenliste),
                    # nehmen wir den mit den meisten XP (falls es Updates gab) oder einfach den ersten.
                    if best_match is None or match_data["xp"] > best_match["xp"]:
                        best_match = match_data
        
        # --- ERGEBNIS ANZEIGEN ---
        if best_match:
            # Name suchen (Fallback auf Spalte D - "Klasse + Name")
            # Wir suchen die Spalte D (Index 3) in der aktuellen Zeile
            real_name = "Schüler"
            # Versuch den Namen aus der Zeile zu holen (Spalte Index 3 ist meist der Name)
            if len(df_xp.columns) > 3:
                real_name = best_match["row"].iloc[3]

            display_level = str(best_match["raw_level"])
            xp_num = best_match["xp"]
            
            # Level als Zahl für Progressbar
            level_num = 0
            try:
                level_num = int(best_match["raw_level"])
            except:
                pass

            st.balloons()
            st.success(f"Willkommen, {real_name}!")
            
            col1, col2 = st.columns(2)
            col1.metric("Level", display_level)
            col2.metric("XP Total", xp_num)
            
            if level_num > 0:
                # Level-Fortschritt Logik (Beispiel: 2000 XP pro Level als Balken-Basis)
                progress = min((xp_num % 1000) / 1000, 1.0)
                st.progress(progress, text="Fortschritt")
            elif best_match["is_game_over"]:
                st.error("💀 GAME OVER - Bitte beim Lehrer melden!")

            # --- QUESTS LADEN ---
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None)
            except:
                st.warning("Konnte Quests nicht laden.")
                st.stop()

            quest_names = df_quests.iloc[1] 
            quest_xps = df_quests.iloc[4]

            # Schüler im Questbuch suchen
            quest_row_index = -1
            
            # Da wir den Namen aus Spalte D haben (z.B. "Antonia Brummer"), suchen wir danach
            # Wir vergleichen etwas fehlertolerant
            for idx, row in df_quests.iterrows():
                # Wir bauen einen String aus den ersten Spalten der Questbuch-Zeile
                # Spalte B (Index 1) ist meist der Name
                name_in_questbuch = str(row.iloc[1]) 
                
                # Prüfen ob "Antonia Brummer" in "11T1 Antonia Brummer" steckt oder umgekehrt
                if str(real_name).lower() in name_in_questbuch.lower() or name_in_questbuch.lower() in str(real_name).lower():
                    quest_row_index = idx
                    break
            
            if quest_row_index != -1:
                student_quest_row = df_quests.iloc[quest_row_index]
                
                st.divider()
                st.subheader("Deine Quests")
                
                cols = st.columns(3)
                col_counter = 0
                found_quests = False
                
                # Durchlaufe alle Quest-Spalten (ab Spalte D / Index 3)
                for c in range(3, df_quests.shape[1]):
                    try:
                        q_name = str(quest_names.iloc[c])
                        if q_name == "nan" or q_name.strip() == "":
                            continue
                            
                        val = str(student_quest_row.iloc[c])
                        
                        if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                            found_quests = True
                            try:
                                xp_val = int(float(str(quest_xps.iloc[c])))
                            except:
                                xp_val = "?"
                            
                            with cols[col_counter % 3]:
                                st.success(f"✅ {q_name}\n\n**+{xp_val} XP**")
                            col_counter += 1
                    except:
                        continue
                
                if not found_quests:
                    st.info("Noch keine Quests abgeschlossen.")
            else:
                st.warning(f"Konnte Quests für '{real_name}' nicht finden.")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

except Exception as e:
    st.error("Ein kritischer Fehler ist aufgetreten:")
    st.code(str(e))


