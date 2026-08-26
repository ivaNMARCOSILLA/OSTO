
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import yt_dlp
import os, re, json, urllib.parse

app = Flask(__name__, static_folder='.')
CORS(app)

# Config yt-dlp
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
        # comments
        comments = []
        for c in (info.get('comments') or [])[:50]:
            comments.append({
                'author': c.get('author'),
                'text': c.get('text'),
                'likes': c.get('like_count'),
            })
        formats = []
        for f in info.get('formats', [])[-10:]:
            if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                formats.append({
                    'ext': f.get('ext'),
                    'height': f.get('height'),
                    'acodec': f.get('acodec'),
                    'vcodec': f.get('vcodec'),
                    'url': f.get('url')[:120] + '...' if f.get('url') else None
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
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/search')
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
def api_video(video_id):
    try:
        info = get_video_info(video_id)
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/trending')
def api_trending():
    # Búsquedas por defecto con estética OSTO
    try:
        results = search_youtube("music 2026 hits", limit=16)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
