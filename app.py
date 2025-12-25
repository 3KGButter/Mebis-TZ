import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="TZ Gamification", page_icon="📐")
st.title("📐 Technisches Zeichnen - XP Dashboard")

# 1. Verbindung zu Google Sheets herstellen
# Ersetze den Link unten mit DEINEM Link zur Tabelle "XP Rechner"
url = "https://docs.google.com/spreadsheets/d/1xfAbOwU6DrbHgZX5AexEl3pedV9vTxyTFbXrIU06O7Q/edit?gid=1717673199#gid=1717673199"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Wir laden das Blatt "XP Rechner 3.0" (oder wie dein Hauptblatt heißt)
    df = conn.read(spreadsheet=url, worksheet="XP Rechner 3.0")
    
    st.success("✅ Verbindung zur Datenbank erfolgreich!")
    
    # 2. Login Bereich
    gamertag_input = st.text_input("Gib deinen Gamertag ein:")

    if gamertag_input:
        # Wir suchen den Schüler im DataFrame
        # Wir gehen davon aus, dass die Spalte in Google Sheets "Gamertag" heißt
        user_data = df[df['Gamertag'] == gamertag_input]

        if not user_data.empty:
            st.balloons() # Konfetti zur Begrüßung!
            
            # Daten aus der Zeile holen (iloc[0] nimmt den ersten Treffer)
            # Pass die Spaltennamen an exakt so an, wie sie in deiner Tabelle stehen!
            level = user_data.iloc[0]['Level'] 
            xp = user_data.iloc[0]['XP']
            rank = user_data.iloc[0]['Rang'] # Falls du eine Rang-Spalte hast

            # Metriken anzeigen
            col1, col2, col3 = st.columns(3)
            col1.metric("Dein Rang", rank)
            col2.metric("Level", level)
            col3.metric("XP Total", xp)
            
            st.divider()
            st.subheader("🛒 Shop")
            st.info("Hier kannst du bald deine XP/Coins ausgeben!")
            
        else:
            st.error("Gamertag nicht gefunden. Tippfehler?")
            
except Exception as e:
    st.error(f"Verbindungsfehler: {e}")
    st.info("Tipp: Hast du die Tabelle für 'streamlit-bot@...' freigegeben und den Link im Code eingetragen?")
