import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, setup_app
from database.db import db_session
from database.models import Grievance, User, Department
from services.grievance_service import GrievanceService

class TestElectricalSwitchboardScenario(unittest.TestCase):
    """
    Verifies all 12 points of the prompt's functional verification scenario:
    A student submits:
      Title: Damaged electrical switchboard
      Description: The electrical switchboard in Classroom 204 is damaged and sparks are coming from it.
    Verify:
      1. SQLite database write.
      2. Category: Infrastructure.
      3. Priority: High (via ML or safety net).
      4. Department: Maintenance Department.
      5. Staff: Er. Rajesh Kumar.
      6. Visible in student dashboard and history.
      7. Visible in staff queue.
      8. Visible in admin dashboard.
      9. Staff updates status to In Progress.
      10. Staff updates status to Resolved with remarks.
      11. Student sees status update.
      12. Admin dashboard statistics update.
    """

    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        setup_app()
        self.session = db_session()

    def tearDown(self):
        self.session.close()

    def test_all_12_points_electrical_switchboard(self):
        # 1. Submission & SQLite DB Write
        title = "Damaged electrical switchboard"
        desc = "The electrical switchboard in Classroom 204 is damaged and sparks are coming from it."

        # Fetch student account
        student = self.session.query(User).filter_by(email='student@college.edu').first()
        self.assertIsNotNone(student, "Student user must exist in database")

        # Submit via GrievanceService (simulating student action)
        grievance, _ = GrievanceService.submit_grievance(
            self.session,
            student_id=student.user_id,
            title=title,
            description=desc
        )

        # Point 1: SQLite database write verified
        self.assertIsNotNone(grievance.grievance_id, "Point 1: Grievance must have a persistent ID in SQLite")
        db_record = self.session.query(Grievance).filter_by(grievance_id=grievance.grievance_id).first()
        self.assertIsNotNone(db_record, "Point 1: Must be readable from SQLite database")

        # Point 2: Category: Infrastructure
        self.assertEqual(db_record.predicted_category, 'Infrastructure', "Point 2: Category must be Infrastructure")

        # Point 3: Priority: High (via ML or safety net)
        self.assertEqual(db_record.predicted_priority, 'High', "Point 3: Priority must be High")

        # Point 4: Department: Maintenance Department
        dept = self.session.query(Department).filter_by(department_id=db_record.assigned_department_id).first()
        self.assertIsNotNone(dept, "Point 4: Department must be assigned")
        self.assertEqual(dept.department_name, 'Maintenance Department', "Point 4: Department must be Maintenance Department")

        # Point 5: Staff: Er. Rajesh Kumar
        staff = self.session.query(User).filter_by(user_id=db_record.assigned_staff_id).first()
        self.assertIsNotNone(staff, "Point 5: Staff must be assigned")
        self.assertEqual(staff.name, 'Er. Rajesh Kumar', "Point 5: Staff must be Er. Rajesh Kumar")

        # Point 6: Visible in student dashboard and history
        # Authenticate as student
        self.client.post('/login', data={'email': 'student@college.edu', 'password': 'student123'}, follow_redirects=True)
        resp_dash = self.client.get('/student/dashboard')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn("Damaged electrical switchboard", resp_dash.get_data(as_text=True), "Point 6: Visible on student dashboard")

        resp_hist = self.client.get('/student/history')
        self.assertEqual(resp_hist.status_code, 200)
        self.assertIn("Damaged electrical switchboard", resp_hist.get_data(as_text=True), "Point 6: Visible in student history")
        self.client.get('/logout')

        # Point 7: Visible in staff queue
        self.client.post('/login', data={'email': 'maintenance@college.edu', 'password': 'staff123'}, follow_redirects=True)
        resp_staff = self.client.get('/staff/dashboard')
        self.assertEqual(resp_staff.status_code, 200)
        self.assertIn("Damaged electrical switchboard", resp_staff.get_data(as_text=True), "Point 7: Visible in staff queue")

        # Point 8: Visible in admin dashboard
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'admin@college.edu', 'password': 'admin123'}, follow_redirects=True)
        resp_admin = self.client.get('/admin/dashboard')
        self.assertEqual(resp_admin.status_code, 200)
        self.assertIn("Damaged electrical switchboard", resp_admin.get_data(as_text=True), "Point 8: Visible on admin dashboard")
        self.client.get('/logout')

        # Point 9: Staff updates status to In Progress
        self.client.post('/login', data={'email': 'maintenance@college.edu', 'password': 'staff123'}, follow_redirects=True)
        resp_up1 = self.client.post(
            f'/grievance/{grievance.grievance_id}/status',
            data={'status': 'In Progress', 'remarks': 'Electrician technician dispatched to Classroom 204 with replacement switch unit.'},
            follow_redirects=True
        )
        self.assertEqual(resp_up1.status_code, 200)
        self.session.expire_all()
        g_prog = self.session.query(Grievance).filter_by(grievance_id=grievance.grievance_id).first()
        self.assertEqual(g_prog.status, 'In Progress', "Point 9: Status must be In Progress")

        # Point 10: Staff updates status to Resolved with remarks
        resp_up2 = self.client.post(
            f'/grievance/{grievance.grievance_id}/status',
            data={'status': 'Resolved', 'remarks': 'Switchboard fully replaced and tested. Classroom power is safe and active.'},
            follow_redirects=True
        )
        self.assertEqual(resp_up2.status_code, 200)
        self.session.expire_all()
        g_res = self.session.query(Grievance).filter_by(grievance_id=grievance.grievance_id).first()
        self.assertEqual(g_res.status, 'Resolved', "Point 10: Status must be Resolved")
        self.assertIsNotNone(g_res.resolved_at, "Point 10: Resolution timestamp must be set")
        self.client.get('/logout')

        # Point 11: Student sees status update
        self.client.post('/login', data={'email': 'student@college.edu', 'password': 'student123'}, follow_redirects=True)
        resp_detail = self.client.get(f'/grievance/{grievance.grievance_id}')
        self.assertEqual(resp_detail.status_code, 200)
        detail_html = resp_detail.get_data(as_text=True)
        self.assertIn("Resolved", detail_html, "Point 11: Student sees Resolved status")
        self.assertIn("Classroom power is safe and active", detail_html, "Point 11: Student sees resolution remarks")
        self.client.get('/logout')

        # Point 12: Admin dashboard statistics update
        self.client.post('/login', data={'email': 'admin@college.edu', 'password': 'admin123'}, follow_redirects=True)
        resp_admin_stats = self.client.get('/api/analytics')
        self.assertEqual(resp_admin_stats.status_code, 200)
        stats_json = resp_admin_stats.get_json()
        self.assertIn('categories', stats_json, "Point 12: Analytics contains categories")
        self.assertIn('Infrastructure', stats_json['categories']['labels'], "Point 12: Infrastructure in categories")
        self.assertIn('Resolved', stats_json['statuses']['labels'], "Point 12: Resolved status in analytics")
        self.client.get('/logout')

if __name__ == '__main__':
    unittest.main()
