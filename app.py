from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import speedtest
import datetime
from functools import wraps
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ============= DATABASE MODELS =============
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    profile_pic = db.Column(db.String(255))
    bio = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    stories = db.relationship('Story', backref='user', lazy=True, cascade='all, delete-orphan')
    messages = db.relationship('Message', backref='sender', lazy=True)

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    image = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ProxyCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ============= DECORATORS =============
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def guest_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'guest_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def user_logged_in(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'guest_id' not in session and 'admin_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ============= ROUTES =============
@app.route('/')
def index():
    return render_template('index.html')

# ============= ADMIN ROUTES =============
@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    admin = Admin.query.filter_by(username=username).first()
    if admin and admin.check_password(password):
        session['admin_id'] = admin.id
        session['user_type'] = 'admin'
        session['admin_username'] = admin.username
        return jsonify({'success': True, 'redirect': '/admin/dashboard'})
    
    return jsonify({'success': False, 'error': 'نام کاربری یا رمز اشتباه است'})

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/api/images', methods=['GET', 'POST'])
@admin_required
def manage_images():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'فایل انتخاب نشده'})
        
        file = request.files['file']
        description = request.form.get('description', '')
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'فایل انتخاب نشده'})
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            image = Image(filename=filename, description=description)
            db.session.add(image)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'عکس آپلود شد'})
        
        return jsonify({'success': False, 'error': 'نوع فایل مجاز نیست'})
    
    # GET - list all images
    images = Image.query.all()
    return jsonify({
        'success': True,
        'images': [{
            'id': img.id,
            'filename': img.filename,
            'description': img.description,
            'url': f'/uploads/{img.filename}',
            'uploaded_at': img.uploaded_at.strftime('%Y-%m-%d %H:%M')
        } for img in images]
    })

@app.route('/admin/api/images/<int:id>', methods=['DELETE'])
@admin_required
def delete_image(id):
    image = Image.query.get(id)
    if not image:
        return jsonify({'success': False, 'error': 'عکس یافت نشد'})
    
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
    except:
        pass
    
    db.session.delete(image)
    db.session.commit()
    return jsonify({'success': True, 'message': 'عکس حذف شد'})

@app.route('/admin/api/proxy-codes', methods=['GET', 'POST'])
@admin_required
def manage_proxy_codes():
    if request.method == 'POST':
        data = request.json
        code = ProxyCode(
            code=data.get('code'),
            description=data.get('description', '')
        )
        db.session.add(code)
        db.session.commit()
        return jsonify({'success': True, 'message': 'کد اضافه شد'})
    
    # GET
    codes = ProxyCode.query.all()
    return jsonify({
        'success': True,
        'codes': [{
            'id': c.id,
            'code': c.code,
            'description': c.description,
            'created_at': c.created_at.strftime('%Y-%m-%d %H:%M')
        } for c in codes]
    })

@app.route('/admin/api/proxy-codes/<int:id>', methods=['DELETE'])
@admin_required
def delete_proxy_code(id):
    code = ProxyCode.query.get(id)
    if not code:
        return jsonify({'success': False, 'error': 'کد یافت نشد'})
    
    db.session.delete(code)
    db.session.commit()
    return jsonify({'success': True, 'message': 'کد حذف شد'})

@app.route('/admin/api/guests')
@admin_required
def get_guests():
    guests = Guest.query.all()
    return jsonify({
        'success': True,
        'guests': [{
            'id': g.id,
            'username': g.username,
            'bio': g.bio,
            'created_at': g.created_at.strftime('%Y-%m-%d %H:%M'),
            'stories_count': len(g.stories)
        } for g in guests]
    })

# ============= GUEST ROUTES =============
@app.route('/guest/login', methods=['POST'])
def guest_login():
    data = request.json
    username = data.get('username')
    
    if not username or len(username) < 2:
        return jsonify({'success': False, 'error': 'نام کاربری باید حداقل 2 حرف باشد'})
    
    guest = Guest.query.filter_by(username=username).first()
    if guest:
        session['guest_id'] = guest.id
        session['guest_username'] = guest.username
    else:
        guest = Guest(username=username)
        db.session.add(guest)
        db.session.commit()
        session['guest_id'] = guest.id
        session['guest_username'] = guest.username
    
    session['user_type'] = 'guest'
    return jsonify({'success': True, 'redirect': '/guest/home'})

@app.route('/guest/home')
@guest_required
def guest_home():
    return render_template('guest_home.html')

