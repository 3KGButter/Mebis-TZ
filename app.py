import streamlit as st
import pandas as pd

# 1. Titel und Konfiguration
st.set_page_config(page_title="TZ Gamification", page_icon="📐")

st.title("📐 Technisches Zeichnen - XP Dashboard")

# 2. Begrüßung
st.write("Willkommen im Gamification-Hub der FOS!")

# 3. Kleiner interaktiver Test
st.info("Das ist der erste Prototyp deiner App.")

# Ein simulierter Login (später machen wir das echt)
user_input = st.text_input("Gib deinen Gamertag ein (z.B. ElArg):")

if user_input:
    st.success(f"Hallo {user_input}! Deine Daten werden geladen...")
    
    # Hier simulieren wir Daten - später kommen die aus deiner Google Tabelle
    col1, col2, col3 = st.columns(3)
    col1.metric("Level", "12", "+1")
    col2.metric("XP", "1540", "+220")
    col3.metric("Coins 🪙", "50", "neu")
    
    st.progress(75, text="Fortschritt bis Level 13")

# 4. Der Shop Teaser
st.divider()
st.subheader("🛒 Item Shop (Preview)")
with st.expander("3D Druck Gutschein ansehen"):
    st.write("Kosten: 500 Coins")
    st.button("Kaufen (noch inaktiv)")
