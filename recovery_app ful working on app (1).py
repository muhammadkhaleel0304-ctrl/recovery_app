import streamlit as st
import qrcode
from io import BytesIO

st.title("CNIC QR Generator")

cnic = st.text_input("Enter CNIC (with or without dashes)")

if st.button("Generate QR"):
    if cnic.strip():

        # REMOVE DASHES (IMPORTANT FIX)
        clean_cnic = cnic.replace("-", "").strip()

        qr = qrcode.make(clean_cnic)

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
        st.warning("Enter CNIC")
