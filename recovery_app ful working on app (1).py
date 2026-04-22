import streamlit as st
import qrcode
from PIL import Image

st.set_page_config(page_title="QR Generator", page_icon="🔗")

st.title("🔗 Free QR Code Generator")

text = st.text_input("Enter URL or Text")

if st.button("Generate QR Code"):
    if text.strip():

        # QR configuration (IMPORTANT FIX)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        # Show image (SAFE)
        st.image(img, caption="Your QR Code", use_container_width=True)

        # Download
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        st.download_button(
            "⬇ Download QR Code",
            data=buf.getvalue(),
            file_name="qrcode.png",
            mime="image/png"
        )

    else:
        st.warning("Please enter text or URL")
