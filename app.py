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
    if xp_needed_for_level <= 0:
        return 1.0, "Level Up!"
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
    df_xp = conn.read(spreadsheet=url, worksheet=blatt_mapping, header=1, ttl=0)
except Exception as e:
    st.error(f"Fehler beim Laden von '{blatt_mapping}': {e}")
    st.stop()

st.info("Logge dich ein, um deinen Status zu sehen.")
gamertag_input = st.text_input("Dein Gamertag:", placeholder="z.B. JoFel")

if gamertag_input:
    input_clean = gamertag_input.strip().lower()

    # --- SCHRITT 1: GAMERTAG SUCHEN (NUR BEREICH L bis P) ---
    found_row_index = -1
    best_stats = None

    target_col_start = 11
    target_col_end = min(17, len(df_xp.columns))

    for col_idx in range(target_col_start, target_col_end):
        col_header = str(df_xp.columns[col_idx]).strip()
        if "Gamertag" in col_header:
            col_data = df_xp.iloc[:, col_idx].astype(str).str.strip().str.lower()
            matches = col_data[col_data == input_clean].index
            if not matches.empty:
                found_row_index = matches[0]
                row = df_xp.iloc[found_row_index]
                if col_idx + 2 < len(df_xp.columns):
                    raw_xp = row.iloc[col_idx + 1]
                    raw_level = row.iloc[col_idx + 2]
                    raw_stufe = ""
                    if col_idx + 3 < len(df_xp.columns):
                        raw_stufe = str(row.iloc[col_idx + 3])
                    check_str = f"{raw_level} {raw_stufe}".lower()
                    is_game_over = "†" in check_str or "game" in check_str or "over" in check_str
                    try:
                        xp_val = int(float(str(raw_xp).replace(',', '.')))
                    except:
                        xp_val = 0
                    best_stats = {
                        "xp": xp_val,
                        "level": raw_level,
                        "is_game_over": is_game_over
                    }
                break

    if best_stats and found_row_index != -1:
        # --- SCHRITT 2: ECHTEN NAMEN HOLEN ---
        try:
            real_name_found = str(df_xp.iloc[found_row_index, 3])
        except:
            real_name_found = "Unbekannt"

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

        # --- QUESTS LADEN ---
        try:
            df_quests = conn.read(spreadsheet=url, worksheet=blatt_quests, header=None, ttl=0)
            st.write("✅ Questbuch geladen")
        except Exception as e:
            st.error(f"❌ Fehler beim Laden von Questbuch: {e}")
            st.stop()

        st.write("---")
        st.write(f"📊 **Questbuch Shape**: {df_quests.shape[0]} Zeilen × {df_quests.shape[1]} Spalten")
        st.write(f"📋 **Zeile 2 (Index 1) - Quest-Namen (erste 15 Spalten)**:")
        st.write(list(df_quests.iloc[1, 0:15]))
        st.write(f"💎 **Zeile 5 (Index 4) - XP-Werte (erste 15 Spalten)**:")
        st.write(list(df_quests.iloc[4, 0:15]))
        st.write("---")

        quest_names = df_quests.iloc[1]
        quest_xps = df_quests.iloc[4]

        # --- SCHÜLERZEILE SUCHEN ---
        q_idx = -1
        search_name_clean = real_name_found.strip().lower()
        search_tokens = [t for t in search_name_clean.split(" ") if len(t) > 1]
        if not search_tokens:
            search_tokens = [search_name_clean]

        st.write(f"🔍 **Suche nach Schüler**: '{real_name_found}' (clean: '{search_name_clean}')")
        st.write(f"🔑 **Tokens**: {search_tokens}")

        for idx in range(6, len(df_quests)):  # Schülerdaten ab Zeile 7 (Index 6)
            row = df_quests.iloc[idx]
            row_txt = " ".join([str(x) for x in row.values[:4]]).lower()
            match_all = True
            for token in search_tokens:
                if token not in row_txt:
                    match_all = False
                    break
            if match_all:
                q_idx = idx
                st.write(f"✅ **Schüler gefunden in Zeile {idx}**: {row.iloc[0:3].tolist()}")
                break

        if q_idx == -1:
            st.error(f"❌ Schüler '{real_name_found}' nicht gefunden!")
            st.write("📋 **Erste 15 Namen im Questbuch:**")
            for i in range(6, min(21, len(df_quests))):
                st.write(f"Zeile {i}: {df_quests.iloc[i, 0:3].tolist()}")
        else:
            student_quest_row = df_quests.iloc[q_idx]

            st.write(f"📍 **Schüler-Zeile**: {q_idx}")
            st.write(f"👤 **Name**: {student_quest_row.iloc[0]}")
            st.write(f"✉️  **Email**: {student_quest_row.iloc[1]}")
            st.write(f"🏫 **Klasse/Gesamt**: {student_quest_row.iloc[2]}")
            st.write("---")

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
            quest_count = 0

            # WICHTIG: Quests liegen in den GERADEN Spalten ab Index 2 (C),
            # also 2,4,6,8,... (Grundregeln, Linienarten, Feedback, ...)
            start_col = 2

            for c in range(start_col, df_quests.shape[1], 2):
                try:
                    q_name = str(quest_names.iloc[c]).strip()
                    if not q_name or q_name.lower() == "nan" or "unnamed" in q_name.lower():
                        continue

                    q_check = q_name.lower()
                    if "summe" in q_check or "game" in q_check or "over" in q_check:
                        continue

                    quest_count += 1

                    val = str(student_quest_row.iloc[c]) if c < len(student_quest_row) else ""
                    is_completed = "abgeschlossen" in val.lower() and "nicht" not in val.lower()

                    try:
                        xp_val = int(float(str(quest_xps.iloc[c]).replace(",", ".")))
                    except:
                        xp_val = "?"

                    if quest_count <= 3:
                        st.write(f"Quest {quest_count}: '{q_name}' | Status: '{val}' | Completed: {is_completed} | XP: {xp_val}")

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
                except Exception as e:
                    st.write(f"❌ Fehler bei Spalte {c}: {str(e)}")
                    continue

            st.write(f"📊 **Total Quests gefunden**: {quest_count}")

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
        st.error(f"❌ Gamertag '{gamertag_input}' nicht gefunden.")
