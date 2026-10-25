import os
import sys
from datetime import datetime
from functools import wraps

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import secrets
from markupsafe import Markup
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, abort, session
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from sqlalchemy import func, or_

from config import Config
from database.db import engine, db_session, init_db, seed_demo_data
from database.models import User, Department, Grievance, GrievanceStatusHistory, DuplicateMatches, Feedback
from services.grievance_service import GrievanceService
from services.notification_service import NotificationService
from ml.predict import predict_grievance, ModelManager

app = Flask(__name__)
app.config.from_object(Config)

# Ensure necessary directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.MODELS_DIR, exist_ok=True)
os.makedirs(Config.DB_DIR, exist_ok=True)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Please log in to access this portal."
login_manager.login_message_category = "info"

@login_manager.user_loader
def load_user(user_id):
    return db_session.get(User, int(user_id))

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# CSRF Protection Implementation
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@app.context_processor
def inject_csrf():
    token = generate_csrf_token()
    return {
        'csrf_token_value': token,
        'csrf_token': lambda: Markup(f'<input type="hidden" name="csrf_token" value="{token}">')
    }

@app.before_request
def csrf_protect():
    if app.config.get('TESTING') or not app.config.get('WTF_CSRF_ENABLED', True):
        return
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        # Allow internal preview endpoint
        if request.path.startswith('/api/predict-preview') or (request.is_json and current_user.is_authenticated):
            return
        token = request.form.get('csrf_token') or request.headers.get('X-CSRFToken')
        expected = session.get('_csrf_token')
        if not expected or not token or not secrets.compare_digest(token, expected):
            abort(400, description="Security Notice: Invalid or expired CSRF submission token. Please reload the page and try again.")

# Role-Based Access Control Decorator
def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login', next=request.url))
            if current_user.role not in allowed_roles:
                flash("Access denied: You do not possess the required privileges to view that page.", "danger")
                if current_user.role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif current_user.role == 'staff':
                    return redirect(url_for('staff_dashboard'))
                elif current_user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -------------------------------------------------------------------
# PUBLIC ROUTES
# -------------------------------------------------------------------

@app.route('/home.html')
@app.route('/index.html')
@app.route('/index', strict_slashes=False)
@app.route('/home', strict_slashes=False)
@app.route('/', strict_slashes=False)
def home():
    # Retrieve live portal stats for institutional credibility
    total_count = db_session.query(Grievance).count()
    resolved_count = db_session.query(Grievance).filter_by(status='Resolved').count()
    dept_count = db_session.query(Department).count()
    departments = db_session.query(Department).all()

    return render_template(
        'home.html',
        total_count=total_count,
        resolved_count=resolved_count,
        dept_count=dept_count,
        departments=departments
    )

