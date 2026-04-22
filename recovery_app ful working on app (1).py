import streamlit as st
import qrcode
from io import BytesIO

st.set_page_config(page_title="QR Code Generator", page_icon="🔗")

# Header
st.markdown("<h1 style='text-align:center;'>🔗 Free QR Code Generator</h1>", unsafe_allow_html=True)

# Input box
text = st.text_input("Enter URL or Text")

# Button
if st.button("Generate QR Code"):
    if text:
        qr = qrcode.make(text)

        st.image(qr, caption="Your QR Code", use_column_width=True)

        # Download
        buffer = BytesIO()
        qr.save(buffer, format="PNG")

        st.download_button(
            label="⬇ Download QR Code",
            data=buffer.getvalue(),
            file_name="qrcode.png",
            mime="image/png"
        )
    else:
        st.warning("⚠ Please enter text or URL")
