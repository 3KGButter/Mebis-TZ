import streamlit as st
import random
import pandas as pd

# Titel und Konfiguration
st.set_page_config(page_title="Mebis Tool", page_icon="🏫")

st.title("🏫 Mebis Schülerkürzel Generator")
st.write("Generiere Benutzerkürzel und Passwörter ohne Installation.")

# --- Hilfsfunktionen ---

def clean_string(text):
    """Ersetzt Umlaute und entfernt Sonderzeichen"""
    umlaut_map = {
        'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
        'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue'
    }
    text = text.strip()
    for k, v in umlaut_map.items():
        text = text.replace(k, v)
    # Nur Buchstaben und Zahlen behalten
    return "".join(c for c in text if c.isalnum())

def generate_password(length=8):
    chars = "abcdefghjkmnpqrstuvwxyz23456789!@#"
    return "".join(random.choice(chars) for _ in range(length))

def generate_data(names_text, style):
    data = []
    lines = names_text.split('\n')
    
    for line in lines:
        full_name = line.strip()
        if not full_name:
            continue
            
        parts = full_name.split()
        if len(parts) == 1:
            last_name = parts[0]
            first_name = "?"
        else:
            last_name = parts[-1]
            first_name = " ".join(parts[:-1])
            
        # Bereinigen für Kürzel
        clean_fn = clean_string(first_name.lower())
        clean_ln = clean_string(last_name.lower())
        
        kuerzel = ""
        
        if style == "Standard (MusMax)":
            # Erste 3 Buchstaben Nachname + Erste 3 Vorname
            # Auffüllen mit X falls zu kurz, dann abschneiden
            l_part = (clean_string(last_name) + "XXX")[:3]
            f_part = (clean_string(first_name) + "XXX")[:3]
            # Großschreibung der Teile (z.B. MusMax)
            kuerzel = l_part.capitalize() + f_part.capitalize()
            
        elif style == "Initialen (MM)":
            kuerzel = (first_name[0] + last_name[0]).upper()
            
        elif style == "Punkt (max.mustermann)":
            kuerzel = f"{clean_fn}.{clean_ln}"
            
        password = generate_password()
        
        data.append({
            "Name": full_name,
            "Benutzer/Kürzel": kuerzel,
            "Passwort": password
        })
        
    return pd.DataFrame(data)

# --- Benutzeroberfläche ---

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Einstellungen")
    style_option = st.selectbox(
        "Kürzel-Stil wählen",
        ("Standard (MusMax)", "Initialen (MM)", "Punkt (max.mustermann)")
    )
    
    st.info("ℹ️ Hinweis: Wenn du diese App online stellst, achte auf den Datenschutz (keine echten Namen auf öffentliche Server laden).")

with col2:
    st.subheader("Namen eingeben")
    input_text = st.text_area(
        "Ein Name pro Zeile (Vorname Nachname)", 
        height=200, 
        placeholder="Max Mustermann\nLisa Müller"
    )

    if st.button("Liste generieren", type="primary"):
        if input_text:
            df = generate_data(input_text, style_option)
            
            st.success(f"{len(df)} Datensätze generiert!")
            
            # Tabelle anzeigen
            st.dataframe(df, use_container_width=True)
            
            # CSV Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Tabelle als CSV herunterladen",
                data=csv,
                file_name='mebis_liste.csv',
                mime='text/csv',
            )
        else:
            st.warning("Bitte gib zuerst Namen ein.")
