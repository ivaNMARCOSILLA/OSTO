
from flask import Flask, request, jsonify, send_from_directory, Response, session, redirect, render_template_string
from flask_cors import CORS
import yt_dlp
import os, re, json, urllib.parse, functools

app = Flask(__name__, static_folder='.')
CORS(app)

# === CONTRASEÑA OSTO ===
# Cambia esto o pon variable de entorno OSTO_PASSWORD en Render
OSTO_PASSWORD = os.environ.get("OSTO_PASSWORD", "osto8551")
app.secret_key = os.environ.get("SECRET_KEY", "osto-8551-secreto-privado-2026")

LOGIN_HTML = r"""
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OSTO PRIVADO - LOGIN</title>
<style>
:root{--bg:#050507;--card:#15151a;--neon:#ff0033;--border:#22222a;--text:#e8e8e8;--muted:#7a7a85}
*{margin:0;padding:0;box-sizing:border-box}body{background:var(--bg);color:var(--text);font-family:monospace;display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;width:100%;max-width:380px;box-shadow:0 0 40px rgba(255,0,51,.15)}
.logo{font-weight:700;font-size:28px;text-align:center;margin-bottom:6px}.logo span{color:var(--neon)}
.sub{font-size:11px;color:var(--muted);text-align:center;margin-bottom:24px;letter-spacing:1px}
input{width:100%;background:#0f0f12;border:1px solid var(--border);color:#fff;padding:12px 14px;border-radius:10px;outline:none;font-size:15px;font-family:monospace}
input:focus{border-color:var(--neon)}
.btn{width:100%;background:var(--neon);border:0;color:#fff;padding:12px;border-radius:10px;font-weight:700;cursor:pointer;margin-top:12px;letter-spacing:1px}
.error{color:var(--neon);font-size:11px;margin-top:10px;text-align:center}
.hint{color:var(--muted);font-size:10px;text-align:center;margin-top:14px}
</style></head><body>
<div class="box">
<div class="logo">OSTO<span>TUBE</span></div>
<div class="sub">PRIVADO 8551 • ACCESO RESTRINGIDO</div>
<form method="POST" action="/login">
<input type="password" name="password" placeholder="Contraseña privada" required autofocus>
<button class="btn" type="submit">ENTRAR 8551</button>
{% if error %}<div class="error">❌ {{error}}</div>{% endif %}
<div class="hint">Variable en Render: OSTO_PASSWORD<br>Por defecto: osto8551</div>
</form>
</div>
</body></html>
"""

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('osto_auth'):
            # Si es API, devuelve 401
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado - login requerido'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        pwd = request.form.get('password','') or (request.json.get('password','') if request.is_json else '')
        if pwd == OSTO_PASSWORD:
            session['osto_auth'] = True
            # si viene de fetch API, devuelve json
            if request.is_json:
                return jsonify({'ok': True})
            return redirect('/')
        else:
            error = "Contraseña incorrecta"
            if request.is_json:
                return jsonify({'ok': False, 'error': error}), 401
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# === TU CODIGO ORIGINAL PERO PROTEGIDO ===

YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'skip_download': True,
    'getcomments': True,
}

def search_youtube(query, limit=12):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,
        'default_search': f'ytsearch{limit}',
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        results = []
        for e in info.get('entries', []):
            if not e: continue
            results.append({
                'id': e.get('id'),
                'title': e.get('title'),
                'thumbnail': e.get('thumbnails', [{}])[-1].get('url') if e.get('thumbnails') else f"https://i.ytimg.com/vi/{e.get('id')}/hqdefault.jpg",
                'channel': e.get('channel') or e.get('uploader'),
                'duration': e.get('duration'),
                'view_count': e.get('view_count'),
                'url': f"https://www.youtube.com/watch?v={e.get('id')}",
            })
        return results

def get_video_info(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'getcomments': True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        comments = []
        for c in (info.get('comments') or [])[:50]:
            comments.append({
                'author': c.get('author'),
                'text': c.get('text'),
                'likes': c.get('like_count'),
            })
        return {
            'id': info.get('id'),
            'title': info.get('title'),
            'description': info.get('description','')[:2000],
            'thumbnail': info.get('thumbnail'),
            'channel': info.get('channel') or info.get('uploader'),
            'view_count': info.get('view_count'),
            'like_count': info.get('like_count'),
            'upload_date': info.get('upload_date'),
            'duration': info.get('duration'),
            'tags': info.get('tags', [])[:20],
            'comments': comments,
            'is_live': info.get('is_live'),
        }

@app.route('/')
@login_required
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search')
@login_required
def api_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify([])
    try:
        results = search_youtube(q, limit=16)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>')
@login_required
def api_video(video_id):
    try:
        info = get_video_info(video_id)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending')
@login_required
def api_trending():
    try:
        results = search_youtube("music 2026 hits", limit=16)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"OSTO PASSWORD: {OSTO_PASSWORD} - Pon OSTO_PASSWORD en Render para cambiarla")
    app.run(host='0.0.0.0', port=port, debug=False)
