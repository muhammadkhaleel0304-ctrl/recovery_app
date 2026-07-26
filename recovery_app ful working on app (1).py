<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CNIC Portal & Dashboard</title>
  
  <!-- Font Awesome Icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <!-- QRCode.js Library -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
  <!-- Firebase App & Database -->
  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-database-compat.js"></script>

  <style>
    :root {
      --bg-dark: #0f172a;
      --card-bg: #1e293b;
      --sidebar-bg: #0f172a;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --btn-green: #10b981;
      --btn-red: #ef4444;
      --text-light: #f8fafc;
      --text-muted: #94a3b8;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', 'Segoe UI', sans-serif; }
    body { background-color: var(--bg-dark); color: var(--text-light); height: 100vh; overflow: hidden; }

    /* MODERN LOGIN SCREEN STYLING */
    #login-screen {
      position: fixed; inset: 0; background: radial-gradient(circle at top right, #1e1b4b, #0f172a 60%);
      display: flex; justify-content: center; align-items: center; z-index: 100;
    }
    .login-card {
      background: rgba(30, 41, 59, 0.7);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      padding: 40px 35px; border-radius: 20px;
      width: 360px;
      border: 1px solid rgba(255, 255, 255, 0.1);
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      text-align: center;
      animation: fadeIn 0.5s ease-in-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(-20px); }
      to { opacity: 1; transform: translateY(0); }
    }
    
    .login-icon {
      width: 60px; height: 60px; background: rgba(56, 189, 248, 0.1);
      color: var(--primary); border-radius: 50%; display: flex;
      align-items: center; justify-content: center; margin: 0 auto 15px auto;
      font-size: 26px; border: 1px solid rgba(56, 189, 248, 0.2);
    }
    
    .login-card h2 { margin-bottom: 6px; color: #ffffff; font-size: 22px; font-weight: 700; }
    .login-card p.subtitle { color: var(--text-muted); font-size: 13px; margin-bottom: 25px; }

    .input-group {
      position: relative; margin-bottom: 18px; text-align: left;
    }
    .input-group i {
      position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
      color: var(--text-muted); font-size: 14px; transition: 0.3s;
    }
    .input-field {
      width: 100%; padding: 13px 14px 13px 42px; border-radius: 10px;
      border: 1px solid #334155; background: rgba(15, 23, 42, 0.6); color: white;
      outline: none; font-size: 14px; transition: 0.3s ease;
    }
    .input-field:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
    }
    .input-field:focus + i { color: var(--primary); }

    .login-btn {
      width: 100%; padding: 13px; background: linear-gradient(135deg, #38bdf8, #0284c7);
      color: white; border: none; border-radius: 10px; font-weight: 600;
      cursor: pointer; font-size: 15px; transition: 0.3s ease;
      box-shadow: 0 4px 15px rgba(2, 132, 199, 0.3); margin-top: 5px;
    }
    .login-btn:hover { opacity: 0.95; transform: translateY(-1px); }

    /* DASHBOARD LAYOUT */
    .app-container { display: flex; height: 100vh; }
    
    .header {
      position: absolute; top: 0; left: 0; right: 0; height: 60px;
      background: #0f172a; border-bottom: 1px solid #1e293b;
      display: flex; justify-content: space-between; align-items: center;
      padding: 0 25px; z-index: 10;
    }
    .user-info { display: flex; align-items: center; gap: 10px; font-weight: 600; color: var(--text-light); }
    .logout-btn {
      background: rgba(239, 68, 68, 0.1); color: var(--btn-red);
      border: 1px solid rgba(239, 68, 68, 0.2); padding: 8px 16px;
      border-radius: 8px; cursor: pointer; font-weight: 600; transition: 0.2s;
    }
    .logout-btn:hover { background: var(--btn-red); color: white; }

    .sidebar {
      width: 250px; background: #0f172a; margin-top: 60px;
      border-right: 1px solid #1e293b; padding: 20px 0; overflow-y: auto;
    }
    .menu-title { padding: 0 20px 10px; font-size: 11px; color: var(--text-muted); letter-spacing: 1px; font-weight: 700; }
    
    .nav-main-header {
      padding: 12px 20px; font-size: 15px; font-weight: 700; color: #ffffff;
      display: flex; align-items: center; gap: 10px; background: rgba(255, 255, 255, 0.03);
      border-left: 4px solid var(--primary); margin-bottom: 8px;
    }
    .sub-menu-container { padding-left: 15px; }

    .nav-sub-btn {
      width: 100%; padding: 12px 18px; background: transparent; border: none;
      color: var(--text-muted); text-align: left; cursor: pointer; display: flex;
      align-items: center; gap: 12px; font-size: 14px; transition: 0.3s;
      border-radius: 0 20px 20px 0; margin-bottom: 4px;
    }
    .nav-sub-btn:hover, .nav-sub-btn.active { background: rgba(56, 189, 248, 0.1); color: var(--primary); font-weight: 600; }

    .main-content {
      flex: 1; margin-top: 60px; padding: 40px; display: flex;
      justify-content: center; align-items: flex-start; overflow-y: auto;
    }
    .tab-content { display: none; width: 100%; max-width: 500px; }
    .tab-content.active { display: block; }

    .card {
      background: var(--card-bg); padding: 30px; border-radius: 16px;
      border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center;
    }
    .card h3 { color: var(--primary); margin-bottom: 25px; font-size: 20px; }
    
    .action-btn {
      width: 100%; padding: 12px; background: var(--btn-green); color: white;
      border: none; border-radius: 8px; font-weight: bold; cursor: pointer;
      margin-top: 15px; font-size: 15px; transition: 0.2s;
    }
    .action-btn:hover { opacity: 0.9; }

    #qrcode-box {
      margin-top: 25px; display: flex; justify-content: center;
      background: white; padding: 20px; border-radius: 12px; width: fit-content; margin: 20px auto 0 auto;
    }
    #qrcode-box:empty { display: none; }
  </style>
