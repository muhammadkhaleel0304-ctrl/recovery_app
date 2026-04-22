import streamlit as st
import qrcode
from io import BytesIO

st.title("QR Generator")

text = st.text_input("Enter text")

if st.button("Generate"):
    if text:

        qr = qrcode.QRCode(
            box_size=10,
            border=4
        )

        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes (MOST COMPATIBLE METHOD)
        buf = BytesIO()
        img.save(buf, format="PNG")
        byte_img = buf.getvalue()

        # ✅ SAFE DISPLAY (no st.image PIL issue)
        st.image(byte_img)

        st.download_button(
            "Download QR",
            data=byte_img,
            file_name="qr.png",
            mime="image/png"
        )
