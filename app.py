from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.sql import text

# Создаем приложение Flask
app = Flask(__name__)

# Секретный ключ для защиты сессий
app.config['SECRET_KEY'] = '0983969059563e68ac235606a8bf7ff6359b2d6b468206f94de9f9cf06eeb862'

# Указываем путь к базе данных SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

# Инициализируем объект SQLAlchemy для работы с базой данных
db = SQLAlchemy(app)

# Настраиваем Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Указываем маршрут для страницы входа

from routes import *

# Функция для загрузки пользователя по ID
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    db.session.execute(text('PRAGMA foreign_keys = ON;'))
    db.session.commit()
    db.create_all()

# Запускаем приложение
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)