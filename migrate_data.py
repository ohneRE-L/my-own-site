from app import app, db, User, Faculty, Group, Student, Teacher, Lesson, GradeType, Journal, Attendance, LessonGroup
import json
from datetime import date

def export_data():
    with app.app_context():
        data = {
            "users": [u.__dict__ for u in User.query.all()],
            "faculties": [f.__dict__ for f in Faculty.query.all()],
            "groups": [g.__dict__ for g in Group.query.all()],
            "students": [s.__dict__ for s in Student.query.all()],
            "teachers": [t.__dict__ for t in Teacher.query.all()],
            "lessons": [l.__dict__ for l in Lesson.query.all()],
            "grade_types": [gt.__dict__ for gt in GradeType.query.all()],
            "journal": [j.__dict__ for j in Journal.query.all()],
            "attendances": [a.__dict__ for a in Attendance.query.all()],
            "lesson_groups": [lg.__dict__ for lg in LessonGroup.query.all()],
        }
        for table in data.values():
            for row in table:
                row.pop('_sa_instance_state', None)
                for key, value in row.items():
                    if isinstance(value, date):
                        row[key] = value.isoformat()
        with open('backup.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Данные успешно экспортированы в backup.json")

def import_data():
    with app.app_context():
        with open('backup.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        db.drop_all()
        db.create_all()

        id_mapping = {
            'users': {},
            'faculties': {},
            'groups': {},
            'students': {},
            'teachers': {},
            'lessons': {},
            'grade_types': {}
        }

        # 1. Users
        for user_data in data['users']:
            old_id = user_data['id']
            user_data.pop('id')
            user = User(**user_data)
            db.session.add(user)
            db.session.flush()
            id_mapping['users'][old_id] = user.id

        # 2. Faculties
        for faculty_data in data['faculties']:
            old_id = faculty_data['id']
            faculty_data.pop('id')
            faculty = Faculty(**faculty_data)
            db.session.add(faculty)
            db.session.flush()
            id_mapping['faculties'][old_id] = faculty.id

        # 3. Teachers
        for teacher_data in data['teachers']:
            old_id = teacher_data['id']
            teacher_data['user_id'] = id_mapping['users'][teacher_data['user_id']]
            teacher_data.pop('id')
            teacher = Teacher(**teacher_data)
            db.session.add(teacher)
            db.session.flush()
            id_mapping['teachers'][old_id] = teacher.id

        # 4. Groups (с обработкой отсутствующих факультетов)
        for group_data in data['groups']:
            old_id = group_data['id']
            faculty_id = group_data['faculty_id']
            # Если faculty_id отсутствует в id_mapping, создаём заглушку
            if faculty_id not in id_mapping['faculties']:
                faculty = Faculty(name=f"Неизвестный факультет (ID {faculty_id})")
                db.session.add(faculty)
                db.session.flush()
                id_mapping['faculties'][faculty_id] = faculty.id
            group_data['faculty_id'] = id_mapping['faculties'][faculty_id]
            if group_data['teacher_id']:
                group_data['teacher_id'] = id_mapping['teachers'][group_data['teacher_id']]
            group_data.pop('id')
            group = Group(**group_data)
            db.session.add(group)
            db.session.flush()
            id_mapping['groups'][old_id] = group.id

        # 5. Students
        for student_data in data['students']:
            old_id = student_data['id']
            student_data['user_id'] = id_mapping['users'][student_data['user_id']]
            if student_data['group_id']:
                student_data['group_id'] = id_mapping['groups'][student_data['group_id']]
            student_data.pop('id')
            student = Student(**student_data)
            db.session.add(student)
            db.session.flush()
            id_mapping['students'][old_id] = student.id

        # 6. Lessons
        for lesson_data in data['lessons']:
            old_id = lesson_data['id']
            lesson_data['teacher_id'] = id_mapping['teachers'][lesson_data['teacher_id']]
            lesson_data.pop('id')
            lesson = Lesson(**lesson_data)
            db.session.add(lesson)
            db.session.flush()
            id_mapping['lessons'][old_id] = lesson.id

        # 7. GradeTypes
        for grade_type_data in data['grade_types']:
            old_id = grade_type_data['id']
            grade_type_data.pop('id')
            grade_type = GradeType(**grade_type_data)
            db.session.add(grade_type)
            db.session.flush()
            id_mapping['grade_types'][old_id] = grade_type.id

        # 8. Journal
        for journal_data in data['journal']:
            journal_data['student_id'] = id_mapping['students'][journal_data['student_id']]
            journal_data['lesson_id'] = id_mapping['lessons'][journal_data['lesson_id']]
            if journal_data['grade_id']:
                journal_data['grade_id'] = id_mapping['grade_types'][journal_data['grade_id']]
            if 'date' in journal_data:
                journal_data['date'] = date.fromisoformat(journal_data['date'])
            journal_data.pop('id')
            journal = Journal(**journal_data)
            db.session.add(journal)

        # 9. Attendances
        for attendance_data in data['attendances']:
            attendance_data['student_id'] = id_mapping['students'][attendance_data['student_id']]
            attendance_data['lesson_id'] = id_mapping['lessons'][attendance_data['lesson_id']]
            if 'date' in attendance_data:
                attendance_data['date'] = date.fromisoformat(attendance_data['date'])
            attendance_data.pop('id')
            attendance = Attendance(**attendance_data)
            db.session.add(attendance)

        # 10. LessonGroups
        for lesson_group_data in data['lesson_groups']:
            lesson_group_data['lesson_id'] = id_mapping['lessons'][lesson_group_data['lesson_id']]
            lesson_group_data['group_id'] = id_mapping['groups'][lesson_group_data['group_id']]
            lesson_group_data.pop('id')
            lesson_group = LessonGroup(**lesson_group_data)
            db.session.add(lesson_group)

        db.session.commit()
        print("Данные успешно импортированы из backup.json")

if __name__ == "__main__":
    # export_data()
    import_data()