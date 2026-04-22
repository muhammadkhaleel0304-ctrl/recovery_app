import streamlit as st
import qrcode
from io import BytesIO

st.title("CNIC QR Generator")

cnic = st.text_input("Enter CNIC")

if st.button("Generate QR"):
    if cnic:

        # IMPORTANT: ensure full string goes inside QR
        data = str(cnic).strip()

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format="PNG")

        img_bytes = buf.getvalue()

        st.image(img_bytes)

        st.download_button(
            "Download QR",
            data=img_bytes,
            file_name="cnic.png",
            mime="image/png"
        )
    else:
        st.warning("Enter CNIC first")
