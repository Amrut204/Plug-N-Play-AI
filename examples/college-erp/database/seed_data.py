import sqlite3
import os

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "college.db")


def init_and_seed_college_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Students Table
    cursor.execute("""
    CREATE TABLE students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        year_of_study INTEGER NOT NULL,
        cgpa REAL NOT NULL,
        email TEXT NOT NULL
    );
    """)

    # 2. Attendance Table
    cursor.execute("""
    CREATE TABLE attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        total_classes INTEGER NOT NULL,
        attended_classes INTEGER NOT NULL,
        attendance_percentage REAL NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );
    """)

    # 3. Marks Table
    cursor.execute("""
    CREATE TABLE marks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL NOT NULL,
        grade TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );
    """)

    # 4. Fees Table
    cursor.execute("""
    CREATE TABLE fees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        total_fees REAL NOT NULL,
        amount_paid REAL NOT NULL,
        pending_due REAL NOT NULL,
        due_date TEXT NOT NULL,
        FOREIGN KEY (student_id) REFERENCES students(student_id)
    );
    """)

    # Seed Data for Students
    cursor.execute("""
    INSERT INTO students (student_id, name, department, year_of_study, cgpa, email) VALUES
    ('STU_1001', 'Alex Johnson', 'Computer Science and Engineering', 3, 8.4, 'alex.j@college.edu'),
    ('STU_1002', 'Sophia Davis', 'Computer Science and Engineering', 3, 9.2, 'sophia.d@college.edu'),
    ('STU_1003', 'Liam Martinez', 'Mechanical Engineering', 2, 7.1, 'liam.m@college.edu');
    """)

    # Seed Attendance
    # Alex: 71% in Database Systems (Below 75%), 82% in Data Structures
    cursor.execute("""
    INSERT INTO attendance (student_id, subject, total_classes, attended_classes, attendance_percentage) VALUES
    ('STU_1001', 'Database Systems', 45, 32, 71.1),
    ('STU_1001', 'Data Structures & Algorithms', 50, 41, 82.0),
    ('STU_1001', 'Computer Networks', 40, 34, 85.0),
    ('STU_1002', 'Database Systems', 45, 42, 93.3),
    ('STU_1002', 'Data Structures & Algorithms', 50, 47, 94.0);
    """)

    # Seed Marks
    cursor.execute("""
    INSERT INTO marks (student_id, subject, score, max_score, grade) VALUES
    ('STU_1001', 'Database Systems', 88.0, 100.0, 'A'),
    ('STU_1001', 'Data Structures & Algorithms', 92.5, 100.0, 'A+'),
    ('STU_1002', 'Database Systems', 96.0, 100.0, 'O');
    """)

    # Seed Fees
    cursor.execute("""
    INSERT INTO fees (student_id, total_fees, amount_paid, pending_due, due_date) VALUES
    ('STU_1001', 75000.0, 75000.0, 0.0, '2026-09-15'),
    ('STU_1002', 75000.0, 60000.0, 15000.0, '2026-09-15');
    """)

    conn.commit()
    conn.close()
    print(f"College database seeded successfully at {DB_PATH}")


if __name__ == "__main__":
    init_and_seed_college_db()
