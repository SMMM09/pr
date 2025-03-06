from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
import datetime
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import random
from kavenegar import *
import re
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tasks.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    verification_code = db.Column(db.String(6))
    verified = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User %r>' % self.username

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    pomodoro_time = db.Column(db.Integer, default=25)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    completed = db.Column(db.Boolean, default=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    rest_time = db.Column(db.Integer)
    priority = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Task %r>' % self.id

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'pomodoro_time': self.pomodoro_time,
            'category_id': self.category_id,
            'completed': self.completed,
            'priority': self.priority
        }

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return '<Category %r>' % self.id

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def send_sms_kavenegar(phone, code, api_key):
    print(f'CODE: {code}')

def send_verification_code(phone, code):
    api_key = 'your_api_key'
    send_sms_kavenegar(phone, code, api_key)

def create_default_categories():
    if Category.query.count() == 0:
        default_categories = ['کار', 'شخصی', 'مطالعه']
        for category_name in default_categories:
            category = Category(name=category_name)
            db.session.add(category)
        db.session.commit()

def calculate_stats():
    tasks = Task.query.all()
    completed_tasks = [task for task in tasks if task.completed]
    total_tasks = len(tasks)
    completed_count = len(completed_tasks)
    completion_rate = round((completed_count / total_tasks) * 100 if total_tasks > 0 else 0)
    return {
        'total_tasks': total_tasks,
        'completed_count': completed_count,
        'completion_rate': completion_rate,
    }

def calculate_rest_time(task_time):
    rest_time = task_time * 0.2
    return math.ceil(rest_time)

@app.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        tasks = Task.query.all()
        return render_template('index.html', logged_in=True, tasks=tasks)
    else:
        return render_template('index.html', logged_in=False)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task_to_delete = Task.query.get_or_404(id)

    try:
        db.session.delete(task_to_delete)
        db.session.commit()
        flash('وظیفه با موفقیت حذف شد', 'success')
        return redirect('/dashboard')
    except:
        flash('مشکلی در حذف وظیفه وجود داشت', 'error')
        return redirect('/dashboard')

@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update(id):
    task = Task.query.get_or_404(id)
    categories = Category.query.all()
    if request.method == 'POST':
        task_content = request.form['content']
        task_pomodoro = request.form.get('pomodoro_time')  # استفاده از get برای جلوگیری از KeyError
        task_category_id = request.form['category_id']

        if not task_content or not task_pomodoro:
            flash('لطفاً عنوان و زمان پومودورو را وارد کنید', 'error')
            return redirect('/update/' + str(id))

        try:
            task.content = task_content
            task.pomodoro_time = task_pomodoro
            task.category_id = task_category_id
            db.session.commit()
            flash('وظیفه با موفقیت به‌روزرسانی شد', 'success')
            return redirect('/dashboard')
        except:
            flash('مشکلی در به‌روزرسانی وظیفه وجود داشت', 'error')
            return redirect('/update/' + str(id))
    else:
        return render_template('update.html', task=task, categories=categories)

