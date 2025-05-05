from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from functools import wraps
from app import app, db
from models import User, Faculty, Group, Student, Teacher, Lesson, GradeType, Journal, Attendance, LessonGroup, Schedule, WeekType
from datetime import datetime
import logging
from utils import register_student, add_grade_and_attendance, mark_attendance_for_lesson, add_schedule_entry, get_group_statistics

# Настройка логирования
handler = logging.FileHandler('app.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.handlers = []
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Маршрут для добавления расписания
@app.route('/add_schedule', methods=['GET', 'POST'])
@login_required
def add_schedule():
    if current_user.role != 'admin':
        flash('Доступ только для администраторов.')
        return redirect(url_for('index'))

    faculties = Faculty.query.all()
    lessons = Lesson.query.all()
    if request.method == 'POST':
        faculty_id = request.form.get('faculty_id')
        week_type = request.form.get('week_type')
        day_of_week = request.form.get('day_of_week')
        time_slot = request.form.get('time_slot')
        lesson_id = request.form.get('lesson_id')
        if add_schedule_entry(faculty_id, week_type, day_of_week, time_slot, lesson_id):
            return redirect(url_for('view_schedule'))
        return redirect(url_for('add_schedule'))
    return render_template('add_schedule.html', faculties=faculties, lessons=lessons)

# Маршрут для просмотра расписания
@app.route('/view_schedule')
@login_required
def view_schedule():
    faculties = Faculty.query.all()
    schedules = Schedule.query.all()
    return render_template('view_schedule.html', faculties=faculties, schedules=schedules)

# Декоратор для проверки роли
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash('У вас нет доступа к этой странице.')
                app.logger.warning(
                    f'Неавторизованный доступ к {request.path} пользователем {current_user.username if current_user.is_authenticated else "неизвестным"}')
                return redirect(url_for('index'))
            app.logger.info(f'Пользователь {current_user.username} с ролью {role} получил доступ к {request.path}')
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Главная страница
@app.route('/')
def index():
    if not current_user.is_authenticated:
        app.logger.info('Неавторизованный пользователь посетил главную страницу')
        return render_template('index.html')
    app.logger.info(f'Пользователь {current_user.username} с ролью {current_user.role} посетил главную страницу')
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif current_user.role == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    elif current_user.role == 'student':
        return redirect(url_for('student_dashboard'))
    else:
        app.logger.warning(f'Неизвестная роль {current_user.role} для пользователя {current_user.username}')
        flash('Неизвестная роль. Пожалуйста, обратитесь к администратору.')
        return redirect(url_for('login'))


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        app.logger.info(f'Пользователь {current_user.username} уже авторизован, перенаправлен на главную')
        return redirect(url_for('index'))
    app.logger.info('Открыта страница регистрации')
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            email = request.form['email']
            if register_student(username, password, first_name, last_name, email):
                return redirect(url_for('login'))
            return redirect(url_for('register'))
        except KeyError:
            flash('Все поля, включая email, обязательны.', 'error')
            app.logger.warning('Попытка регистрации с отсутствующим полем')
            return redirect(url_for('register'))
    return render_template('register.html')


# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        app.logger.info(f'Пользователь {current_user.username} уже авторизован, перенаправлен на главную')
        return redirect(url_for('index'))
    app.logger.info('Открыта страница входа')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            app.logger.info(f'Пользователь {username} успешно вошел в систему')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль')
            app.logger.warning(f'Неудачная попытка входа для пользователя {username}')
            return redirect(url_for('login'))
    return render_template('login.html')


# Выход
@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    app.logger.info(f'Пользователь {username} вышел из системы')
    return redirect(url_for('login'))


# Экран администратора
@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    app.logger.info(f'Администратор {current_user.username} открыл панель управления')
    faculties = Faculty.query.all()
    groups = Group.query.all()
    students = Student.query.all()
    teachers = Teacher.query.all()
    lessons = Lesson.query.all()
    return render_template('admin_dashboard.html', faculties=faculties, groups=groups, students=students,
                           teachers=teachers, lessons=lessons)


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    # Список пользователей для администратора
    users = User.query.all() if current_user.role == 'admin' else []

    if request.method == 'POST':
        # Определяем, какая форма отправлена
        form_type = request.form.get('form_type')

        # Смена собственного пароля
        if form_type == 'own_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_user.check_password(old_password):
                flash('Неверный текущий пароль!')
                return redirect(url_for('change_password'))

            if new_password != confirm_password:
                flash('Новый пароль и подтверждение не совпадают!')
                return redirect(url_for('change_password'))

            if len(new_password) < 8:
                flash('Пароль должен содержать минимум 8 символов!')
                return redirect(url_for('change_password'))

            current_user.set_password(new_password)
            db.session.commit()
            flash('Ваш пароль успешно изменён!')
            return redirect(url_for('change_password'))

        # Смена пароля другого пользователя (для админа)
        elif form_type == 'user_password' and current_user.role == 'admin':
            user_id = request.form.get('user_id')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            user = User.query.get_or_404(user_id)
            if new_password != confirm_password:
                flash('Новый пароль и подтверждение не совпадают!')
                return redirect(url_for('change_password'))

            if len(new_password) < 8:
                flash('Пароль должен содержать минимум 8 символов!')
                return redirect(url_for('change_password'))

            user.set_password(new_password)
            db.session.commit()
            flash(f'Пароль пользователя {user.username} успешно изменён!')
            return redirect(url_for('change_password'))

    return render_template('change_password.html', users=users)


# Просмотр групп по факультету
@app.route('/admin/faculty/<int:faculty_id>/groups')
@role_required('admin')
def faculty_groups(faculty_id):
    faculty = Faculty.query.get_or_404(faculty_id)
    groups = Group.query.filter_by(faculty_id=faculty_id).all()
    app.logger.info(f'Администратор {current_user.username} просмотрел группы факультета {faculty.name}')
    return render_template('faculty_groups.html', faculty=faculty, groups=groups)


# Просмотр студентов по группе
@app.route('/admin/group/<int:group_id>/students')
@role_required('admin')
def group_students(group_id):
    group = Group.query.get_or_404(group_id)
    students = Student.query.filter_by(group_id=group_id).all()
    app.logger.info(f'Администратор {current_user.username} просмотрел студентов группы {group.name}')
    return render_template('group_students.html', group=group, students=students)


# Добавление факультета
@app.route('/admin/add_faculty', methods=['GET', 'POST'])
@role_required('admin')
def add_faculty():
    app.logger.info(f'Администратор {current_user.username} открыл страницу добавления факультета')
    faculties = Faculty.query.all()
    if request.method == 'POST':
        name = request.form['name']
        if Faculty.query.filter_by(name=name).first():
            flash('Факультет с таким названием уже существует')
            app.logger.warning(
                f'Попытка добавления существующего факультета {name} пользователем {current_user.username}')
            return redirect(url_for('add_faculty'))
        faculty = Faculty(name=name)
        db.session.add(faculty)
        db.session.commit()
        app.logger.info(f'Добавлен новый факультет {name} пользователем {current_user.username}')
        flash('Факультет добавлен')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_faculty.html', faculties=faculties)


# Добавление группы
@app.route('/admin/add_group', methods=['GET', 'POST'])
@role_required('admin')
def add_group():
    app.logger.info(f'Администратор {current_user.username} открыл страницу добавления группы')
    faculties = Faculty.query.all()
    teachers = Teacher.query.all()
    groups = Group.query.all()
    if request.method == 'POST':
        name = request.form['name']
        faculty_id = int(request.form['faculty_id'])
        teacher_id = request.form.get('teacher_id')
        group = Group(name=name, faculty_id=faculty_id, teacher_id=int(teacher_id) if teacher_id else None)
        db.session.add(group)
        db.session.commit()
        app.logger.info(
            f'Добавлена новая группа {name} на факультете {faculty_id} пользователем {current_user.username}')
        flash('Группа успешно добавлена!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_group.html', faculties=faculties, teachers=teachers, groups=groups)


@app.route('/admin/edit_group', methods=['GET', 'POST'])
@role_required('admin')
def edit_group():
    app.logger.info(f'Администратор {current_user.username} открыл страницу редактирования группы')
    groups = Group.query.all()
    faculties = Faculty.query.all()
    teachers = Teacher.query.all()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'select_group':
            group_id = int(request.form['group_id'])
            group = Group.query.get_or_404(group_id)
            students = Student.query.filter_by(group_id=group_id).all()
            app.logger.info(f'Администратор {current_user.username} выбрал группу {group.name} для редактирования')
            return render_template('edit_group.html', group=group, faculties=faculties, teachers=teachers,
                                   groups=groups, students=students)

        elif action == 'update_group':
            group_id = int(request.form['group_id'])
            group = Group.query.get_or_404(group_id)
            old_name = group.name
            group.name = request.form['name']
            group.faculty_id = int(request.form['faculty_id'])
            teacher_id = request.form.get('teacher_id')
            group.teacher_id = int(teacher_id) if teacher_id else None
            db.session.commit()
            app.logger.info(
                f'Группа {old_name} обновлена пользователем {current_user.username} (новое имя: {group.name})')
            flash('Группа успешно обновлена!')

        elif action == 'edit_student':
            student_id = int(request.form['student_id'])
            student = Student.query.get_or_404(student_id)
            student.first_name = request.form['first_name']
            student.last_name = request.form['last_name']
            db.session.commit()
            app.logger.info(
                f'Информация о студенте {student.first_name} {student.last_name} обновлена пользователем {current_user.username}')
            flash('Информация о студенте обновлена!')

        elif action == 'delete_student':
            student_id = int(request.form['student_id'])
            student = Student.query.get_or_404(student_id)
            student_name = f'{student.first_name} {student.last_name}'
            db.session.delete(student)
            db.session.commit()
            app.logger.info(f'Студент {student_name} удален пользователем {current_user.username}')
            flash('Студент успешно удалён!')

        return redirect(url_for('edit_group'))

    return render_template('edit_group.html', groups=groups)


# Добавление студента в группу
@app.route('/admin/add_student_in_group', methods=['GET', 'POST'])
@role_required('admin')
def add_student_in_group():
    app.logger.info(f'Администратор {current_user.username} открыл страницу добавления студента в группу')
    users = User.query.filter_by(role='student').all()
    groups = Group.query.all()
    students = Student.query.all()

    user_data = []
    for user in users:
        student = Student.query.filter_by(user_id=user.id).first()
        if student:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'first_name': student.first_name,
                'last_name': student.last_name
            })
        else:
            user_data.append({
                'id': user.id,
                'username': user.username,
                'first_name': '',
                'last_name': ''
            })

    if request.method == 'POST':
        user_id = int(request.form['user_id'])
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        group_id = int(request.form['group_id'])

        student = Student.query.filter_by(user_id=user_id).first()
        if student:
            student.group_id = group_id
            app.logger.info(
                f'Обновлена группа студента {student.first_name} {student.last_name} на {group_id} пользователем {current_user.username}')
            flash('Группа студента успешно обновлена!')
        else:
            student = Student(user_id=user_id, first_name=first_name, last_name=last_name, group_id=group_id)
            db.session.add(student)
            app.logger.info(
                f'Добавлен студент {first_name} {last_name} в группу {group_id} пользователем {current_user.username}')
            flash('Студент успешно добавлен!')

        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('add_student_in_group.html', users=user_data, groups=groups, students=students)


