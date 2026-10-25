import os, hmac, hashlib, secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-only-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{BASE_DIR / "learnwithhb.db"}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_MB', '25')) * 1024 * 1024
app.config['UPLOAD_FOLDER'] = str(BASE_DIR / 'uploads')
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
db = SQLAlchemy(app)
login_manager = LoginManager(app); login_manager.login_view = 'login'
CATEGORIES = ['AWS & Cloud Computing','Kubernetes','Docker & Containers','Jenkins & CI/CD','Terraform & IaC','Linux & Shell Scripting','DevOps Interview Preparation','Prometheus & Grafana','Git & GitHub Actions','PostgreSQL & Databases']

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True); email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False); is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    def set_password(self, p): self.password_hash = generate_password_hash(p)
    def check_password(self, p): return check_password_hash(self.password_hash, p)
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True); title = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False); short_description = db.Column(db.String(400), nullable=False)
    description = db.Column(db.Text, default=''); category = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(255), nullable=False); price_paise = db.Column(db.Integer, default=10000, nullable=False)
    published = db.Column(db.Boolean, default=False); featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Blog(db.Model):
    id = db.Column(db.Integer, primary_key=True); title = db.Column(db.String(180), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False); category = db.Column(db.String(100), default='DevOps')
    excerpt = db.Column(db.String(400), default=''); content = db.Column(db.Text, nullable=False)
    published = db.Column(db.Boolean, default=False); created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True); user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False); amount_paise = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False); razorpay_order_id = db.Column(db.String(120), unique=True)
    razorpay_payment_id = db.Column(db.String(120)); created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User'); material = db.relationship('Material')
@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))
def admin_required(fn):
    @wraps(fn)
    def wrapped(*a, **kw):
        if not current_user.is_authenticated or not current_user.is_admin: abort(403)
        return fn(*a, **kw)
    return wrapped
def slugify(s):
    import re
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')
def has_access(material_id):
    return current_user.is_authenticated and (current_user.is_admin or Order.query.filter_by(user_id=current_user.id, material_id=material_id, status='paid').first() is not None)
@app.context_processor
def inject_globals(): return {'categories': CATEGORIES, 'has_access': has_access}

@app.route('/')
def home():
    materials = Material.query.filter_by(published=True).order_by(Material.created_at.desc()).limit(6).all()
    blogs = Blog.query.filter_by(published=True).order_by(Blog.created_at.desc()).limit(3).all()
    return render_template('home.html', materials=materials, blogs=blogs)
@app.route('/materials')
def materials():
    q = request.args.get('q','').strip(); category = request.args.get('category','')
    query = Material.query.filter_by(published=True)
    if q: query = query.filter(Material.title.ilike(f'%{q}%') | Material.short_description.ilike(f'%{q}%'))
    if category: query = query.filter_by(category=category)
    return render_template('materials.html', materials=query.order_by(Material.created_at.desc()).all(), q=q, category=category)
@app.route('/categories/<path:category>')
def category_page(category): return redirect(url_for('materials', category=category.replace('-', ' ').title()))
@app.route('/materials/<slug>')
def material_detail(slug):
    item = Material.query.filter_by(slug=slug, published=True).first_or_404()
    return render_template('material.html', item=item)
@app.route('/blogs')
def blogs(): return render_template('blogs.html', blogs=Blog.query.filter_by(published=True).order_by(Blog.created_at.desc()).all())
@app.route('/blogs/<slug>')
def blog_detail(slug): return render_template('blog.html', blog=Blog.query.filter_by(slug=slug, published=True).first_or_404())
@app.route('/about')
def about(): return render_template('page.html', title='About LearnWithHB', body='LearnWithHB helps technology learners build practical skills with focused notes, tutorials, and interview preparation resources.')
@app.route('/contact')
def contact(): return render_template('page.html', title='Contact', body='For questions about study materials or access, contact the site administrator. Add your business email here before publishing.')
@app.route('/privacy-policy')
def privacy(): return render_template('page.html', title='Privacy Policy', body='Replace this starter policy with a policy reviewed for your business, including account data, payment processing, cookies, retention, and contact details.')
@app.route('/terms')
def terms(): return render_template('page.html', title='Terms and Conditions', body='Replace this starter text with your terms of service before accepting real payments.')
@app.route('/refund-policy')
def refunds(): return render_template('page.html', title='Refund Policy', body='Publish a clear refund policy reviewed for your business before accepting real payments.')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email=request.form.get('email','').strip().lower(); password=request.form.get('password','')
        if not email or len(password)<10: flash('Enter an email and a password of at least 10 characters.','error')
        elif User.query.filter_by(email=email).first(): flash('That email is already registered.','error')
        else:
            u=User(email=email); u.set_password(password); db.session.add(u); db.session.commit(); login_user(u); return redirect(url_for('home'))
    return render_template('auth.html', mode='register')
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u=User.query.filter_by(email=request.form.get('email','').strip().lower()).first()
        if u and u.check_password(request.form.get('password','')): login_user(u); return redirect(url_for('admin') if u.is_admin else url_for('library'))
        flash('Invalid email or password.','error')
    return render_template('auth.html', mode='login')
