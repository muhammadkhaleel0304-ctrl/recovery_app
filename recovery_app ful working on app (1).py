<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QR Code Generator</title>

<script src="https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js"></script>

<style>
body {
    font-family: Arial;
    background: linear-gradient(135deg,#667eea,#764ba2);
    color: white;
    text-align: center;
    padding-top: 80px;
}

.container {
    background: white;
    color: black;
    padding: 30px;
    border-radius: 15px;
    width: 320px;
    margin: auto;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
}

input {
    width: 100%;
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #ccc;
}

button {
    margin-top: 10px;
    padding: 10px;
    width: 100%;
    border: none;
    border-radius: 8px;
    background: #667eea;
    color: white;
    font-size: 16px;
    cursor: pointer;
}

button:hover {
    background: #5a67d8;
}

canvas {
    margin-top: 20px;
}

.download {
    background: green;
}
</style>

</head>

<body>

<div class="container">
    <h2>QR Code Generator</h2>

    <input type="text" id="text" placeholder="Enter link or text">

    <button onclick="generateQR()">Generate QR</button>
    <button class="download" onclick="downloadQR()">Download QR</button>

    <canvas id="qrcode"></canvas>
</div>

<script>
function generateQR() {
    let text = document.getElementById("text").value;
    let canvas = document.getElementById("qrcode");

    if(text === ""){
        alert("Please enter text or URL");
        return;
    }

    QRCode.toCanvas(canvas, text, function (error) {
        if (error) console.error(error);
    });
}

function downloadQR() {
    let canvas = document.getElementById("qrcode");
    let link = document.createElement('a');
    link.download = "qrcode.png";
    link.href = canvas.toDataURL();
    link.click();
}
</script>

</body>
</html>