# Маршрут для добавления урока
@app.route('/admin/add_lesson', methods=['GET', 'POST'])
def add_lesson():
    app.logger.info(f'Администратор {current_user.username} открыл страницу добавления урока')
    teachers = Teacher.query.all()
    lessons = Lesson.query.all()
    if request.method == 'POST':
        name = request.form['name']
        teacher_id = int(request.form['teacher_id'])
        lesson = Lesson(name=name, teacher_id=teacher_id)
        db.session.add(lesson)
        db.session.commit()
        app.logger.info(
            f'Добавлен новый урок {name} для преподавателя {teacher_id} пользователем {current_user.username}')
        flash('Урок успешно добавлен!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_lesson.html', teachers=teachers, lessons=lessons)


@app.route('/admin/link_lesson_group', methods=['GET', 'POST'])
@role_required('admin')
def link_lesson_group():
    app.logger.info(f'Администратор {current_user.username} открыл страницу связи урока с группой')
    lessons = Lesson.query.all()
    groups = Group.query.all()
    if request.method == 'POST':
        lesson_id = int(request.form['lesson_id'])
        group_id = int(request.form['group_id'])
        if LessonGroup.query.filter_by(lesson_id=lesson_id, group_id=group_id).first():
            flash('Эта связь уже существует!')
            app.logger.warning(
                f'Попытка добавить существующую связь урока {lesson_id} с группой {group_id} пользователем {current_user.username}')
        else:
            new_link = LessonGroup(lesson_id=lesson_id, group_id=group_id)
            db.session.add(new_link)
            db.session.commit()
            app.logger.info(
                f'Добавлена связь урока {lesson_id} с группой {group_id} пользователем {current_user.username}')
            flash('Связь между уроком и группой успешно добавлена!')
        return redirect(url_for('admin_dashboard'))
    return render_template('link_lesson_group.html', lessons=lessons, groups=groups)