@app.route('/logout', methods=['POST'])
@login_required
def logout(): logout_user(); return redirect(url_for('home'))
@app.route('/my-library')
@login_required
def library(): return render_template('library.html', orders=Order.query.filter_by(user_id=current_user.id,status='paid').order_by(Order.created_at.desc()).all())
@app.route('/my-orders')
@login_required
def my_orders(): return render_template('library.html', orders=Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all(), show_all=True)
@app.route('/download/<int:material_id>')
@login_required
def download(material_id):
    item=Material.query.get_or_404(material_id)
    if not has_access(item.id): abort(403)
    # Local development storage only. For production, replace with short-lived private S3 presigned URLs.
    return send_from_directory(app.config['UPLOAD_FOLDER'], item.filename, as_attachment=True)

@app.route('/buy/<int:material_id>', methods=['POST'])
@login_required
def buy(material_id):
    item=Material.query.filter_by(id=material_id,published=True).first_or_404()
    if has_access(item.id): return redirect(url_for('download', material_id=item.id))
    key=os.getenv('RAZORPAY_KEY_ID'); secret=os.getenv('RAZORPAY_KEY_SECRET')
    if not key or not secret:
        flash('Payments are not configured yet. Admin: add Razorpay Test Mode keys to .env. No payment has been taken.','error'); return redirect(url_for('material_detail',slug=item.slug))
    try:
        import razorpay
        client=razorpay.Client(auth=(key,secret)); rp_order=client.order.create({'amount':item.price_paise,'currency':'INR','receipt':f'lwhb-{current_user.id}-{item.id}-{secrets.token_hex(3)}','notes':{'user_id':str(current_user.id),'material_id':str(item.id)}})
        order=Order(user_id=current_user.id,material_id=item.id,amount_paise=item.price_paise,razorpay_order_id=rp_order['id'],status='pending'); db.session.add(order); db.session.commit()
        return render_template('checkout.html', item=item, order=order, key_id=key, site_url=os.getenv('SITE_URL','http://127.0.0.1:5000'))
    except Exception as e:
        app.logger.exception('Could not create payment order'); flash('Could not start payment. Check server configuration and try again.','error'); return redirect(url_for('material_detail',slug=item.slug))
@app.route('/payment/verify', methods=['POST'])
@login_required
def payment_verify():
    from razorpay.utility import Utility
    order_id=request.form.get('razorpay_order_id',''); payment_id=request.form.get('razorpay_payment_id',''); signature=request.form.get('razorpay_signature','')
    order=Order.query.filter_by(razorpay_order_id=order_id,user_id=current_user.id).first_or_404()
    if order.status == 'paid': return redirect(url_for('download',material_id=order.material_id))
    secret=os.getenv('RAZORPAY_KEY_SECRET','')
    expected=hmac.new(secret.encode(),f'{order_id}|{payment_id}'.encode(),hashlib.sha256).hexdigest() if secret else ''
    if not expected or not hmac.compare_digest(expected, signature):
        flash('Payment signature could not be verified. Your download is not enabled.','error'); return redirect(url_for('my_orders'))
    # Verify the payment/order server-side before granting access.
    try:
        import razorpay
        client=razorpay.Client(auth=(os.getenv('RAZORPAY_KEY_ID'),secret)); payment=client.payment.fetch(payment_id)
        if payment.get('order_id') != order_id or int(payment.get('amount',-1)) != order.amount_paise or payment.get('currency') != 'INR' or payment.get('status') not in ('captured','authorized'):
            flash('Payment is not confirmed as successful yet. Please refresh your order status later.','error'); return redirect(url_for('my_orders'))
        order.status='paid'; order.razorpay_payment_id=payment_id; db.session.commit()
        return redirect(url_for('download',material_id=order.material_id))
    except Exception:
        app.logger.exception('Payment verification failed'); flash('Could not confirm payment with Razorpay. Access remains locked; contact support if money was deducted.','error'); return redirect(url_for('my_orders'))
@app.route('/razorpay/webhook', methods=['POST'])
def webhook():
    secret=os.getenv('RAZORPAY_WEBHOOK_SECRET',''); signature=request.headers.get('X-Razorpay-Signature',''); body=request.get_data()
    expected=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest() if secret else ''
    if not expected or not hmac.compare_digest(expected,signature): return jsonify({'error':'invalid signature'}),400
    import json
    event=json.loads(body)
    if event.get('event') == 'payment.captured':
        entity=event.get('payload',{}).get('payment',{}).get('entity',{}); oid=entity.get('order_id')
        order=Order.query.filter_by(razorpay_order_id=oid).first()
        if order and entity.get('currency')=='INR' and int(entity.get('amount',-1))==order.amount_paise and entity.get('status')=='captured':
            order.status='paid'; order.razorpay_payment_id=entity.get('id'); db.session.commit()
    return jsonify({'ok':True})

