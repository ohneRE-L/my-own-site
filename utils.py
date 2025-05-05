from flask import flash
from werkzeug.security import generate_password_hash
from app import db, app
from models import User, Student, Journal, Attendance, LessonGroup, Schedule, Lesson, WeekType, Group

def register_student(username, password, first_name, last_name, email):
    try:
        if not email:
            flash('Email обязателен.', 'error')
            app.logger.warning(f'Попытка регистрации без email для имени {username}')
            return False
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя уже занято.', 'error')
            app.logger.warning(f'Попытка регистрации с существующим именем {username}')
            return False
        if User.query.filter_by(email=email).first():
            flash('Email уже зарегистрирован.', 'error')
            app.logger.warning(f'Попытка регистрации с существующим email {email}')
            return False

        user = User(
            username=username,
            password_hash=generate_password_hash(password),
            email=email,
            role='student'
        )
        db.session.add(user)
        db.session.commit()

        student = Student(
            first_name=first_name,
            last_name=last_name,
            user_id=user.id
        )
        db.session.add(student)
        db.session.commit()

        flash('Регистрация успешна!', 'success')
        app.logger.info(f'Зарегистрирован новый студент {username} с email {email}')
        return True
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка регистрации: {str(e)}', 'error')
        app.logger.error(f'Ошибка регистрации студента {username}: {str(e)}')
        return False


def add_grade_and_attendance(student_id, lesson_id, grade_id, date, status='present'):
    """
    Добавляет или обновляет оценку и посещаемость для студента на занятии.
    Эквивалент хранимой процедуры для управления оценками и посещаемостью.
    """
    try:
        student = Student.query.get(student_id)
        if not student:
            flash('Студент не найден.', 'error')
            app.logger.warning(f'Попытка добавить оценку для несуществующего студента {student_id}')
            return False

        journal_entry = Journal.query.filter_by(student_id=student_id, lesson_id=lesson_id, date=date).first()
        if journal_entry:
            journal_entry.grade_id = grade_id
            flash('Оценка обновлена.', 'success')
            app.logger.info(f'Оценка студента {student_id} обновлена для урока {lesson_id} на {date}')
        else:
            journal_entry = Journal(student_id=student_id, lesson_id=lesson_id, grade_id=grade_id, date=date)
            db.session.add(journal_entry)
            flash('Оценка добавлена.', 'success')
            app.logger.info(f'Оценка добавлена студенту {student_id} для урока {lesson_id} на {date}')

        attendance_entry = Attendance.query.filter_by(student_id=student_id, lesson_id=lesson_id, date=date).first()
        if not attendance_entry:
            attendance_entry = Attendance(student_id=student_id, lesson_id=lesson_id, date=date, status=status)
            db.session.add(attendance_entry)
            app.logger.info(f'Добавлено присутствие для студента {student_id} на уроке {lesson_id} за {date}')

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка добавления оценки: {str(e)}', 'error')
        app.logger.error(f'Ошибка добавления оценки для студента {student_id}: {str(e)}')
        return False


def mark_attendance_for_lesson(lesson_id, date, status_dict):
    """
    Отмечает посещаемость для всех студентов на занятии.
    Эквивалент хранимой процедуры для массовой отметки посещаемости.
    """
    try:
        # Получаем студентов, связанных с уроком через LessonGroup и Group
        students = db.session.query(Student). \
            join(Group, Student.group_id == Group.id). \
            join(LessonGroup, LessonGroup.group_id == Group.id). \
            filter(LessonGroup.lesson_id == lesson_id).all()

        if not students:
            flash('Студенты для этого урока не найдены.', 'error')
            app.logger.warning(f'Не найдены студенты для урока {lesson_id}')
            return False

        for student in students:
            status = status_dict.get(str(student.id), 'absent')
            attendance = Attendance.query.filter_by(student_id=student.id, lesson_id=lesson_id, date=date).first()
            if attendance:
                attendance.status = status
            else:
                attendance = Attendance(student_id=student.id, lesson_id=lesson_id, date=date, status=status)
                db.session.add(attendance)

        db.session.commit()
        flash('Посещаемость успешно отмечена.', 'success')
        app.logger.info(f'Посещаемость отмечена для урока {lesson_id} на {date}')
        return True
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка отметки посещаемости: {str(e)}', 'error')
        app.logger.error(f'Ошибка отметки посещаемости для урока {lesson_id}: {str(e)}')
        return False


