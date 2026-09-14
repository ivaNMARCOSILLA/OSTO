from flask import Flask, request, jsonify, send_from_directory, session, redirect, render_template_string
from flask_cors import CORS
import os, functools, requests

app = Flask(__name__, static_folder='.')
CORS(app)

OSTO_PASSWORD = os.environ.get("OSTO_PASSWORD", "osto8551")
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")
app.secret_key = os.environ.get("SECRET_KEY", "osto-8551-secreto-privado-2026")

LOGIN_HTML = """
<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OSTO PRIVADO - LOGIN</title>
<style>
:root{--bg:#050507;--card:#15151a;--neon:#ff0033;--border:#22222a;--text:#e8e8e8;--muted:#7a7a85}
*{margin:0;padding:0;box-sizing:border-box}body{background:var(--bg);color:var(--text);font-family:monospace;display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:32px;width:100%;max-width:380px;box-shadow:0 0 40px rgba(255,0,51,.15)}
.logo{font-weight:700;font-size:28px;text-align:center;margin-bottom:6px}.logo span{color:var(--neon)}
.sub{font-size:11px;color:var(--muted);text-align:center;margin-bottom:24px;letter-spacing:1px}
input{width:100%;background:#0f0f12;border:1px solid var(--border);color:#fff;padding:12px 14px;border-radius:10px;outline:none;font-size:15px}
input:focus{border-color:var(--neon)}
.btn{width:100%;background:var(--neon);border:0;color:#fff;padding:12px;border-radius:10px;font-weight:700;cursor:pointer;margin-top:12px}
.error{color:var(--neon);font-size:11px;margin-top:10px;text-align:center}
</style></head><body>
<div class="box">
<div class="logo">OSTO<span>TUBE</span></div>
<div class="sub">PRIVADO 8551 • ACCESO RESTRINGIDO</div>
<form method="POST" action="/login">
<input type="password" name="password" placeholder="Contraseña privada" required autofocus>
<button class="btn" type="submit">ENTRAR 8551</button>
{% if error %}<div class="error">❌ {{error}}</div>{% endif %}
</form>
</div>
</body></html>
"""

def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('osto_auth'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autorizado'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET','POST'])
def login():
    error=None
    if request.method=='POST':
        pwd=request.form.get('password','')
        if pwd==OSTO_PASSWORD:
            session['osto_auth']=True
            return redirect('/')
        else:
            error="Contraseña incorrecta"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def search_youtube_api(query, limit=12):
    if not YOUTUBE_API_KEY:
        raise Exception("No YT API KEY")
    url="https://www.googleapis.com/youtube/v3/search"
    params={'part':'snippet','q':query,'maxResults':limit,'type':'video','key':YOUTUBE_API_KEY}
    r=requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data=r.json()
    results=[]
    for item in data.get('items',[]):
        vid=item['id'].get('videoId')
        sn=item['snippet']
        results.append({'id':vid,'title':sn['title'],'thumbnail':sn['thumbnails']['high']['url'],'channel':sn['channelTitle'],'duration':0,'view_count':0,'url':f"https://www.youtube.com/watch?v={vid}"})
    return results

def search_youtube_ydl(query, limit=12):
    import yt_dlp
    opts={'quiet':True,'no_warnings':True,'extract_flat':True,'cookiefile':'cookies.txt' if os.path.exists('cookies.txt') else None}
    opts={k:v for k,v in opts.items() if v}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        res=[]
        for e in info.get('entries',[]):
            if not e: continue
            res.append({'id':e.get('id'),'title':e.get('title'),'thumbnail':e.get('thumbnails', [{}])[-1].get('url') if e.get('thumbnails') else f"https://i.ytimg.com/vi/{e.get('id')}/hqdefault.jpg",'channel':e.get('channel') or e.get('uploader'),'duration':e.get('duration'),'view_count':e.get('view_count'),'url':f"https://www.youtube.com/watch?v={e.get('id')}"})
        return res

def search_youtube(query, limit=12):
    if YOUTUBE_API_KEY:
        try:
            return search_youtube_api(query, limit)
        except Exception as e:
            print(f"API fallo: {e}")
    try:
        return search_youtube_ydl(query, limit)
    except Exception as e:
        if "Sign in" in str(e):
            raise Exception("YouTube pide login bot. Añade YOUTUBE_API_KEY en Render (ya lo hiciste) y redeploy.")
        raise e

def get_video_info(video_id):
    if YOUTUBE_API_KEY:
        try:
            url="https://www.googleapis.com/youtube/v3/videos"
            params={'part':'snippet,statistics','id':video_id,'key':YOUTUBE_API_KEY}
            r=requests.get(url, params=params, timeout=10)
            data=r.json()
            if data.get('items'):
                it=data['items'][0]; sn=it['snippet']; st=it.get('statistics',{})
                return {'id':video_id,'title':sn['title'],'description':sn.get('description','')[:2000],'thumbnail':sn['thumbnails']['high']['url'],'channel':sn['channelTitle'],'view_count':st.get('viewCount'),'like_count':st.get('likeCount'),'upload_date':sn.get('publishedAt','')[:10],'duration':0,'tags':sn.get('tags',[])[:20],'comments':[],'is_live':False}
        except: pass
    import yt_dlp
    url=f"https://www.youtube.com/watch?v={video_id}"
    opts={'quiet':True,'no_warnings':True,'skip_download':True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info=ydl.extract_info(url, download=False)
        return {'id':info.get('id'),'title':info.get('title'),'description':info.get('description','')[:2000],'thumbnail':info.get('thumbnail'),'channel':info.get('channel') or info.get('uploader'),'view_count':info.get('view_count'),'like_count':info.get('like_count'),'upload_date':info.get('upload_date'),'duration':info.get('duration'),'tags':info.get('tags',[])[:20],'comments':[],'is_live':info.get('is_live')}

@app.route('/')
@login_required
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search')
@login_required
def api_search():
    q=request.args.get('q','').strip()
    if not q: return jsonify([])
    try:
        return jsonify(search_youtube(q, limit=16))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/video/<video_id>')
@login_required
def api_video(video_id):
    try:
        return jsonify(get_video_info(video_id))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending')
@login_required
def api_trending():
    try:
        return jsonify(search_youtube("music 2026 hits", limit=16))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__=='__main__':
    port=int(os.environ.get('PORT',8080))
    app.run(host='0.0.0.0', port=port, debug=False)

