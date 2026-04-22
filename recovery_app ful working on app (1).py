import streamlit as st
import qrcode
from io import BytesIO

st.set_page_config(page_title="QR Generator", page_icon="🔗")

st.title("🔗 Free QR Code Generator")

text = st.text_input("Enter URL or Text")

if st.button("Generate QR Code"):
    if text.strip():

        # Generate QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes ONLY (IMPORTANT FIX)
        buf = BytesIO()
        img.save(buf, format="PNG")
        byte_img = buf.getvalue()

        # Show image (SAFE METHOD)
        st.image(byte_img, caption="Your QR Code", use_container_width=True)

        # Download button
        st.download_button(
            "⬇ Download QR Code",
            data=byte_img,
            file_name="qrcode.png",
            mime="image/png"
        )

    else:
        st.warning("Please enter text or URL")
