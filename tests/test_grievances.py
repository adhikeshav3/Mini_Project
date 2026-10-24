import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, setup_app
from database.db import db_session
from database.models import Grievance, User, Department, Feedback
from services.grievance_service import GrievanceService

class TestGrievanceWorkflow(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        setup_app()

    def test_scenario_complete_lifecycle(self):
        """
        Tests Scenarios 1 to 5 end-to-end:
        1. Student submits complaint
        2. AI predicts Category, Priority, Sentiment
        3. Correct department routing and staff assignment
        4. Staff updates status (In Progress -> Resolved)
        5. Admin analytics reflect current database records
        """
        session = db_session()
        student = session.query(User).filter_by(role='student').first()

        # Step 1 & 2: Submit grievance with electrical issue
        title = "Damaged switchboard in Room 204"
        desc = "The electrical switchboard in Classroom 204 is damaged and sparks are coming from it."

        grievance, duplicates = GrievanceService.submit_grievance(
            session,
            student_id=student.user_id,
            title=title,
            description=desc
        )

        self.assertIsNotNone(grievance.grievance_id)
        # Verify AI Predictions
        self.assertEqual(grievance.predicted_category, 'Infrastructure')
        self.assertEqual(grievance.predicted_priority, 'High')
        self.assertEqual(grievance.predicted_sentiment, 'Negative')

        # Step 3: Verify assigned to Maintenance Department
        dept = session.query(Department).filter_by(department_id=grievance.assigned_department_id).first()
        self.assertEqual(dept.department_name, 'Maintenance Department')
        self.assertIsNotNone(grievance.assigned_staff_id)

        # Step 4: Staff updates status to In Progress, then Resolved
        staff_id = grievance.assigned_staff_id
        GrievanceService.update_status(
            session,
            grievance_id=grievance.grievance_id,
            user_id=staff_id,
            new_status='In Progress',
            remarks="Inspection team deployed to Room 204."
        )

        updated_g = session.query(Grievance).filter_by(grievance_id=grievance.grievance_id).first()
        self.assertEqual(updated_g.status, 'In Progress')

        # Staff resolves
        GrievanceService.update_status(
            session,
            grievance_id=grievance.grievance_id,
            user_id=staff_id,
            new_status='Resolved',
            remarks="Switchboard replaced with industrial grade enclosure and new circuit breaker."
        )
        resolved_g = session.query(Grievance).filter_by(grievance_id=grievance.grievance_id).first()
        self.assertEqual(resolved_g.status, 'Resolved')
        self.assertIsNotNone(resolved_g.resolved_at)

        # Step 5: Student provides satisfaction feedback
        fb = GrievanceService.add_feedback(
            session,
            grievance_id=grievance.grievance_id,
            student_id=student.user_id,
            rating=5,
            comments="Prompt and safe replacement within 2 hours. Excellent work!"
        )
        self.assertIsNotNone(fb.feedback_id)
        self.assertEqual(fb.rating, 5)

        # Step 6: Verify Admin API returns matching statistics from database
        # Log in as admin
        self.client.post('/login', data={'email': 'admin@college.edu', 'password': 'admin123'})
        resp = self.client.get('/api/analytics')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('categories', data)
        self.assertIn('Infrastructure', data['categories']['labels'])
        self.assertIn('priorities', data)
        self.assertIn('High', data['priorities']['labels'])

if __name__ == '__main__':
    unittest.main()
