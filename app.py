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

    # --- SCHRITT 1: GAMERTAG & ECHTNAME LADEN ---
    try:
        # Wir laden Zeile 2 als Header (Index 1), da Zeile 1 nur Überschriften sind
        df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1)
        # Leerzeichen in Spaltennamen entfernen
        df_xp.columns = df_xp.columns.str.strip()
    except Exception as e:
        st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
        st.stop()

    st.info("Logge dich ein, um deinen Status zu sehen.")
    gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. BrAnt")

    if gamertag_input:
        # --- SPALTEN SUCHEN (DER FIX) ---
        # Wir suchen ALLE Spalten, die "Gamertag" heißen
        gamertag_cols = [c for c in df_xp.columns if "Gamertag" in str(c)]
        
        if not gamertag_cols:
            st.error("Konnte Spalte 'Gamertag' nicht finden.")
            st.stop()
            
        # WICHTIG: Wir nehmen die LETZTE gefundene Gamertag-Spalte.
        # Grund: Links steht die Rohberechnung (mit Fehlern/Kreuzen), 
        # rechts (im blauen Bereich) steht die saubere Rangliste.
        target_gamertag_col = gamertag_cols[-1]
        
        # Für den Namen suchen wir eine Spalte wie "Klasse + Name" oder "Nachname"
        col_realname = None
        for col in df_xp.columns:
            if "Klasse + Name" in str(col):
                col_realname = col
                break
        if not col_realname:
             # Fallback: Spalte D (Index 3)
             col_realname = df_xp.columns[3]

        # --- SCHÜLER SUCHEN ---
        # Wir suchen im DataFrame in der RECHTEN Spalte (target_gamertag_col)
        # Dazu müssen wir wissen, an welcher Position (Index) diese Spalte steht
        target_col_idx = df_xp.columns.get_loc(target_gamertag_col)
        
        # Manuelle Suche durch die Zeilen, um sicherzugehen
        found_row = None
        
        for idx, row in df_xp.iterrows():
            # Wert in der Gamertag-Spalte prüfen
            val = str(row.iloc[target_col_idx]).strip()
            if val.lower() == gamertag_input.strip().lower():
                found_row = row
                break
        
        if found_row is not None:
            # Wir haben den Schüler im RICHTIGEN Bereich gefunden!
            
            # Jetzt holen wir XP und Level.
            # In deiner Tabelle stehen XP und Level immer RECHTS neben dem Gamertag.
            # Gamertag = Spalte X -> XP = Spalte X+1, Level = Spalte X+2 (ungefähr)
            
            # Wir suchen im DataFrame nach Spalten "XP" und "Level", die NACH unserer Gamertag-Spalte kommen
            # Da das schwierig ist, nehmen wir die Werte direkt aus der Zeile anhand ihrer Position
            
            # Wir gehen davon aus: Gamertag | XP | Level | Stufe (wie im blauen Bereich)
            try:
                # XP ist meist direkt rechts daneben (+1)
                xp_val_raw = found_row.iloc[target_col_idx + 1]
                # Level ist daneben (+2)
                level_val_raw = found_row.iloc[target_col_idx + 2]
                # Name holen wir aus der festen Namensspalte
                real_name = found_row[col_realname]
            except:
                st.error("Konnte XP/Level neben dem Gamertag nicht lesen.")
                st.stop()

            # Daten bereinigen
            try:
                display_level = str(int(level_val_raw))
                level_num = int(level_val_raw)
            except:
                # Falls es doch ein Kreuz ist oder Text
                display_level = str(level_val_raw)
                level_num = 0
            
            try:
                xp_num = int(xp_val_raw)
            except:
                xp_num = 0

            st.balloons()
            st.success(f"Willkommen, {real_name}!")
            
            # Dashboard
            col1, col2 = st.columns(2)
            col1.metric("Level", display_level)
            col2.metric("XP Total", xp_num)
            
            if level_num > 0:
                progress = min((xp_num % 1000) / 1000, 1.0)
                st.progress(progress, text="Fortschritt")
            elif "†" in display_level or "Game" in str(display_level):
                st.error("💀 GAME OVER - Bitte beim Lehrer melden!")

            # --- SCHRITT 2: QUESTS LADEN ---
            try:
                df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None)
            except:
                st.warning("Konnte Quests nicht laden.")
                st.stop()

            quest_names = df_quests.iloc[1] 
            quest_xps = df_quests.iloc[4]

            # Schüler im Questbuch suchen (über den echten Namen)
            quest_row_index = -1
            for idx, row in df_quests.iterrows():
                # Suche in den ersten 4 Spalten nach dem Namen
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
                
                # --- QUEST SCHLEIFE (FIX FÜR FEHLER 9) ---
                # Wir iterieren sicher durch die Spalten
                for c in range(3, df_quests.shape[1]):
                    try:
                        q_name = str(quest_names.iloc[c])
                        
                        # Überspringe leere Spalten
                        if q_name == "nan" or q_name.strip() == "":
                            continue
                            
                        # Status prüfen
                        val = str(student_quest_row.iloc[c])
                        
                        if "abgeschlossen" in val.lower() and "nicht" not in val.lower():
                            found_quests = True
                            
                            # XP holen - sicher!
                            try:
                                raw_xp = str(quest_xps.iloc[c])
                                xp_val = int(float(raw_xp))
                            except:
                                xp_val = "?"
                            
                            with cols[col_counter % 3]:
                                st.success(f"✅ {q_name}\n\n**+{xp_val} XP**")
                            col_counter += 1
                            
                    except Exception:
                        # Falls eine einzelne Spalte Fehler wirft (z.B. Fehler 9), ignorieren wir sie einfach
                        continue
                
                if not found_quests:
                    st.info("Noch keine Quests abgeschlossen.")
            else:
                st.warning("Keine Quests für diesen Namen gefunden.")

        else:
            st.error(f"Gamertag '{gamertag_input}' nicht gefunden.")

    else:
        st.write("Bitte Gamertag eingeben.")

except Exception as e:
    st.error("Ein kritischer Fehler ist aufgetreten:")
    st.code(str(e))
