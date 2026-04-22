import streamlit as st
import qrcode
from io import BytesIO

st.set_page_config(page_title="QR Generator", page_icon="🔗")

st.title("🔗 Free QR Code Generator")

text = st.text_input("Enter URL or Text")

if st.button("Generate QR Code"):
    if text.strip():

        # Generate QR
        qr = qrcode.make(text)

        # Convert to bytes (IMPORTANT FIX)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()

        # Show image from bytes (SAFE METHOD)
        st.image(img_bytes, caption="Your QR Code", use_container_width=True)

        # Download button
        st.download_button(
            label="⬇ Download QR Code",
            data=img_bytes,
            file_name="qrcode.png",
            mime="image/png"
        )

    else:
        st.warning("Please enter text or URL")