@app.route('/login.html', methods=['GET', 'POST'])
@app.route('/login/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = db_session.query(User).filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name} ({user.role.capitalize()}).", "success")
            
            # Automatic role-based redirection
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'staff':
                return redirect(url_for('staff_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid email address or password. Please verify credentials.", "danger")

    return render_template('login.html')

@app.route('/register.html', methods=['GET', 'POST'])
@app.route('/register/', methods=['GET', 'POST'])
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not name or not email or not password:
            flash("Please fill in all mandatory fields.", "warning")
            return render_template('register.html')

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html')

        existing = db_session.query(User).filter_by(email=email).first()
        if existing:
            flash("An account with this institutional email already exists.", "warning")
            return render_template('register.html')

        new_user = User(name=name, email=email, role='student')
        new_user.set_password(password)
        db_session.add(new_user)
        db_session.commit()

        login_user(new_user)
        flash("Registration successful! Welcome to the Student Grievance Portal.", "success")
        return redirect(url_for('student_dashboard'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been signed out safely.", "info")
    return redirect(url_for('login'))

# -------------------------------------------------------------------
# STUDENT PORTAL ROUTES
# -------------------------------------------------------------------

@app.route('/student/dashboard', methods=['GET', 'POST'])
@role_required('student')
def student_dashboard():
    student_id = current_user.user_id
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip()

    # Query for filtered display
    query = db_session.query(Grievance).filter_by(student_id=student_id)
    if status_filter:
        query = query.filter(Grievance.status == status_filter)
    if search_query:
        query = query.filter(
            or_(
                Grievance.title.ilike(f'%{search_query}%'),
                Grievance.description.ilike(f'%{search_query}%'),
                Grievance.predicted_category.ilike(f'%{search_query}%')
            )
        )

    # Compute overall statistics for the student across all records
    all_grievances = db_session.query(Grievance).filter_by(student_id=student_id).all()
    total_submitted = len(all_grievances)
    pending_count = sum(1 for g in all_grievances if g.status in ['Submitted', 'Assigned'])
    in_progress_count = sum(1 for g in all_grievances if g.status == 'In Progress')
    resolved_count = sum(1 for g in all_grievances if g.status == 'Resolved')

    recent_grievances = query.order_by(Grievance.created_at.desc()).limit(15).all()

    return render_template(
        'student_dashboard.html',
        total_submitted=total_submitted,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        recent_grievances=recent_grievances,
        active_filter=status_filter,
        search_query=search_query
    )

@app.route('/student/submit', methods=['GET', 'POST'])
@role_required('student')
def submit_grievance():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        file_obj = request.files.get('attachment')

        if not title or not description:
            flash("Please provide a title and description for your grievance.", "warning")
            return redirect(url_for('student_dashboard'))

        try:
            grievance, duplicates = GrievanceService.submit_grievance(
                db_session,
                student_id=current_user.user_id,
                title=title,
                description=description,
                file_obj=file_obj
            )

            dept_name = grievance.assigned_department.department_name if grievance.assigned_department else 'Support Cell'
            flash(f"Grievance #{grievance.grievance_id} submitted successfully! Automatically routed to {dept_name}.", "success")
            return redirect(url_for('student_dashboard'))

        except Exception as e:
            flash(f"Error submitting grievance: {str(e)}", "danger")
            return redirect(url_for('student_dashboard'))

    return render_template('submit_grievance.html')

@app.route('/student/history')
@role_required('student')
def student_history():
    status_filter = request.args.get('status', '').strip()
    search_query = request.args.get('q', '').strip()
    query = db_session.query(Grievance).filter_by(student_id=current_user.user_id)

    if status_filter:
        query = query.filter(Grievance.status == status_filter)
    if search_query:
        query = query.filter(
            or_(
                Grievance.title.ilike(f'%{search_query}%'),
                Grievance.description.ilike(f'%{search_query}%'),
                Grievance.predicted_category.ilike(f'%{search_query}%')
            )
        )

    grievances = query.order_by(Grievance.created_at.desc()).all()
    return render_template(
        'student_history.html',
        grievances=grievances,
        active_filter=status_filter,
        search_query=search_query
    )

@app.route('/student/feedback/<int:grievance_id>', methods=['POST'])
@role_required('student')
def submit_feedback(grievance_id):
    rating = request.form.get('rating', type=int)
    comments = request.form.get('comments', '')

    if not rating or rating < 1 or rating > 5:
        flash("Please provide a valid rating from 1 to 5.", "warning")
        return redirect(url_for('grievance_details', grievance_id=grievance_id))

    try:
        GrievanceService.add_feedback(
            db_session,
            grievance_id=grievance_id,
            student_id=current_user.user_id,
            rating=rating,
            comments=comments
        )
        flash("Thank you! Your feedback on this grievance resolution has been recorded.", "success")
    except Exception as e:
        flash(f"Error saving feedback: {str(e)}", "danger")

    return redirect(url_for('grievance_details', grievance_id=grievance_id))

# -------------------------------------------------------------------
# STAFF PORTAL ROUTES
# -------------------------------------------------------------------

@app.route('/staff/dashboard')
@role_required('staff')
def staff_dashboard():
    dept_id = current_user.department_id
    if not dept_id:
        flash("Your staff account is not assigned to a department. Please contact Administrator.", "warning")
        return render_template(
            'staff_dashboard.html',
            grievances=[],
            total_count=0,
            pending_count=0,
            in_progress_count=0,
            resolved_count=0,
            high_priority_count=0,
            urgent_grievances=[],
            active_filter='',
            active_priority='',
            search_query='',
            department=None
        )

    status_filter = request.args.get('status', '').strip()
    priority_filter = request.args.get('priority', '').strip()
    search_query = request.args.get('q', '').strip()

    # Department grievances
    base_filter = or_(
        Grievance.assigned_department_id == dept_id,
        Grievance.assigned_staff_id == current_user.user_id
    )
    query = db_session.query(Grievance).filter(base_filter)

    if status_filter:
        query = query.filter(Grievance.status == status_filter)
    if priority_filter:
        query = query.filter(Grievance.predicted_priority == priority_filter)
    if search_query:
        query = query.join(User, Grievance.student_id == User.user_id, isouter=True).filter(
            or_(
                Grievance.title.ilike(f'%{search_query}%'),
                Grievance.description.ilike(f'%{search_query}%'),
                User.name.ilike(f'%{search_query}%'),
                User.email.ilike(f'%{search_query}%')
            )
        )

    dept_grievances = query.order_by(Grievance.created_at.desc()).all()

    # Compute metrics for staff department across all its cases
    all_dept_grievances = db_session.query(Grievance).filter(base_filter).all()

    total_count = len(all_dept_grievances)
    pending_count = sum(1 for g in all_dept_grievances if g.status in ['Submitted', 'Assigned'])
    in_progress_count = sum(1 for g in all_dept_grievances if g.status == 'In Progress')
    resolved_count = sum(1 for g in all_dept_grievances if g.status == 'Resolved')
    high_priority_count = sum(1 for g in all_dept_grievances if g.predicted_priority == 'High' and g.status != 'Resolved')

    urgent_grievances = [g for g in all_dept_grievances if g.predicted_priority == 'High' and g.status != 'Resolved']

    return render_template(
        'staff_dashboard.html',
        grievances=dept_grievances,
        total_count=total_count,
        pending_count=pending_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        high_priority_count=high_priority_count,
        urgent_grievances=urgent_grievances,
        active_filter=status_filter,
        active_priority=priority_filter,
        search_query=search_query,
        department=current_user.department
    )

@app.route('/staff/update-status/<int:grievance_id>', methods=['POST'])
@app.route('/grievance/<int:grievance_id>/status', methods=['POST'])
@role_required('staff', 'admin')
def update_grievance_status(grievance_id):
    new_status = request.form.get('status', '').strip()
    remarks = request.form.get('remarks', '').strip()

    if not new_status:
        flash("Please select a valid target status.", "warning")
        return redirect(url_for('grievance_details', grievance_id=grievance_id))

    try:
        GrievanceService.update_status(
            db_session,
            grievance_id=grievance_id,
            user_id=current_user.user_id,
            new_status=new_status,
            remarks=remarks
        )
        flash(f"Grievance #{grievance_id} status updated to '{new_status}'.", "success")
    except Exception as e:
        flash(f"Error updating status: {str(e)}", "danger")

    return redirect(url_for('grievance_details', grievance_id=grievance_id))

# -------------------------------------------------------------------
# ADMINISTRATOR PORTAL ROUTES
# -------------------------------------------------------------------

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    # Filters
    dept_filter = request.args.get('department', type=int)
    priority_filter = request.args.get('priority')
    status_filter = request.args.get('status')
    search_query = request.args.get('q', '').strip()

    query = db_session.query(Grievance)

    if dept_filter:
        query = query.filter(Grievance.assigned_department_id == dept_filter)
    if priority_filter:
        query = query.filter(Grievance.predicted_priority == priority_filter)
    if status_filter:
        query = query.filter(Grievance.status == status_filter)
    if search_query:
        query = query.filter(
            or_(
                Grievance.title.ilike(f'%{search_query}%'),
                Grievance.description.ilike(f'%{search_query}%'),
                Grievance.predicted_category.ilike(f'%{search_query}%')
            )
        )

    all_grievances = query.order_by(Grievance.created_at.desc()).all()

    # Overall system statistics (from real database records)
    total_grievances = db_session.query(Grievance).count()
    pending_grievances = db_session.query(Grievance).filter(Grievance.status.in_(['Submitted', 'Assigned'])).count()
    in_progress_grievances = db_session.query(Grievance).filter_by(status='In Progress').count()
    resolved_grievances = db_session.query(Grievance).filter_by(status='Resolved').count()
    high_priority_grievances = db_session.query(Grievance).filter_by(predicted_priority='High').count()

    # Calculate average resolution time for resolved grievances
    resolved_list = db_session.query(Grievance).filter(
        Grievance.status == 'Resolved',
        Grievance.resolved_at != None
    ).all()

    if resolved_list:
        total_hours = sum((g.resolved_at - g.created_at).total_seconds() / 3600.0 for g in resolved_list if g.resolved_at and g.created_at)
        avg_res_hours = round(total_hours / len(resolved_list), 1)
    else:
        avg_res_hours = 0.0

    # Departments and Staff for Management Tab
    departments = db_session.query(Department).all()
    staff_members = db_session.query(User).filter_by(role='staff').all()

    # Staff Workload Breakdown
    staff_workload = []
    for staff in staff_members:
        active_count = db_session.query(Grievance).filter(
            Grievance.assigned_staff_id == staff.user_id,
            Grievance.status.in_(['Assigned', 'In Progress'])
        ).count()
        resolved_count = db_session.query(Grievance).filter(
            Grievance.assigned_staff_id == staff.user_id,
            Grievance.status == 'Resolved'
        ).count()
        staff_workload.append({
            'staff': staff,
            'active_count': active_count,
            'resolved_count': resolved_count
        })

    # Flagged Duplicates
    flagged_duplicates = db_session.query(DuplicateMatches).filter_by(review_status='Flagged').all()

    # Unassigned Grievance Alert (Grievances awaiting staff assignment)
    unassigned_grievances = db_session.query(Grievance).filter(
        Grievance.assigned_staff_id == None,
        Grievance.status.in_(['Submitted', 'Assigned', 'In Progress'])
    ).order_by(Grievance.created_at.desc()).all()

    # Admin Notifications
    notifications = NotificationService.get_admin_notifications(db_session)

    # ML Model Metrics
    metrics_path = os.path.join(Config.MODELS_DIR, 'model_metrics.json')
    model_metrics = None
    if os.path.exists(metrics_path):
        import json
        with open(metrics_path, 'r') as f:
            model_metrics = json.load(f)

    return render_template(
        'admin_dashboard.html',
        grievances=all_grievances,
        total_grievances=total_grievances,
        pending_grievances=pending_grievances,
        in_progress_grievances=in_progress_grievances,
        resolved_grievances=resolved_grievances,
        high_priority_grievances=high_priority_grievances,
        avg_res_hours=avg_res_hours,
        departments=departments,
        staff_workload=staff_workload,
        flagged_duplicates=flagged_duplicates,
        unassigned_grievances=unassigned_grievances,
        notifications=notifications,
        model_metrics=model_metrics,
        selected_dept=dept_filter,
        selected_priority=priority_filter,
        selected_status=status_filter,
        search_query=search_query
    )

@app.route('/admin/reassign/<int:grievance_id>', methods=['GET', 'POST'])
@role_required('admin')
def admin_reassign(grievance_id):
    grievance = db_session.query(Grievance).filter_by(grievance_id=grievance_id).first_or_404()
    departments = db_session.query(Department).all()
    staff_members = db_session.query(User).filter_by(role='staff').all()

    if request.method == 'POST':
        new_category = request.form.get('category', '').strip()
        new_dept_id = request.form.get('department_id', type=int)
        new_staff_id = request.form.get('staff_id', type=int)
        remarks = request.form.get('remarks', '').strip()

        try:
            GrievanceService.reassign_grievance(
                db_session,
                grievance_id=grievance_id,
                admin_id=current_user.user_id,
                new_category=new_category,
                new_dept_id=new_dept_id,
                new_staff_id=new_staff_id,
                remarks=remarks
            )
            flash(f"Grievance #{grievance_id} reassigned successfully.", "success")
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            flash(f"Error reassigning grievance: {str(e)}", "danger")

    return render_template(
        'admin_reassign.html',
        grievance=grievance,
        departments=departments,
        staff_members=staff_members
    )

@app.route('/admin/duplicate-review/<int:match_id>', methods=['POST'])
@role_required('admin')
def review_duplicate(match_id):
    action = request.form.get('action')  # 'confirm' or 'dismiss'
    match = db_session.query(DuplicateMatches).filter_by(match_id=match_id).first_or_404()

    if action == 'confirm':
        match.review_status = 'Confirmed'
        flash(f"Confirmed match #{match_id} as related duplicate.", "info")
    elif action == 'dismiss':
        match.review_status = 'Dismissed'
        flash(f"Dismissed duplicate match #{match_id}.", "secondary")

    db_session.commit()
    return redirect(url_for('admin_dashboard'))

# -------------------------------------------------------------------
# GRIEVANCE DETAILS & TIMELINE
# -------------------------------------------------------------------

@app.route('/grievances/<int:grievance_id>')
@app.route('/grievance/<int:grievance_id>')
@login_required
def grievance_details(grievance_id):
    grievance = db_session.query(Grievance).filter_by(grievance_id=grievance_id).first()
    if not grievance:
        abort(404)

    # Authorization check:
    # Allowed if user is the student who filed it, staff assigned to it or in that dept, or admin
    if current_user.role == 'student' and grievance.student_id != current_user.user_id:
        abort(403)
    if current_user.role == 'staff' and grievance.assigned_department_id != current_user.department_id and grievance.assigned_staff_id != current_user.user_id:
        abort(403)

    return render_template('grievance_details.html', grievance=grievance)

# -------------------------------------------------------------------
# REAL-TIME ANALYTICS API (FOR CHART.JS)
# -------------------------------------------------------------------

@app.route('/api/analytics')
@role_required('admin')
def api_analytics():
    """Returns actual dynamic analytics calculated directly from SQLite database."""
    
    # 1. Grievances by Category
    cat_counts = db_session.query(
        Grievance.predicted_category, func.count(Grievance.grievance_id)
    ).group_by(Grievance.predicted_category).all()
    
    cat_labels = [c[0] if c[0] else 'Uncategorized' for c in cat_counts]
    cat_data = [c[1] for c in cat_counts]

    # 2. Grievances by Department
    dept_counts = db_session.query(
        Department.department_name, func.count(Grievance.grievance_id)
    ).join(Grievance, Grievance.assigned_department_id == Department.department_id, isouter=True)\
     .group_by(Department.department_name).all()

    dept_labels = [d[0] for d in dept_counts]
    dept_data = [d[1] for d in dept_counts]

    # 3. Priority Distribution
    prio_counts = db_session.query(
        Grievance.predicted_priority, func.count(Grievance.grievance_id)
    ).group_by(Grievance.predicted_priority).all()

    prio_labels = [p[0] if p[0] else 'Unassigned' for p in prio_counts]
    prio_data = [p[1] for p in prio_counts]

    # 4. Status Distribution (Resolution Performance)
    status_counts = db_session.query(
        Grievance.status, func.count(Grievance.grievance_id)
    ).group_by(Grievance.status).all()

    status_labels = [s[0] for s in status_counts]
    status_data = [s[1] for s in status_counts]

    # 5. Monthly Trends (by month)
    # SQLite strftime for month
    monthly_counts = db_session.query(
        func.strftime('%Y-%m', Grievance.created_at), func.count(Grievance.grievance_id)
    ).group_by(func.strftime('%Y-%m', Grievance.created_at))\
     .order_by(func.strftime('%Y-%m', Grievance.created_at).asc()).all()

    monthly_labels = [m[0] for m in monthly_counts]
    monthly_data = [m[1] for m in monthly_counts]

    # 6. Sentiment Distribution
    sent_counts = db_session.query(
        Grievance.predicted_sentiment, func.count(Grievance.grievance_id)
    ).group_by(Grievance.predicted_sentiment).all()

    sent_labels = [s[0] if s[0] else 'Neutral' for s in sent_counts]
    sent_data = [s[1] for s in sent_counts]

    return jsonify({
        'categories': {'labels': cat_labels, 'data': cat_data},
        'departments': {'labels': dept_labels, 'data': dept_data},
        'priorities': {'labels': prio_labels, 'data': prio_data},
        'statuses': {'labels': status_labels, 'data': status_data},
        'monthly': {'labels': monthly_labels, 'data': monthly_data},
        'sentiments': {'labels': sent_labels, 'data': sent_data}
    })

@app.route('/api/predict-preview', methods=['POST'])
@login_required
def api_predict_preview():
    """Provides interactive live prediction preview as student drafts grievance."""
    data = request.get_json() or {}
    title = data.get('title', '')
    desc = data.get('description', '')

    if not title and not desc:
        return jsonify({'error': 'No text provided'}), 400

    try:
        prediction = predict_grievance(title, desc)
        return jsonify(prediction)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# -------------------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------------------

@app.errorhandler(400)
def bad_request_error(error):
    desc = getattr(error, 'description', "400 Bad Request: The request could not be processed due to invalid parameters.")
    return render_template('base.html', custom_error=str(desc)), 400

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('base.html', custom_error="403 Forbidden: You do not have permission to access this resource."), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', custom_error="404 Not Found: The requested institutional record was not found."), 404

@app.errorhandler(500)
def internal_error(error):
    db_session.rollback()
    return render_template('base.html', custom_error="500 Internal Error: A server error occurred. Please contact administrative IT support."), 500

# -------------------------------------------------------------------
# APPLICATION ENTRYPOINT & INITIALIZATION
# -------------------------------------------------------------------

def setup_app():
    init_db()
    seed_demo_data()

if __name__ == '__main__':
    setup_app()
    print("\n" + "="*60)
    print("  STUDENT GRIEVANCE RESOLUTION PORTAL IS RUNNING")
    print("  Local URL: http://127.0.0.1:5000")
    print(f"  Debug Mode: {Config.DEBUG}")
    print("="*60 + "\n")
    app.run(debug=Config.DEBUG, port=5000)
