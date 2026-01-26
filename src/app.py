import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from pathlib import Path
import uuid

st.set_page_config(page_title="OCR stare dokumenty — MVP", layout="wide")
st.title("OCR stare dokumenty — MVP (annotator)")

uploaded = st.file_uploader("Wgraj skan (PNG/JPG)", type=["png", "jpg", "jpeg"])

if uploaded:
    img = Image.open(uploaded).convert("RGB")
    w, h = img.size

    debug_dir = Path("logs/debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.subheader("Zaznacz obszary (ramki)")
        canvas = st_canvas(
            fill_color="rgba(255, 165, 0, 0.2)",
            stroke_width=2,
            stroke_color="#ff4b4b",
            background_image=img,
            update_streamlit=True,
            height=min(900, h),
            width=min(1200, w),
            drawing_mode="rect",
            key="canvas",
        )

    with col2:
        st.subheader("Cropy (debug)")

        if canvas.json_data and "objects" in canvas.json_data:
            rects = [
                obj for obj in canvas.json_data["objects"]
                if obj.get("type") == "rect"
            ]

            st.write(f"Liczba ramek: {len(rects)}")

            for i, r in enumerate(rects, start=1):
                left = int(r.get("left", 0))
                top = int(r.get("top", 0))
                right = int(left + r.get("width", 0))
                bottom = int(top + r.get("height", 0))

                # Minimalna walidacja granic obrazu
                left = max(0, min(left, w))
                top = max(0, min(top, h))
                right = max(0, min(right, w))
                bottom = max(0, min(bottom, h))

                if right <= left or bottom <= top:
                    st.warning(f"Crop {i}: zbyt mały / niepoprawny (pomijam).")
                    continue

                crop = img.crop((left, top, right, bottom))

                fname = debug_dir / f"crop_{i}_{uuid.uuid4().hex[:8]}.png"
                crop.save(fname)

                st.markdown(f"**Crop {i}**")
                st.image(crop, width='stretch')
                st.caption(str(fname))
        else:
            st.info("Dodaj prostokąty po lewej stronie.")
else:
    st.info("Wgraj plik, żeby rozpocząć.")

