from flask import Flask, render_template_string, jsonify, request, session, redirect, url_for
import os

app = Flask(__name__)
app.secret_key = 'sky_switch_secret_key_123'

# --- ডেটা স্টোরেজ ---
command_queue = []
devices = {str(i): {"name": f"Switch {i-1}", "state": 0} for i in range(2, 14)}
online_users = {}

# --- ১. কমন CSS এবং স্টাইল (Premium UI) ---
STYLE = """
<style>
    :root {
        --neon-blue: #00d2ff;
        --neon-green: #39ff14;
        --neon-pink: #f400ff;
        --bg-dark: #020617;
        --glass: rgba(15, 23, 42, 0.7);
        --border: rgba(0, 210, 255, 0.3);
    }

    * { box-sizing: border-box; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
    
    body, html {
        margin: 0; padding: 0; min-height: 100vh;
        background: var(--bg-dark);
        color: white; font-family: 'Rajdhani', sans-serif;
        overflow-x: hidden;
    }

    .bg-vibe {
        position: fixed; inset: 0;
        background: radial-gradient(circle at 50% 50%, #1e293b 0%, #020617 100%);
        z-index: -2;
    }

    /* --- ৩ডি কার্ড এবং অ্যানিমেশন --- */
    .card {
        background: var(--glass);
        border: 1px solid var(--border);
        border-radius: 20px;
        padding: 30px;
        backdrop-filter: blur(15px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        transform-style: preserve-3d;
        perspective: 1000px;
        position: relative;
    }

    .card:hover {
        transform: translateY(-10px) rotateX(5deg) rotateY(5deg);
        border-color: var(--neon-blue);
        box-shadow: 0 0 30px rgba(0, 210, 255, 0.4);
    }

    .active-card {
        border-color: var(--neon-green) !important;
        box-shadow: 0 0 40px rgba(57, 255, 20, 0.2) !important;
    }

    /* --- এনিমেশন কীফ্রেম --- */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    @keyframes glow {
        0%, 100% { text-shadow: 0 0 10px var(--neon-blue); }
        50% { text-shadow: 0 0 25px var(--neon-blue), 0 0 40px var(--neon-blue); }
    }

    .animate-text {
        font-family: 'Orbitron';
        animation: glow 2s infinite ease-in-out;
    }
</style>
"""

# --- ২. লগইন পেজ ---
LOGIN_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SkySwitch | Gateway</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500&display=swap" rel="stylesheet">
    {STYLE}
</head>
<body>
    <div class="bg-vibe"></div>
    <div style="display: flex; justify-content: center; align-items: center; height: 100vh;">
        <div class="card" style="width: 350px; text-align: center; animation: fadeInUp 1s forwards;">
            <h1 class="animate-text" style="color: var(--neon-blue); margin-bottom: 30px;">SKYSWITCH</h1>
            <form method="POST" action="/login">
                <input type="text" name="username" placeholder="CODENAME" required 
                       style="width:100%; padding:15px; margin-bottom:20px; background:transparent; border:1px solid var(--border); color:white; border-radius:10px;">
                <input type="password" name="password" placeholder="ACCESS KEY" required 
                       style="width:100%; padding:15px; margin-bottom:25px; background:transparent; border:1px solid var(--border); color:white; border-radius:10px;">
                <button type="submit" style="width:100%; padding:15px; background:var(--neon-blue); color:black; border:none; border-radius:10px; font-weight:bold; cursor:pointer;">INITIALIZE SYSTEM</button>
            </form>
            {{% if error %}} <p style="color:red; margin-top:15px;">{{{{ error }}}}</p> {{% endif %}}
        </div>
    </div>
