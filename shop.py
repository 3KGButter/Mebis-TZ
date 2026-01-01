import streamlit as st
import json
import os
import io
from PIL import Image, ImageDraw


def load_items(path='data/shop_items.json'):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    # Fallback demo items
    return [
        {"id": "hat", "name": "Roter Hut", "price": 30, "color": "#c0392b", "layer": "hat"},
        {"id": "cape", "name": "Blauer Umhang", "price": 50, "color": "#2980b9", "layer": "cape"},
        {"id": "sword", "name": "Bronzeschwert", "price": 70, "color": "#b8860b", "layer": "sword"}
    ]


def compose_avatar(inventory):
    size = (128, 128)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base face
    draw.ellipse((32, 16, 96, 80), fill=(255, 224, 189, 255))
    # Body
    draw.rectangle((44, 76, 84, 110), fill=(80, 40, 20, 255))

    # Simple layer rendering based on item id
    for it in inventory:
        iid = it.get('id')
        color = it.get('color', '#000000')
        if iid == 'hat':
            draw.rectangle((28, 0, 100, 28), fill=color)
        elif iid == 'cape':
            draw.polygon([(40, 110), (88, 110), (128, 80), (0, 80)], fill=color)
        elif iid == 'sword':
            draw.rectangle((88, 40, 104, 100), fill=color)

    return img


def show_shop(player_tag, stats):
    st.sidebar.info(f"Shop geöffnet für: {player_tag}")

    if 'gold' not in st.session_state:
        st.session_state['gold'] = 100
    if 'inventory' not in st.session_state:
        st.session_state['inventory'] = []

    items = load_items()

    st.header("🛒 Shop (Demo)")
    st.write(f"Gold: {st.session_state['gold']}")

    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            st.markdown(f"**{item['name']}**\nPreis: {item['price']} Gold")
            if st.button(f"Kaufen: {item['name']}", key=f"buy_{item['id']}"):
                if st.session_state['gold'] >= item['price']:
                    st.session_state['gold'] -= item['price']
                    if not any(i.get('id') == item['id'] for i in st.session_state['inventory']):
                        st.session_state['inventory'].append(item)
                        st.success(f"{item['name']} gekauft!")
                    else:
                        st.info("Bereits im Inventar.")
                else:
                    st.error("Nicht genug Gold.")

    st.subheader("Avatar Vorschau")
    avatar = compose_avatar(st.session_state['inventory'])
    buf = io.BytesIO()
    avatar.save(buf, format='PNG')
    buf.seek(0)
    st.image(buf)