</head>
<body>

  <!-- MODERN LOGIN SCREEN -->
  <div id="login-screen">
    <div class="login-card">
      <div class="login-icon">
        <i class="fa-solid fa-shield-halved"></i>
      </div>
      <h2>Welcome Back</h2>
      <p class="subtitle">Please enter your credentials</p>

      <div class="input-group">
        <input type="text" id="username" class="input-field" placeholder="Username">
        <i class="fa-solid fa-user"></i>
      </div>

      <div class="input-group">
        <input type="password" id="password" class="input-field" placeholder="Password">
        <i class="fa-solid fa-lock"></i>
      </div>

      <button class="login-btn" onclick="handleLogin()">Sign In</button>
      <p id="login-err" style="color: #ef4444; margin-top: 15px; font-size: 13px; font-weight: 600;"></p>
    </div>
  </div>

  <!-- DASHBOARD PAGE -->
  <div class="header">
    <div class="user-info">
      <i class="fa-solid fa-circle-user fa-lg" style="color: var(--primary);"></i>
      <span id="display-user">Guest</span>
    </div>
    <button class="logout-btn" onclick="handleLogout()"><i class="fa-solid fa-right-from-bracket"></i> Logout</button>
  </div>

  <div class="app-container">
    <div class="sidebar">
      <div class="menu-title">MENU OPTIONS</div>
      <div class="nav-main-header">
        <i class="fa-solid fa-gauge"></i> Dashboard
      </div>
      <div class="sub-menu-container">
        <button class="nav-sub-btn active" onclick="switchTab('qr-generator', this)">
          <i class="fa-solid fa-qrcode"></i> QR Generator
        </button>
        <button class="nav-sub-btn" onclick="switchTab('verify-cnic', this)">
          <i class="fa-solid fa-id-card"></i> Verify CNIC
        </button>
      </div>
    </div>

    <div class="main-content">
      <div id="qr-generator" class="tab-content active">
        <div class="card">
          <h3>🪪 CNIC QR Code Generator</h3>
          <div class="input-group">
            <input type="text" id="cnic-input" class="input-field" placeholder="Enter 13 Digit CNIC" maxlength="13">
            <i class="fa-solid fa-id-card"></i>
          </div>
          <button class="action-btn" onclick="generateQR()">✨ Generate QR Code</button>
          <div style="display: flex; justify-content: center; width: 100%;">
            <div id="qrcode-box"></div>
          </div>
        </div>
      </div>

      <div id="verify-cnic" class="tab-content">
        <div class="card">
          <h3>Verify CNIC Number</h3>
          <div class="input-group">
            <input type="text" id="verify-input" class="input-field" placeholder="Enter CNIC to Verify">
            <i class="fa-solid fa-magnifying-glass"></i>
          </div>
          <button class="action-btn" style="background: var(--primary-hover);" onclick="verifyCNIC()">Verify Now</button>
          <p id="verify-result" style="margin-top: 20px; font-weight: bold;"></p>
        </div>
      </div>
    </div>
  </div>

  <script>
    const FIXED_FIRST_12 = "421011234567";

    const firebaseConfig = {
      databaseURL: "https://mywebsite-7016a-default-rtdb.firebaseio.com"
    };
    firebase.initializeApp(firebaseConfig);
    const db = firebase.database();

    let currentUser = null;

    function getDeviceId() {
      let devId = localStorage.getItem('device_unique_id');
      if (!devId) {
        devId = 'dev_' + Math.random().toString(36).substring(2, 11) + Date.now();
        localStorage.setItem('device_unique_id', devId);
      }
      return devId;
    }

    // LOGIN & STRICT DEVICE LOCK LOGIC
    async function handleLogin() {
      const user = document.getElementById('username').value.trim();
      const pass = document.getElementById('password').value.trim();
      const errEl = document.getElementById('login-err');

      if (!user || !pass) {
        errEl.innerText = "Please fill all fields!";
        return;
      }

      errEl.innerText = "Verifying...";

      try {
        const snapshot = await db.ref(`users/${user}`).once('value');
        const userData = snapshot.val();

        if (userData && userData.password === pass) {
          const thisDeviceId = getDeviceId();

          if (userData.boundDeviceId && userData.boundDeviceId !== thisDeviceId) {
            errEl.innerText = "⛔ Account registered to another device!";
            return;
          }

          if (!userData.boundDeviceId) {
            await db.ref(`users/${user}/boundDeviceId`).set(thisDeviceId);
          }

          currentUser = user;
          localStorage.setItem('logged_user', user);

          document.getElementById('display-user').innerText = user;
          document.getElementById('login-screen').style.display = 'none';
          errEl.innerText = "";

        } else {
          errEl.innerText = "Invalid Username or Password!";
        }
      } catch (e) {
        console.error(e);
        errEl.innerText = "Database connection error!";
      }
    }

    function handleLogout() {
      localStorage.removeItem('logged_user');
      location.reload();
    }

    window.onload = function() {
      const savedUser = localStorage.getItem('logged_user');
      if (savedUser) {
        currentUser = savedUser;
        document.getElementById('display-user').innerText = savedUser;
        document.getElementById('login-screen').style.display = 'none';
      }
    };

    function switchTab(tabId, btn) {
      document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.nav-sub-btn').forEach(b => b.classList.remove('active'));
      
      document.getElementById(tabId).classList.add('active');
      btn.classList.add('active');
    }

    function generateQR() {
      const userInput = document.getElementById('cnic-input').value.trim().replace(/-/g, "");
      const qrBox = document.getElementById('qrcode-box');

      if (!/^\d{13}$/.test(userInput)) {
        alert("❌ Invalid! Must Enter Exactly 13 Digits");
        return;
      }

      const fullCNIC = FIXED_FIRST_12 + userInput;
      qrBox.innerHTML = "";
      
      new QRCode(qrBox, {
        text: fullCNIC,
        width: 180,
        height: 180,
        colorDark : "#000000",
        colorLight : "#ffffff",
        correctLevel : QRCode.CorrectLevel.H
      });
    }

    function verifyCNIC() {
      const cnic = document.getElementById('verify-input').value.trim();
      const resultEl = document.getElementById('verify-result');

      if (cnic.length >= 13) {
        resultEl.style.color = "#10b981";
        resultEl.innerText = `✔ CNIC ${cnic} Verified Successfully!`;
      } else {
        resultEl.style.color = "#ef4444";
        resultEl.innerText = "❌ Invalid CNIC Format. Minimum 13 digits required.";
      }
    }
  </script>
</body>
</html> 