@app.route('/admin')
@login_required
@admin_required
def admin(): return render_template('admin.html', materials=Material.query.order_by(Material.created_at.desc()).all(), blogs=Blog.query.order_by(Blog.created_at.desc()).all(), orders=Order.query.order_by(Order.created_at.desc()).limit(30).all(), sales=db.session.query(db.func.sum(Order.amount_paise)).filter_by(status='paid').scalar() or 0)
@app.route('/admin/materials/new', methods=['GET','POST'])
@login_required
@admin_required
def new_material():
    if request.method=='POST':
        f=request.files.get('file'); title=request.form.get('title','').strip(); slug=slugify(request.form.get('slug') or title)
        try: price=int(float(request.form.get('price','100'))*100)
        except ValueError: price=10000
        if not title or not f or not f.filename or not slug: flash('Title and a file are required.','error')
        elif Material.query.filter_by(slug=slug).first(): flash('That URL slug already exists.','error')
        elif Path(f.filename).suffix.lower() not in ('.pdf','.docx','.zip'): flash('Allowed formats: PDF, DOCX, ZIP.','error')
        else:
            filename=secrets.token_hex(12)+'_'+secure_filename(f.filename); f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
            m=Material(title=title,slug=slug,short_description=request.form.get('short_description','')[:400],description=request.form.get('description',''),category=request.form.get('category',CATEGORIES[0]),filename=filename,price_paise=max(0,price),published=bool(request.form.get('published')),featured=bool(request.form.get('featured')))
            db.session.add(m); db.session.commit(); flash('Study material saved.','success'); return redirect(url_for('admin'))
    return render_template('material_form.html', item=None)
@app.route('/admin/materials/<int:item_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def edit_material(item_id):
    m=Material.query.get_or_404(item_id)
    if request.method=='POST':
        m.title=request.form.get('title',m.title).strip(); m.short_description=request.form.get('short_description','')[:400]; m.description=request.form.get('description',''); m.category=request.form.get('category',m.category); m.price_paise=int(float(request.form.get('price','100'))*100); m.published=bool(request.form.get('published')); m.featured=bool(request.form.get('featured'))
        f=request.files.get('file')
        if f and f.filename:
            if Path(f.filename).suffix.lower() not in ('.pdf','.docx','.zip'): flash('Allowed formats: PDF, DOCX, ZIP.','error'); return redirect(request.url)
            filename=secrets.token_hex(12)+'_'+secure_filename(f.filename); f.save(os.path.join(app.config['UPLOAD_FOLDER'],filename)); m.filename=filename
        db.session.commit(); flash('Material updated.','success'); return redirect(url_for('admin'))
    return render_template('material_form.html',item=m)
@app.route('/admin/blogs/new', methods=['GET','POST'])
@login_required
@admin_required
def new_blog():
    if request.method=='POST':
        title=request.form.get('title','').strip(); slug=slugify(request.form.get('slug') or title)
        if not title or not request.form.get('content','').strip(): flash('Title and article content are required.','error')
        elif Blog.query.filter_by(slug=slug).first(): flash('That blog slug already exists.','error')
        else:
            b=Blog(title=title,slug=slug,category=request.form.get('category','DevOps'),excerpt=request.form.get('excerpt','')[:400],content=request.form.get('content',''),published=bool(request.form.get('published'))); db.session.add(b); db.session.commit(); flash('Blog saved.','success'); return redirect(url_for('admin'))
    return render_template('blog_form.html',blog=None)
@app.route('/admin/blogs/<int:blog_id>/edit', methods=['GET','POST'])
@login_required
@admin_required
def edit_blog(blog_id):
    b=Blog.query.get_or_404(blog_id)
    if request.method=='POST':
        b.title=request.form.get('title',b.title).strip(); b.category=request.form.get('category','DevOps'); b.excerpt=request.form.get('excerpt','')[:400]; b.content=request.form.get('content',''); b.published=bool(request.form.get('published')); db.session.commit(); flash('Blog updated.','success'); return redirect(url_for('admin'))
    return render_template('blog_form.html',blog=b)
@app.errorhandler(403)
def forbidden(e): return render_template('page.html',title='Access denied',body='You do not have permission to access this page.'),403
@app.errorhandler(404)
def not_found(e): return render_template('page.html',title='Page not found',body='We could not find that page. Browse study materials or free blogs instead.'),404
@app.errorhandler(413)
def too_large(e): return render_template('page.html',title='File too large',body='The upload exceeds the configured file-size limit.'),413

with app.app_context():
    db.create_all()
    admin_email=os.getenv('ADMIN_EMAIL','').strip().lower(); admin_password=os.getenv('ADMIN_PASSWORD','')
    if admin_email and admin_password and not User.query.filter_by(email=admin_email).first():
        u=User(email=admin_email,is_admin=True); u.set_password(admin_password); db.session.add(u); db.session.commit()

if __name__ == '__main__': app.run(host='127.0.0.1', port=int(os.getenv('PORT','5000')), debug=os.getenv('FLASK_DEBUG','0')=='1')
