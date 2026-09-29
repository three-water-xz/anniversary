from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key_for_dev')

# 上传上限 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'mov'}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_PHOTOS = os.path.join(BASE_DIR, 'static', 'uploads', 'photos')
UPLOAD_VIDEOS = os.path.join(BASE_DIR, 'static', 'uploads', 'videos')
MUSIC_DIR = os.path.join(BASE_DIR, 'static', 'music')
LETTER_PATH = os.path.join(BASE_DIR, 'letter.txt')

os.makedirs(UPLOAD_PHOTOS, exist_ok=True)
os.makedirs(UPLOAD_VIDEOS, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)

app.config['UPLOAD_PHOTOS'] = UPLOAD_PHOTOS
app.config['UPLOAD_VIDEOS'] = UPLOAD_VIDEOS
app.config['MUSIC_DIR'] = MUSIC_DIR

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 解决浏览器默认请求 favicon 导致的 404 日志
@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/')
def index():
    letter_content = "暂无信件内容"
    if os.path.exists(LETTER_PATH):
        with open(LETTER_PATH, 'r', encoding='utf-8') as f:
            letter_content = f.read()

    # 倒序排列，最新上传的照片/视频排在前面
    photos = []
    if os.path.exists(app.config['UPLOAD_PHOTOS']):
        photos = sorted([f for f in os.listdir(app.config['UPLOAD_PHOTOS'])
                         if os.path.isfile(os.path.join(app.config['UPLOAD_PHOTOS'], f)) and not f.startswith('.')],
                        reverse=True)

    videos = []
    if os.path.exists(app.config['UPLOAD_VIDEOS']):
        videos = sorted([f for f in os.listdir(app.config['UPLOAD_VIDEOS'])
                         if os.path.isfile(os.path.join(app.config['UPLOAD_VIDEOS'], f)) and not f.startswith('.')],
                        reverse=True)

    # 加载 MP3 音频，并确保将《嗜好.mp3》置顶为第一首歌
    music_files = []
    default_song = "嗜好.mp3"
    if os.path.exists(app.config['MUSIC_DIR']):
        for f in os.listdir(app.config['MUSIC_DIR']):
            full_path = os.path.join(app.config['MUSIC_DIR'], f)
            if os.path.isfile(full_path) and not f.startswith('.') and f.lower().endswith('.mp3'):
                music_files.append(f)
        
        music_files.sort()
        matched_song = next((s for s in music_files if s.lower() == default_song.lower()), None)
        if matched_song:
            music_files.remove(matched_song)
            music_files.insert(0, matched_song)

    return render_template('index.html', letter=letter_content, photos=photos, videos=videos, music_files=music_files)

@app.route('/upload/<file_type>', methods=['POST'])
def upload_file(file_type):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if 'file' not in request.files:
        if is_ajax: return jsonify(success=False, msg='未选择文件')
        flash('没有选择文件！', 'error')
        return redirect(url_for('index'))

    file = request.files['file']
    if not file or file.filename == '':
        if is_ajax: return jsonify(success=False, msg='文件名不能为空')
        flash('文件名不能为空！', 'error')
        return redirect(url_for('index'))

    if file_type == 'photo' and not allowed_file(file.filename, ALLOWED_PHOTO_EXTENSIONS):
        msg = '不支持的图片格式！'
        if is_ajax: return jsonify(success=False, msg=msg)
        flash(msg, 'error')
        return redirect(url_for('index'))

    if file_type == 'video' and not allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
        msg = '不支持的视频格式！请上传 mp4 或 webm'
        if is_ajax: return jsonify(success=False, msg=msg)
        flash(msg, 'error')
        return redirect(url_for('index'))

    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    try:
        target_dir = app.config['UPLOAD_PHOTOS'] if file_type == 'photo' else app.config['UPLOAD_VIDEOS']
        file.save(os.path.join(target_dir, unique_filename))
        
        if is_ajax:
            url_path = f"/static/uploads/{'photos' if file_type == 'photo' else 'videos'}/{unique_filename}"
            return jsonify(success=True, msg='上传成功啦！✨', filename=unique_filename, url=url_path, type=file_type)

        flash('上传成功啦！✨', 'success')
    except Exception as e:
        if is_ajax: return jsonify(success=False, msg=f'保存失败: {str(e)}')
        flash(f'保存失败: {str(e)}', 'error')

    return redirect(url_for('index'))

@app.route('/delete/<file_type>/<filename>', methods=['POST'])
def delete_file(file_type, filename):
    clean_name = os.path.basename(filename)
    target_dir = app.config['UPLOAD_PHOTOS'] if file_type == 'photo' else app.config['UPLOAD_VIDEOS']
    file_path = os.path.join(target_dir, clean_name)

    if os.path.exists(file_path) and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            return jsonify(success=True, msg='已经悄悄删掉啦～')
        except Exception as e:
            return jsonify(success=False, msg=f'删除失败: {str(e)}')
    return jsonify(success=False, msg='文件不存在')

@app.errorhandler(413)
def request_entity_too_large(error):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify(success=False, msg='文件过大，上限 50MB！')
    flash('上传文件过大，单次上传上限为 50MB！', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)