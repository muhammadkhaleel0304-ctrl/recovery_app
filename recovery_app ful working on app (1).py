import streamlit as st
import qrcode
from io import BytesIO

st.title("CNIC QR Generator")

text = st.text_input("Enter CNIC (e.g. 37203-xxxxxxx-x)")

if st.button("Generate QR"):
    if text.strip():

        qr = qrcode.make(text.strip())

        buf = BytesIO()
        qr.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        st.image(img_bytes)

        st.download_button(
            "Download QR",
            data=img_bytes,
            file_name="cnic_qr.png",
            mime="image/png"
        )
    else:
        st.warning("Please enter CNIC")
