import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config
from database.models import Base, User, Department, Grievance, GrievanceStatusHistory, Feedback, DuplicateMatches
from datetime import datetime, timedelta

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, connect_args={"check_same_thread": False})
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    Base.metadata.create_all(bind=engine)

def seed_demo_data():
    """Seeds initial departments, users, and realistic grievances for demonstration."""
    session = db_session()
    
    # Check if already seeded
    if session.query(Department).first():
        return

    # 1. Seed Departments
    departments_data = [
        ("Academic Office", "Handles course enrollments, lecture timetables, faculty coordination, and attendance disputes."),
        ("Examination Cell", "Manages semester exams, hall tickets, grade sheets, revaluation, and exam scheduling."),
        ("Hostel Administration", "Responsible for student residential blocks, room allocations, mess food, and hygiene."),
        ("Transport Office", "Oversees college bus operations, route allocations, driver schedules, and transport safety."),
        ("Maintenance Department", "Manages campus physical infrastructure, electrical, plumbing, lab equipment, and repairs."),
        ("Library Administration", "Oversees print collection, digital journal subscriptions, study spaces, and library services."),
        ("Administrative Office", "Processes student certificates, fee verifications, scholarship forms, and official identity cards.")
    ]

    dept_map = {}
    for name, desc in departments_data:
        dept = Department(department_name=name, description=desc)
        session.add(dept)
        session.flush()
        dept_map[name] = dept.department_id

    # 2. Seed Users
    # Admin
    admin_user = User(
        name="Dean of Student Affairs",
        email="admin@college.edu",
        role="admin"
    )
    admin_user.set_password("admin123")
    session.add(admin_user)

    # Department Staff
    staff_data = [
        ("Er. Rajesh Kumar", "maintenance@college.edu", "staff", dept_map["Maintenance Department"]),
        ("Smt. Sunita Rao", "hostel@college.edu", "staff", dept_map["Hostel Administration"]),
        ("Dr. Arvind Sharma", "academic@college.edu", "staff", dept_map["Academic Office"]),
        ("Prof. Meenakshi Sundaram", "exam@college.edu", "staff", dept_map["Examination Cell"]),
        ("Shri Suresh Nair", "transport@college.edu", "staff", dept_map["Transport Office"]),
        ("Mrs. Kavita Verma", "library@college.edu", "staff", dept_map["Library Administration"]),
        ("Mr. Anand Kulkarni", "admoffice@college.edu", "staff", dept_map["Administrative Office"]),
    ]

    staff_map = {}
    for name, email, role, dept_id in staff_data:
        u = User(name=name, email=email, role=role, department_id=dept_id)
        u.set_password("staff123")
        session.add(u)
        session.flush()
        staff_map[dept_id] = u.user_id

    # Students
    students_data = [
        ("Rahul Sharma", "student@college.edu", "student"),
        ("Priya Patel", "priya@college.edu", "student"),
        ("Alex George", "alex@college.edu", "student")
    ]
    student_users = []
    for name, email, role in students_data:
        s = User(name=name, email=email, role=role)
        s.set_password("student123")
        session.add(s)
        session.flush()
        student_users.append(s)

    session.commit()

    # 3. Seed Realistic Grievances for Dashboards & Analytics Demonstration
    now = datetime.utcnow()
    sample_grievances = [
        {
            "student_id": student_users[0].user_id,
            "title": "Frequent power trip and faulty switches in Lab 3",
            "description": "In Computer Lab 3, several power plugs on row 4 keep sparking and tripping the main circuit breaker during practical sessions.",
            "predicted_category": "Infrastructure",
            "predicted_priority": "High",
            "predicted_sentiment": "Negative",
            "category_confidence": 0.94,
            "assigned_dept": dept_map["Maintenance Department"],
            "assigned_staff": staff_map[dept_map["Maintenance Department"]],
            "status": "In Progress",
            "created_offset_days": 3,
            "history": [
                ("Submitted", "Assigned", "Automatically categorized as Infrastructure and routed to Maintenance Dept."),
                ("Assigned", "In Progress", "Electrician team deployed to inspect circuit breakers.")
            ]
        },
        {
            "student_id": student_users[1].user_id,
            "title": "Water shortage in Hostel Block B third floor",
            "description": "There has been no running water in Hostel Block B 3rd floor bathrooms since yesterday morning. It is causing extreme inconvenience to all residents.",
            "predicted_category": "Hostel",
            "predicted_priority": "High",
            "predicted_sentiment": "Negative",
            "category_confidence": 0.96,
            "assigned_dept": dept_map["Hostel Administration"],
            "assigned_staff": staff_map[dept_map["Hostel Administration"]],
            "status": "Resolved",
            "created_offset_days": 5,
            "resolved_offset_days": 2,
            "history": [
                ("Submitted", "Assigned", "AI classified as Hostel grievance; routed to Hostel Admin."),
                ("Assigned", "In Progress", "Plumbing contractor summoned to fix booster pump."),
                ("In Progress", "Resolved", "Overhead booster pump repaired and continuous water supply restored.")
            ],
            "feedback": (5, "Thank you for the quick resolution within 24 hours!")
        },
        {
            "student_id": student_users[0].user_id,
            "title": "Semester 4 mark sheet grade mismatch in Database Systems",
            "description": "My grade on the provisional result portal shows B+, but the re-evaluated paper score was updated to A. Kindly rectify the grade in the official transcript.",
            "predicted_category": "Examination",
            "predicted_priority": "Medium",
            "predicted_sentiment": "Neutral",
            "category_confidence": 0.91,
            "assigned_dept": dept_map["Examination Cell"],
            "assigned_staff": staff_map[dept_map["Examination Cell"]],
            "status": "In Progress",
            "created_offset_days": 4,
            "history": [
                ("Submitted", "Assigned", "Dispatched to Examination Cell for verification."),
                ("Assigned", "In Progress", "Physical revaluation ledger requested from evaluators.")
            ]
        },
        {
            "student_id": student_users[2].user_id,
            "title": "Route 7 college bus arriving 30 minutes late consistently",
            "description": "The college bus on Route 7 (North Campus line) has been arriving 25 to 30 minutes late every morning for the past week, making us miss the first lecture.",
            "predicted_category": "Transport",
            "predicted_priority": "Medium",
            "predicted_sentiment": "Negative",
            "category_confidence": 0.89,
            "assigned_dept": dept_map["Transport Office"],
            "assigned_staff": staff_map[dept_map["Transport Office"]],
            "status": "Submitted",
            "created_offset_days": 1,
            "history": [
                ("Submitted", "Submitted", "Grievance received and awaiting staff review.")
            ]
        },
        {
            "student_id": student_users[1].user_id,
            "title": "Request for IEEE Xplore digital library remote access",
            "description": "Students working on final year capstone projects need off-campus proxy access to IEEE and ACM digital libraries through student portal logins.",
            "predicted_category": "Library",
            "predicted_priority": "Low",
            "predicted_sentiment": "Positive",
            "category_confidence": 0.93,
            "assigned_dept": dept_map["Library Administration"],
            "assigned_staff": staff_map[dept_map["Library Administration"]],
            "status": "Resolved",
            "created_offset_days": 8,
            "resolved_offset_days": 4,
            "history": [
                ("Submitted", "Assigned", "Routed to Library Admin."),
                ("Assigned", "In Progress", "Configuring institutional SSO proxy credentials."),
                ("In Progress", "Resolved", "Remote VPN credentials and Athens login links issued to all registered scholars.")
            ],
            "feedback": (4, "Remote credentials work smoothly now. Great support.")
        },
        {
            "student_id": student_users[2].user_id,
            "title": "Delay in issuing Bonafide Certificate for scholarship",
            "description": "Applied for government scholarship bonafide certificate 10 days ago at Admin counter 3. The deadline is approaching in 3 days.",
            "predicted_category": "Administration",
            "predicted_priority": "High",
            "predicted_sentiment": "Negative",
            "category_confidence": 0.92,
            "assigned_dept": dept_map["Administrative Office"],
            "assigned_staff": staff_map[dept_map["Administrative Office"]],
            "status": "Assigned",
            "created_offset_days": 2,
            "history": [
                ("Submitted", "Assigned", "Dispatched to Administrative Office officer.")
            ]
        },
        {
            "student_id": student_users[0].user_id,
            "title": "Attendance record missing for Machine Learning elective lab",
            "description": "I attended all 4 lab sessions on Fridays in September, but the portal marks 2 sessions absent due to biometric scanner glitch.",
            "predicted_category": "Academic",
            "predicted_priority": "Medium",
            "predicted_sentiment": "Neutral",
            "category_confidence": 0.95,
            "assigned_dept": dept_map["Academic Office"],
            "assigned_staff": staff_map[dept_map["Academic Office"]],
            "status": "Resolved",
            "created_offset_days": 12,
            "resolved_offset_days": 6,
            "history": [
                ("Submitted", "Assigned", "Sent to Academic Office for instructor confirmation."),
                ("Assigned", "In Progress", "Instructor physical sign-in sheet cross-verified."),
                ("In Progress", "Resolved", "Attendance ledger updated to 100% for the concerned sessions.")
            ],
            "feedback": (5, "Attendance rectified accurately on the student portal.")
        }
    ]

    for item in sample_grievances:
        c_time = now - timedelta(days=item["created_offset_days"])
        r_time = (now - timedelta(days=item["resolved_offset_days"])) if "resolved_offset_days" in item else None
        
        g = Grievance(
            student_id=item["student_id"],
            title=item["title"],
            description=item["description"],
            predicted_category=item["predicted_category"],
            predicted_priority=item["predicted_priority"],
            predicted_sentiment=item["predicted_sentiment"],
            category_confidence=item["category_confidence"],
            assigned_department_id=item["assigned_dept"],
            assigned_staff_id=item["assigned_staff"],
            status=item["status"],
            created_at=c_time,
            updated_at=r_time or c_time,
            resolved_at=r_time
        )
        session.add(g)
        session.flush()

        # Add history entries
        prev_st = None
        for step_idx, (p_st, n_st, rem) in enumerate(item["history"]):
            h_time = c_time + timedelta(hours=(step_idx + 1) * 6)
            h = GrievanceStatusHistory(
                grievance_id=g.grievance_id,
                updated_by=admin_user.user_id if step_idx == 0 else (item["assigned_staff"] or admin_user.user_id),
                previous_status=p_st,
                new_status=n_st,
                remarks=rem,
                updated_at=min(h_time, now)
            )
            session.add(h)

        # Feedback if any
        if "feedback" in item:
            fb_rating, fb_comment = item["feedback"]
            fb = Feedback(
                grievance_id=g.grievance_id,
                student_id=item["student_id"],
                rating=fb_rating,
                comments=fb_comment,
                submitted_at=r_time + timedelta(hours=4) if r_time else now
            )
            session.add(fb)

    session.commit()
    session.close()