def add_schedule_entry(faculty_id, week_type, day_of_week, time_slot, lesson_id):
    """
    Добавляет новую запись в расписание, синхронизируя название урока.
    Эквивалент хранимой процедуры для добавления расписания.
    Использует NUMERATOR/DENOMINATOR для week_type.
    """
    try:
        if not all([faculty_id, week_type, day_of_week, time_slot, lesson_id]):
            flash('Все поля обязательны.', 'error')
            app.logger.warning(f'Попытка добавить расписание с пустыми полями')
            return False

        try:
            week_type = WeekType[week_type.upper()]
        except KeyError:
            flash('Неверный тип недели. Допустимые значения: NUMERATOR, DENOMINATOR.', 'error')
            app.logger.warning(f'Неверный тип недели: {week_type}')
            return False

        lesson = Lesson.query.get(lesson_id)
        if not lesson:
            flash('Выбранный урок не существует.', 'error')
            app.logger.warning(f'Попытка добавить расписание для несуществующего урока {lesson_id}')
            return False

        schedule = Schedule(
            faculty_id=faculty_id,
            week_type=week_type,
            day_of_week=day_of_week,
            time_slot=time_slot,
            lesson_name=lesson.name
        )
        db.session.add(schedule)
        db.session.commit()
        flash('Расписание успешно добавлено!', 'success')
        app.logger.info(f'Добавлено расписание для урока {lesson.name} на факультете {faculty_id}')
        return True
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка добавления расписания: {str(e)}', 'error')
        app.logger.error(f'Ошибка добавления расписания: {str(e)}')
        return False


def get_group_statistics(group_id, teacher_id):
    """
    Собирает статистику по группе: оценки и посещаемость студентов.
    Эквивалент хранимой процедуры для получения статистики группы.
    """
    try:
        group = Group.query.get_or_404(group_id)
        lesson_group_ids = [g.id for lesson in Lesson.query.filter_by(teacher_id=teacher_id).all() for g in
                            lesson.groups]
        if group_id not in lesson_group_ids and group.teacher_id != teacher_id:
            flash('У вас нет доступа к статистике этой группы.', 'error')
            app.logger.warning(f'Попытка доступа к статистике группы {group_id} преподавателем {teacher_id}')
            return None

        group_lessons = Lesson.query.join(LessonGroup).filter(LessonGroup.group_id == group_id,
                                                              Lesson.teacher_id == teacher_id).all()
        students = Student.query.filter_by(group_id=group_id).all()
        group_stats = {'lessons': group_lessons, 'students': students, 'student_stats': {}}

        for lesson in group_stats['lessons']:
            attendance_dates = db.session.query(Attendance.date).filter_by(lesson_id=lesson.id).distinct().order_by(
                Attendance.date).all()
            attendance_dates = [date[0] for date in attendance_dates]
            for student in group_stats['students']:
                attendances = Attendance.query.filter_by(student_id=student.id, lesson_id=lesson.id).all()
                attendance_dict = {attendance.date: attendance.status for attendance in attendances}
                attendance_statuses = [(date, attendance_dict.get(date, 'Неизвестно')) for date in attendance_dates]
                grades = Journal.query.filter_by(student_id=student.id, lesson_id=lesson.id).all()
                student_grades = [(grade.date, grade.grade_type.value) for grade in grades]
                if student.id not in group_stats['student_stats']:
                    group_stats['student_stats'][student.id] = {}
                group_stats['student_stats'][student.id][lesson.id] = {
                    'lesson_name': lesson.name,
                    'attendance': attendance_statuses,
                    'grades': student_grades
                }

        app.logger.info(f'Получена статистика группы {group_id} для преподавателя {teacher_id}')
        return group_stats
    except Exception as e:
        flash(f'Ошибка получения статистики: {str(e)}', 'error')
        app.logger.error(f'Ошибка получения статистики группы {group_id}: {str(e)}')
        return None