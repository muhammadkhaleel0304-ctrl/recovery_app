import streamlit as st
import qrcode
from PIL import Image
from io import BytesIO

st.set_page_config(page_title="QR Code Generator", page_icon="🔗")

st.title("🔗 Free QR Code Generator")

text = st.text_input("Enter URL or Text")

if st.button("Generate QR Code"):
    if text:
        # QR generate
        qr = qrcode.make(text)

        # Convert to proper PIL image
        img = qr.convert("RGB")

        # Show image safely
        st.image(img, caption="Your QR Code", use_container_width=True)

        # Download
        buffer = BytesIO()
        img.save(buffer, format="PNG")

        st.download_button(
            "⬇ Download QR Code",
            data=buffer.getvalue(),
            file_name="qrcode.png",
            mime="image/png"
        )
    else:
        st.warning("Please enter text or URL")