@app.route('/guest/logout')
def guest_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/guest/api/speed-test')
@guest_required
def speed_test():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Convert to Mbps
        upload = st.upload() / 1_000_000
        ping = st.results.ping
        
        return jsonify({
            'success': True,
            'download': round(download, 2),
            'upload': round(upload, 2),
            'ping': round(ping, 2)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/guest/api/chat', methods=['GET', 'POST'])
@guest_required
def chat():
    if request.method == 'POST':
        data = request.json
        content = data.get('content', '').strip()
        
        if not content or len(content) > 1000:
            return jsonify({'success': False, 'error': 'پیام نامعتبر است'})
        
        message = Message(
            sender_id=session['guest_id'],
            content=content
        )
        db.session.add(message)
        db.session.commit()
        return jsonify({'success': True})
    
    # GET - recent messages
    messages = Message.query.order_by(Message.created_at.desc()).limit(100).all()
    return jsonify({
        'success': True,
        'messages': [{
            'id': msg.id,
            'sender': msg.sender.username,
            'content': msg.content,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for msg in reversed(messages)]
    })

@app.route('/guest/api/images')
@guest_required
def guest_get_images():
    images = Image.query.all()
    return jsonify({
        'success': True,
        'images': [{
            'id': img.id,
            'filename': img.filename,
            'description': img.description,
            'url': f'/uploads/{img.filename}'
        } for img in images]
    })

@app.route('/guest/api/proxy-codes')
@guest_required
def guest_get_proxy_codes():
    codes = ProxyCode.query.all()
    return jsonify({
        'success': True,
        'codes': [{
            'id': c.id,
            'code': c.code,
            'description': c.description
        } for c in codes]
    })

@app.route('/guest/api/profile', methods=['GET', 'POST'])
@guest_required
def profile():
    guest_id = session['guest_id']
    guest = Guest.query.get(guest_id)
    
    if request.method == 'POST':
        if 'bio' in request.form:
            bio = request.form.get('bio', '').strip()
            if len(bio) <= 500:
                guest.bio = bio
        
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')
                filename = f"profile_{guest_id}_{timestamp}{os.path.splitext(filename)[1]}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                guest.profile_pic = filename
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'پروفایل بروزرسانی شد'})
    
    return jsonify({
        'success': True,
        'username': guest.username,
        'bio': guest.bio or '',
        'profile_pic': f'/uploads/{guest.profile_pic}' if guest.profile_pic else None,
        'created_at': guest.created_at.strftime('%Y-%m-%d')
    })

@app.route('/guest/api/stories', methods=['GET', 'POST'])
@guest_required
def stories():
    guest_id = session['guest_id']
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'فایل انتخاب نشده'})
        
        file = request.files['file']
        caption = request.form.get('caption', '').strip()
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = f"story_{guest_id}_{timestamp}{os.path.splitext(filename)[1]}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            story = Story(user_id=guest_id, image=filename, caption=caption)
            db.session.add(story)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'استوری آپلود شد'})
        
        return jsonify({'success': False, 'error': 'نوع فایل مجاز نیست'})
    
    # GET - get user's stories
    user_stories = Story.query.filter_by(user_id=guest_id).all()
    return jsonify({
        'success': True,
        'stories': [{
            'id': s.id,
            'image': f'/uploads/{s.image}',
            'caption': s.caption,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M')
        } for s in user_stories]
    })

@app.route('/guest/api/all-stories')
@guest_required
def all_stories():
    stories = Story.query.order_by(Story.created_at.desc()).all()
    return jsonify({
        'success': True,
        'stories': [{
            'id': s.id,
            'username': s.user.username,
            'image': f'/uploads/{s.image}',
            'caption': s.caption,
            'created_at': s.created_at.strftime('%Y-%m-%d %H:%M')
        } for s in stories]
    })

# ============= UTILITIES =============
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============= ERROR HANDLERS =============
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('500.html'), 500

# ============= CREATE INITIAL ADMIN =============
def create_initial_admin():
    with app.app_context():
        db.create_all()
        admin = Admin.query.first()
        if not admin:
            admin = Admin(username='admin')
            admin.set_password('1234')
            db.session.add(admin)
            db.session.commit()
            print("=" * 50)
            print("✅ ادمین ایجاد شد")
            print("📧 نام کاربری: admin")
            print("🔐 رمز: 1234")
            print("=" * 50)

if __name__ == '__main__':
    create_initial_admin()
    print("🚀 سرور در حال اجرا است...")
    print("📱 به آدرس زیر بروید:")
    print("http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