</body>
</html>
"""

# --- ৩. মেইন সুইচ হাব (With 3D & Startup) ---
HUB_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SkySwitch Hub</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Rajdhani:wght@500;700&display=swap" rel="stylesheet">
    {STYLE}
</head>
<body>
    <div class="bg-vibe"></div>
    <audio id="startupSound" src="/static/startup.mp3" preload="auto"></audio>

    <div id="loader" style="position:fixed; inset:0; background:black; z-index:999; display:flex; flex-direction:column; justify-content:center; align-items:center;">
        <h1 id="loadText" class="animate-text" style="font-size:3rem; color:var(--neon-blue); letter-spacing:10px;">SKYSWITCH</h1>
        <div style="width:200px; height:2px; background:var(--border); margin-top:20px;">
            <div id="bar" style="width:0%; height:100%; background:var(--neon-blue); box-shadow:0 0 15px var(--neon-blue);"></div>
        </div>
    </div>

    <div id="content" style="display:none; padding: 20px;">
        <header style="text-align:center; padding: 40px 0;">
            <h1 class="animate-text" style="margin:0; font-size: 2.5rem; letter-spacing: 5px;">SYSTEM ONLINE</h1>
            <p style="color: var(--neon-blue);">USER: {{{{ user }}}}</p>
        </header>

        <div id="deviceGrid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap:25px; max-width:1200px; margin: 0 auto;">
            </div>
    </div>

    <script>
        window.onload = () => {{
            let bar = document.getElementById('bar');
            let progress = 0;
            let interval = setInterval(() => {{
                progress += 5;
                bar.style.width = progress + "%";
                if(progress >= 100) {{
                    clearInterval(interval);
                    document.getElementById('startupSound').play().catch(e => console.log("Sound error"));
                    document.getElementById('loader').style.opacity = '0';
                    setTimeout(() => {{
                        document.getElementById('loader').style.display = 'none';
                        document.getElementById('content').style.display = 'block';
                        loadDevices();
                    }}, 800);
                }}
            }}, 50);
        }};

        async function loadDevices() {{
            const res = await fetch('/status');
            if (res.status === 401) window.location.href = "/";
            const devices = await res.json();
            const grid = document.getElementById('deviceGrid');
            grid.innerHTML = '';

            for (const [pin, info] of Object.entries(devices)) {{
                const active = info.state == 1;
                grid.innerHTML += `
                    <div class="card ${{active ? 'active-card' : ''}}">
                        <div style="font-size: 40px; margin-bottom: 20px; color: ${{active ? 'var(--neon-green)' : '#334155'}}">
                            <i class="fas fa-lightbulb"></i>
                        </div>
                        <input type="text" value="${{info.name}}" onchange="rename('${{pin}}', this.value)" 
                               style="background:transparent; border:none; color:white; font-family:'Orbitron'; text-align:center; width:100%; font-size:1.2rem; margin-bottom:20px;">
                        <button onclick="toggle('${{pin}}', ${{active ? 0 : 1}})" 
                                style="width:100%; padding:12px; border-radius:10px; cursor:pointer; font-family:'Orbitron'; 
                                background: ${{active ? 'var(--neon-green)' : 'transparent'}}; 
                                color: ${{active ? 'black' : 'var(--neon-blue)'}}; 
                                border: 1px solid ${{active ? 'var(--neon-green)' : 'var(--border)'}}">
                            ${{active ? 'POWER ACTIVE' : 'ENGAGE'}}
                        </button>
                    </div>
                `;
            }}
        }}

        function toggle(pin, state) {{ fetch(`/send/${{pin}}/${{state}}`).then(() => loadDevices()); }}
        function rename(pin, name) {{ fetch(`/rename/${{pin}}/${{name}}`); }}
        setInterval(loadDevices, 5000);
    </script>
</body>
</html>
"""

# --- ৪. ড্যাশবোর্ড (পাসওয়ার্ড প্রোটেকটেড) ---
DASHBOARD_PAGE = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard</title>
    {STYLE}
</head>
<body style="padding:40px;">
    <div class="bg-vibe"></div>
    <div id="admin-lock" style="position:fixed; inset:0; background:black; z-index:1000; display:flex; justify-content:center; align-items:center;">
        <div class="card" style="text-align:center;">
            <h2>ADMIN ACCESS</h2>
            <input type="password" id="adminPass" placeholder="ENTER KEY">
            <button onclick="checkAdmin()" style="margin-top:20px; padding:10px 20px;">VERIFY</button>
        </div>
    </div>

    <div id="admin-content" style="display:none;">
        <h1 class="animate-text">ACTIVE NODES</h1>
        <div class="card" style="margin-top:30px;">
            <table style="width:100%; text-align:left;">
                <tr style="color:var(--neon-blue)"><th>IP ADDRESS</th><th>PILOT NAME</th><th>ACTION</th></tr>
                {{% for ip, name in users.items() %}}
                <tr>
                    <td>{{{{ ip }}}}</td>
                    <td>{{{{ name }}}}</td>
                    <td><a href="/kick/{{{{ ip }}}}" style="color:red; text-decoration:none;">[ TERMINATE ]</a></td>
                </tr>
                {{% endfor %}}
            </table>
        </div>
    </div>

    <script>
        function checkAdmin() {{
            if(document.getElementById('adminPass').value === '11') {{
                document.getElementById('admin-lock').style.display = 'none';
                document.getElementById('admin-content').style.display = 'block';
            }} else {{
                alert('ACCESS DENIED');
            }}
        }}
    </script>
</body>
</html>
"""

# --- Flask Logic (Backend remains same) ---

@app.route('/')
def index():
    user_ip = request.remote_addr
    if 'user' in session and user_ip in online_users:
        return redirect(url_for('hub'))
    return render_template_string(LOGIN_PAGE)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    if password == '123':
        session['user'] = username
        online_users[request.remote_addr] = username
        return redirect(url_for('hub'))
    return render_template_string(LOGIN_PAGE, error="INVALID AUTHENTICATION")

@app.route('/hub')
def hub():
    user_ip = request.remote_addr
    if user_ip not in online_users: return redirect(url_for('index'))
    return render_template_string(HUB_PAGE, user=online_users[user_ip])

@app.route('/dashboard')
def dashboard():
    return render_template_string(DASHBOARD_PAGE, users=online_users)

@app.route('/kick/<ip>')
def kick_user(ip):
    if ip in online_users: del online_users[ip]
    return redirect(url_for('dashboard'))

@app.route('/status')
def get_status():
    if request.remote_addr not in online_users: return jsonify({"err": "Unauthorized"}), 401
    return jsonify(devices)

@app.route('/send/<pin>/<state>')
def send_command(pin, state):
    if request.remote_addr not in online_users: return jsonify({"err": "Unauthorized"}), 401
    devices[pin]['state'] = int(state)
    command_queue.append(f"{pin}:{state}")
    return jsonify({"status": "ok"})

@app.route('/rename/<pin>/<name>')
def rename_device(pin, name):
    if request.remote_addr not in online_users: return jsonify({"err": "Unauthorized"}), 401
    devices[pin]['name'] = name
    return jsonify({"status": "ok"})

@app.route('/get')
def get_command():
    if command_queue: return jsonify({"cmd": command_queue.pop(0)})
    return jsonify({"cmd": "none"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)