@app.route('/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'POST':
        category_name = request.form['name']

        if not category_name:
            flash('لطفاً نام دسته بندی را وارد کنید', 'error')
            return redirect('/categories')

        new_category = Category(name=category_name)

        try:
            db.session.add(new_category)
            db.session.commit()
            flash('دسته بندی با موفقیت اضافه شد', 'success')
            return redirect('/categories')
        except:
            flash('مشکلی در اضافه کردن دسته بندی وجود داشت', 'error')
            return redirect('/categories')

    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/delete_category/<int:id>')
@login_required
def delete_category(id):
    category_to_delete = Category.query.get_or_404(id)

    try:
        db.session.delete(category_to_delete)
        db.session.commit()
        flash('دسته بندی با موفقیت حذف شد', 'success')
        return redirect('/categories')
    except:
        flash('مشکلی در حذف دسته بندی وجود داشت', 'error')
        return redirect('/categories')

@app.route('/update_category/<int:id>', methods=['GET', 'POST'])
@login_required
def update_category(id):
    category = Category.query.get_or_404(id)
    if request.method == 'POST':
        category_name = request.form['name']

        if not category_name:
            flash('لطفاً نام دسته بندی را وارد کنید', 'error')
            return redirect('/update_category/' + str(id))

        try:
            category.name = category_name
            db.session.commit()
            flash('دسته بندی با موفقیت به‌روزرسانی شد', 'success')
            return redirect('/categories')
        except:
            flash('مشکلی در به‌روزرسانی دسته بندی وجود داشت', 'error')
            return redirect('/update_category/' + str(id))
    else:
        return render_template('update_category.html', category=category)

@app.route('/dashboard', methods=['POST', 'GET'])
@login_required
def dashboard():
    create_default_categories()
    categories = Category.query.all()
    if request.method == 'POST':
        task_content = request.form['content']
        task_pomodoro = request.form['pomodoro_time']
        task_category_id = request.form['category_id']

        if not task_content or not task_pomodoro:
            flash('لطفاً عنوان و زمان پومودورو را وارد کنید', 'error')
            return redirect('/dashboard')

        try:
            new_task = Task(content=task_content, pomodoro_time=task_pomodoro, category_id=task_category_id)
            db.session.add(new_task)
            db.session.commit()
            flash('وظیفه با موفقیت اضافه شد', 'success')
            return redirect('/dashboard')
        except:
            flash('مشکلی در اضافه کردن وظیفه شما وجود داشت', 'error')
            return redirect('/dashboard')

    else:
        tasks = Task.query.order_by(Task.completed, Task.priority).all()
        tasks_list = []
        for task in tasks:
            tasks_list.append({
                'id': task.id,
                'content': task.content,
                'pomodoro_time': task.pomodoro_time,
                'category_id': task.category_id,
                'completed': task.completed,
                'priority': task.priority
            })
        stats = calculate_stats()
        return render_template('dashboard.html', tasks=tasks_list, stats=stats, categories=categories)

@app.route('/complete/<int:id>', methods=['POST'])
@login_required
def complete(id):
    task = Task.query.get_or_404(id)
    data = request.get_json()
    task.completed = data['completed']
    db.session.commit()
    return jsonify({'message': 'وضعیت وظیفه به‌روزرسانی شد'})

@app.route('/update_task_priority', methods=['POST'])
@login_required
def update_task_priority():
    tasks_order = request.get_json()
    for index, task_id in enumerate(tasks_order):
        task = Task.query.get_or_404(task_id)
        task.priority = index + 1
    db.session.commit()
    return jsonify({'message': 'اولویت وظایف به‌روزرسانی شد'})

@app.route('/login', methods=['GET', 'POST'])
def login():
   if current_user.is_authenticated:
       return redirect(url_for('dashboard'))

   if request.method == 'POST':
       username = request.form['username']
       password = request.form['password']
       user = User.query.filter_by(username=username).first()

       if user and bcrypt.check_password_hash(user.password, password):
           if user.verified:
               login_user(user)
               return redirect(url_for('dashboard'))
           else:
               flash('حساب شما هنوز تایید نشده است.', 'warning')
               return redirect(url_for('verify', phone=user.phone))
       else:
           flash('نام کاربری یا رمز عبور اشتباه است.', 'error')

   return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
   if request.method == 'POST':
       username = request.form['username']
       phone = request.form['phone']
       password = request.form['password']

       errors = {}

       if not re.match(r"^[a-zA-Z0-9_]+$", username):
           errors['username'] = 'نام کاربری باید شامل حروف، اعداد و زیرخط باشد.'

       if not re.match(r"^09\d{9}$", phone):
           errors['phone'] = 'شماره تلفن باید با 09 شروع شود و 11 رقم باشد.'

       if len(password) < 8:
           errors['password'] = 'رمز عبور باید حداقل 8 کاراکتر باشد.'

       if errors:
           return render_template('register.html', errors=errors)

       hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
       verification_code = str(random.randint(100000, 999000))
       new_user = User(username=username, phone=phone, password=hashed_password, verification_code=verification_code)

       try:
           db.session.add(new_user)
           db.session.commit()
           send_verification_code(phone, verification_code)
           flash('کد تأیید به شماره تلفن شما ارسال شد.', 'info')
           return redirect(url_for('verify', phone=phone))
       except:
           flash('مشکلی در ثبت نام شما وجود داشت.', 'error')

   return render_template('register.html')

@app.route('/verify/<phone>', methods=['GET', 'POST'])
def verify(phone):
   user = User.query.filter_by(phone=phone).first()

   if not user:
       flash('کاربر یافت نشد.', 'error')
       return redirect(url_for('register'))

   if request.method == 'POST':
       verification_code = request.form['verification_code']
       if user.verification_code == verification_code:
           user.verified = True
           db.session.commit()
           flash('حساب شما با موفقیت تایید شد.', 'success')
           login_user(user)
           return redirect(url_for('dashboard'))
       else:
           flash('کد تأیید اشتباه است.', 'error')

   return render_template('verify.html', phone=phone)

@app.route('/logout')
@login_required
def logout():
   logout_user()
   return redirect(url_for('login'))

if __name__ == "__main__":
   with app.app_context():
       db.create_all()
       create_default_categories()
   app.run(debug=True)