# Экран преподавателя
@app.route('/teacher/dashboard')
@role_required('teacher')
def teacher_dashboard():
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Сначала зарегистрируйтесь как преподаватель у администратора.')
        app.logger.warning(f'Преподаватель {current_user.username} не зарегистрирован')
        return render_template('teacher_dashboard.html', teacher=None, lessons=[], groups=[])

    lessons = Lesson.query.filter_by(teacher_id=teacher.id).all()
    lesson_groups = list(set(group for lesson in lessons for group in lesson.groups))
    teacher_groups = Group.query.filter_by(teacher_id=teacher.id).all()
    groups = list(set(lesson_groups + teacher_groups))
    groups.sort(key=lambda x: x.name)
    app.logger.info(f'Преподаватель {current_user.username} открыл панель управления')
    return render_template('teacher_dashboard.html', teacher=teacher, lessons=lessons, groups=groups)

# Добавление оценки
@app.route('/teacher/add_grade/<int:lesson_id>', methods=['GET', 'POST'])
@role_required('teacher')
def add_grade(lesson_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != teacher.id:
        flash('Вы не можете добавлять оценки для этого урока.')
        app.logger.warning(f'Преподаватель {current_user.username} попытался добавить оценку для урока {lesson_id}')
        return redirect(url_for('teacher_dashboard'))

    lessons = Lesson.query.filter_by(teacher_id=teacher.id).all()
    groups = list(set(group for lesson in lessons for group in lesson.groups))
    students = Student.query.filter(Student.group_id.in_([group.id for group in lesson.groups])).all()
    grade_types = GradeType.query.all()
    if request.method == 'POST':
        student_id = int(request.form['student_id'])
        grade_id = int(request.form['grade_id'])
        date_str = request.form['date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if add_grade_and_attendance(student_id, lesson_id, grade_id, date_obj):
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('add_grade', lesson_id=lesson_id))
    return render_template('add_grade.html', lesson=lesson, students=students, grade_types=grade_types, lessons=lessons, groups=groups)


# Список студентов урока
@app.route('/teacher/lesson/<int:lesson_id>/students', methods=['GET'])
@role_required('teacher')
def teacher_lesson_students(lesson_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != teacher.id:
        flash('Вы не можете просматривать студентов этого урока.')
        app.logger.warning(f'Преподаватель {current_user.username} попытался просмотреть студентов урока {lesson_id}, к которому не имеет доступа')
        return redirect(url_for('teacher_dashboard'))

    lessons = Lesson.query.filter_by(teacher_id=teacher.id).all()
    groups = list(set(group for lesson in lessons for group in lesson.groups))
    group_id = request.args.get('group_id', type=int)
    if group_id:
        students = Student.query.filter_by(group_id=group_id).filter(
            Student.group_id.in_([group.id for group in lesson.groups])).all()
    else:
        students = Student.query.filter(Student.group_id.in_([group.id for group in lesson.groups])).all()
    app.logger.info(f'Преподаватель {current_user.username} просмотрел студентов урока {lesson.name}')
    return render_template('teacher_lesson_students.html', lesson=lesson, students=students, groups=groups, lessons=lessons, selected_group_id=group_id)

# Отметка посещаемости
@app.route('/teacher/mark_attendance/<int:lesson_id>', methods=['GET', 'POST'])
@role_required('teacher')
def mark_attendance(lesson_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != teacher.id:
        flash('Вы не можете отмечать посещаемость для этого урока.')
        app.logger.warning(f'Преподаватель {current_user.username} попытался отметить посещаемость урока {lesson_id}')
        return redirect(url_for('teacher_dashboard'))

    lessons = Lesson.query.filter_by(teacher_id=teacher.id).all()
    groups = list(set(group for lesson in lessons for group in lesson.groups))
    students = Student.query.filter(Student.group_id.in_([group.id for group in lesson.groups])).all()
    if request.method == 'POST':
        date_str = request.form['date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        status_dict = {key.split('_')[1]: value for key, value in request.form.items() if key.startswith('status_')}
        if mark_attendance_for_lesson(lesson_id, date_obj, status_dict):
            return redirect(url_for('teacher_dashboard'))
        return redirect(url_for('mark_attendance', lesson_id=lesson_id))
    return render_template('mark_attendance.html', lesson=lesson, students=students, lessons=lessons, groups=groups)

# Статистика группы
@app.route('/teacher/group_statistics/<int:group_id>')
@role_required('teacher')
def group_statistics(group_id):
    teacher = Teacher.query.filter_by(user_id=current_user.id).first()
    if not teacher:
        flash('Сначала зарегистрируйтесь как преподаватель у администратора.')
        app.logger.warning(f'Преподаватель {current_user.username} не зарегистрирован')
        return redirect(url_for('teacher_dashboard'))

    lessons = Lesson.query.filter_by(teacher_id=teacher.id).all()
    groups = list(set(group for lesson in lessons for group in lesson.groups))
    group_stats = get_group_statistics(group_id, teacher.id)
    if not group_stats:
        return redirect(url_for('teacher_dashboard'))
    return render_template('group_statistics.html', group=Group.query.get(group_id), group_stats=group_stats, lessons=lessons, groups=groups)


# Экран студента
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Вы еще не зарегистрированы как студент.')
        app.logger.warning(f'Студент {current_user.username} не зарегистрирован')
        return render_template('student_dashboard.html', student=None, lessons=[], grades=[])

    lessons = Lesson.query.join(LessonGroup).filter(LessonGroup.group_id == student.group_id).all()
    grades = Journal.query.filter_by(student_id=student.id).all()
    app.logger.info(f'Студент {current_user.username} открыл панель управления')
    return render_template('student_dashboard.html', student=student, lessons=lessons, grades=grades)


@app.route('/student/grades', methods=['GET'])
@login_required
def student_grades():
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Вы ещё не зарегистрированы как студент.')
        app.logger.warning(f'Студент {current_user.username} не зарегистрирован')
        return redirect(url_for('student_dashboard'))

    lesson_id = request.args.get('lesson_id', type=int)
    lessons = Lesson.query.join(Journal).filter(Journal.student_id == student.id).distinct().all()
    if lesson_id:
        grades = Journal.query.filter_by(student_id=student.id, lesson_id=lesson_id).all()
    else:
        grades = Journal.query.filter_by(student_id=student.id).all()
    app.logger.info(
        f'Студент {current_user.username} просмотрел свои оценки с фильтром по уроку {lesson_id if lesson_id else "все уроки"}')
    return render_template('student_grades.html', grades=grades, lessons=lessons, selected_lesson=lesson_id)


# Добавление преподавателя
@app.route('/admin/add_teacher', methods=['GET', 'POST'])
@role_required('admin')
def add_teacher():
    app.logger.info(f'Администратор {current_user.username} открыл страницу добавления преподавателя')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        role = 'teacher'
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует')
            app.logger.warning(
                f'Попытка добавления существующего пользователя {username} администратором {current_user.username}')
            return redirect(url_for('add_teacher'))
        user = User(username=username, role=role, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        teacher = Teacher(user_id=user.id, first_name=first_name, last_name=last_name)
        db.session.add(teacher)
        db.session.commit()
        app.logger.info(f'Администратор {current_user.username} добавил нового преподавателя {username}')
        flash('Преподаватель успешно добавлен!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_teacher.html')


@app.route('/student/attendance')
@login_required
def student_attendance():
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Вы ещё не зарегистрированы как студент.')
        app.logger.warning(f'Студент {current_user.username} не зарегистрирован')
        return redirect(url_for('student_dashboard'))

    attendances = Attendance.query.filter_by(student_id=student.id).all()
    lessons = {lesson.id: lesson.name for lesson in Lesson.query.all()}
    app.logger.info(f'Студент {current_user.username} просмотрел свою посещаемость')
    return render_template('student_attendance.html', attendances=attendances, lessons=lessons)


# Обработка ошибок (например, 404)
@app.errorhandler(404)
def page_not_found(e):
    app.logger.error(
        f'Страница не найдена: {request.url} (пользователь: {current_user.username if current_user.is_authenticated else "неизвестный"})')
    return render_template('404.html'), 404