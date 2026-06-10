from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = '1'


#Подключение к бд
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


#Создание баз данных
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

#Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')

#Таблица товаров
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            warranty INTEGER DEFAULT 12,
            description TEXT,
            image_url TEXT,
            category TEXT)
    ''')

#Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            product_price INTEGER NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'новый',
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id))
    ''')

#Таблица обратной связи
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')

#Таблица товары
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            UNIQUE(user_id, product_id))
    ''')

#Товары в базу данных
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        products = [
            ('Игровая мышь RGB', 2499, 24, 'RGB подсветка, 6 программируемых кнопок, 3200 DPI, USB', 'mouse.jpg',
             'мыши'),
            ('Механическая клавиатура', 4599, 36, 'Механические переключатели, RGB подсветка, анти-гостинг',
             'keyboard.jpg', 'клавиатуры'),
            ('Фен-фурье', 1899, 12, '3 режима температуры, ионизация, складная ручка', 'hair_dryer.jpg', 'фены'),
            ('Беспроводная мышь', 1599, 18, '2.4GHz, тихие кнопки, 3 уровня DPI', 'wireless_mouse.jpg', 'мыши'),
            ('Компактная клавиатура', 2999, 24, '60% раскладка, Bluetooth, до 30 дней работы', 'compact_keyboard.jpg',
             'клавиатуры'),
            ('Профессиональный фен', 3499, 24, '220W, 6 насадок, защита от перегрева', 'pro_hair_dryer.jpg', 'фены')]
        for product in products:
            cursor.execute(
                'INSERT INTO products (name, price, warranty, description, image_url, category) VALUES (?, ?, ?, ?, ?, ?)',
                product)

    conn.commit()
    conn.close()


#Проверка правильности всего

#Проверка правильности имени юзера
def validate_username(username):
    if not username or len(username) < 3 or len(username) > 50:
        return False, "Имя пользователя должно быть от 3 до 50 символов"
    if not re.match(r'^[A-Za-zА-Яа-я0-9_]+$', username):
        return False, "Имя пользователя может содержать только буквы, цифры и нижнее подчёркивание"
    return True, ""


#Проверка правильности г-майла
def validate_email(email):
    if not email or len(email) > 100:
        return False, "Email не может быть пустым или длиннее 100 символов"
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Введите правильный email адрес"
    return True, ""


#Проверка правильности пароля
def validate_password(password, confirm_password):
    if not password or len(password) < 6:
        return False, "Пароль должен быть не менее 6 символов"
    if len(password) > 100:
        return False, "Пароль не может быть длиннее 100 символов"
    if password != confirm_password:
        return False, "Пароли не совпадают"
    return True, ""


#Существует ли пользователь в БД
def is_username_exists(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user is not None


#Существует ли почта в БД
def is_email_exists(email):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    return user is not None


#Добавление нового пользователя в БД
def add_user(username, email, password):
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                     (username, email, password))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


#Верификация пользователя
def verify_user(login_input, password):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (login_input,)).fetchone()
    if not user:
        user = conn.execute('SELECT * FROM users WHERE email = ?', (login_input.lower(),)).fetchone()
    conn.close()
    if user and user['password'] == password:
        return user
    return None


#Добавление товара в корзину
def add_to_cart(user_id, product_id, quantity=1):
    conn = get_db_connection()
    try:
        existing = conn.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?',
                                (user_id, product_id)).fetchone()
        if existing:
            conn.execute('UPDATE cart SET quantity = quantity + ? WHERE user_id = ? AND product_id = ?',
                         (quantity, user_id, product_id))
        else:
            conn.execute('INSERT INTO cart (user_id, product_id, quantity) VALUES (?, ?, ?)',
                         (user_id, product_id, quantity))
        conn.commit()
        conn.close()
        return True
    except Exception:
        conn.close()
        return False


def get_cart(user_id):
    conn = get_db_connection()
    cart = conn.execute('''
        SELECT c.*, p.name, p.price, p.description, p.image_url, p.category 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?''',
                        (user_id,)).fetchall()
    conn.close()
    return cart


#Покупка товаров
def get_cart_total(user_id):
    conn = get_db_connection()
    result = conn.execute('''
        SELECT SUM(c.quantity * p.price) as total 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?''',
                          (user_id,)).fetchone()
    conn.close()
    return result['total'] or 0


#Страницы на сайте
#Главная (без пагинации)
@app.route('/')
def index():
    user_id = session.get('user_id')
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return render_template('index.html', products=products, user_id=user_id)


#
@app.route('/order/<int:product_id>', methods=['POST'])
#Если пользователь не в аккаунте, то отправляет на логин
def order_product(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login', error='Пожалуйста, войдите в аккаунт для оформления заказа'))

    user_id = session['user_id']
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()

    conn.execute('''INSERT INTO orders (user_id, product_id, product_name, product_price) 
        VALUES (?, ?, ?, ?)''',(user_id, product_id, product['name'], product['price']))
    conn.commit()
    conn.close()
    return redirect(url_for('order_success', product_name=product['name']))


#Страница с успешной покупкой
@app.route('/order_success')
def order_success():
    product_name = request.args.get('product_name', '')
    return render_template('order_success.html', product_name=product_name)


#Страница с фидбеком
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    error_message = None
    success_message = None

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        message = request.form.get('message', '').strip()

        if not name or not email or not message:
            error_message = 'Заполните все поля'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            error_message = 'Введите корректный email'
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO feedback (name, email, message) VALUES (?, ?, ?)', (name, email, message))
            conn.commit()
            conn.close()
            success_message = 'Сообщение отправлено'

    return render_template('feedback.html', error=error_message, success=success_message)


#Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        is_valid = True
        valid, message = validate_username(username)
        if not valid:
            error_message = message
            is_valid = False
        if is_valid:
            valid, message = validate_email(email)
            if not valid:
                error_message = message
                is_valid = False
        if is_valid:
            valid, message = validate_password(password, confirm_password)
            if not valid:
                error_message = message
                is_valid = False
        if is_valid and is_username_exists(username):
            error_message = 'Это имя пользователя уже занято'
            is_valid = False
        if is_valid and is_email_exists(email):
            error_message = 'Этот email уже зарегистрирован'
            is_valid = False
        if is_valid:
            if add_user(username, email, password):
                return redirect(url_for('login_success'))
            else:
                error_message = 'Ошибка регистрации. Попробуйте позже.'
    return render_template('register.html', error=error_message)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = request.args.get('error', None)
    if request.method == 'POST':
        login_input = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        if not login_input or not password:
            error_message = 'Заполните все поля'
        else:
            user = verify_user(login_input, password)
            if user:
                session['user_id'] = user['id']
                return redirect(url_for('dashboard'))
            else:
                error_message = 'Неверное имя пользователя/email или пароль'
    return render_template('login.html', error=error_message)


@app.route('/login_success')
def login_success():
    return render_template('login_success.html')


@app.route('/dashboard')
@app.route('/dashboard/page/<int:page_num>')
def dashboard(page_num=1):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    per_page = 5
    offset = (page_num - 1) * per_page

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    #Получаем общее количество заказов пользователя
    total_orders = conn.execute('SELECT COUNT(*) FROM orders WHERE user_id = ?', (user_id,)).fetchone()[0]
    total_pages = (total_orders + per_page - 1) // per_page
    if total_pages == 0:
        total_pages = 1

    #Проверяем корректность номера страницы
    if page_num < 1:
        page_num = 1
    elif page_num > total_pages:
        page_num = total_pages
        offset = (page_num - 1) * per_page

    #Получаем заказы с пагинацией и правильной сортировкой
    orders = conn.execute('''
        SELECT * FROM orders 
        WHERE user_id = ? 
        ORDER BY order_date DESC, id DESC 
        LIMIT ? OFFSET ?
    ''', (user_id, per_page, offset)).fetchall()

    conn.close()

    if not user:
        session.clear()
        return redirect(url_for('login'))

    return render_template('dashboard.html',
                           user=user,
                           orders=orders,
                           current_page=page_num,
                           total_pages=total_pages,
                           total_orders=total_orders)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()

    if request.method == 'POST':
        new_email = request.form.get('email', '').strip().lower()
        valid, message = validate_email(new_email)
        if not valid:
            conn.close()
            return render_template('profile.html', user=user, error=message)
        if new_email != user['email'] and is_email_exists(new_email):
            conn.close()
            return render_template('profile.html', user=user, error='Этот email уже используется')
        conn.execute('UPDATE users SET email = ? WHERE id = ?', (new_email, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('profile.html', user=user, error=None)


# Контакты
@app.route('/contacts')
def contacts():
    contacts_info = {
        'phone': '+7000000000',
        'address': 'ул. Программирование, д. 55',
        'email': 'FlimShop@shop.ru',
        'work_hours': 'Пн-Пт: 10:00 - 20:00, Сб-Вс: 11:00 - 18:00',
        'instagram': '@flimshop_official',
        'telegram': '@flimshop_bot',
        'vk': 'vk.com/flimshop'}

    return render_template('contacts.html', contacts=contacts_info)


@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        return redirect(url_for('login', error='Войдите в аккаунт для просмотра корзины'))

    cart_items = get_cart(session['user_id'])
    total = get_cart_total(session['user_id'])

    return render_template('cart.html', cart_items=cart_items, total=total)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart_route(product_id):
    if 'user_id' not in session:
        return redirect(url_for('login', error='Войдите в аккаунт для добавления товаров'))

    quantity = request.form.get('quantity', 1, type=int)
    if quantity < 1:
        quantity = 1

    if add_to_cart(session['user_id'], product_id, quantity):
        return redirect(url_for('view_cart'))
    else:
        return redirect(url_for('index'))


@app.route('/update_cart/<int:cart_id>', methods=['POST'])
def update_cart_route(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    quantity = request.form.get('quantity', 1, type=int)
    if quantity <= 0:
        quantity = 1

    conn = get_db_connection()
    conn.execute('UPDATE cart SET quantity = ? WHERE id = ? AND user_id = ?',
                 (quantity, cart_id, session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('view_cart'))


@app.route('/remove_from_cart/<int:cart_id>')
def remove_from_cart_route(cart_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM cart WHERE id = ? AND user_id = ?', (cart_id, session['user_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login', error='Войдите в аккаунт для оформления заказа'))

    conn = get_db_connection()
    cart_items = conn.execute('''
        SELECT c.*, p.name, p.price 
        FROM cart c 
        JOIN products p ON c.product_id = p.id 
        WHERE c.user_id = ?
    ''', (session['user_id'],)).fetchall()

    if not cart_items:
        conn.close()
        return redirect(url_for('view_cart', error='Корзина пуста'))

    for item in cart_items:
        for i in range(item['quantity']):
            conn.execute('''
                INSERT INTO orders (user_id, product_id, product_name, product_price)
                VALUES (?, ?, ?, ?)
            ''', (session['user_id'], item['product_id'], item['name'], item['price']))

    conn.execute('DELETE FROM cart WHERE user_id = ?', (session['user_id'],))
    conn.commit()
    conn.close()

    return redirect(url_for('order_success', product_name='все товары'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)