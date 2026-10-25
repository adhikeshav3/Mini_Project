import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app, setup_app
from database.db import db_session
from database.models import User

class TestAuthenticationAndRBAC(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        setup_app()

    def test_student_login_and_redirect(self):
        response = self.client.post('/login', data={
            'email': 'student@college.edu',
            'password': 'student123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Dashboard", response.data)

    def test_staff_login_and_redirect(self):
        response = self.client.post('/login', data={
            'email': 'maintenance@college.edu',
            'password': 'staff123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Staff Dashboard", response.data)

    def test_admin_login_and_redirect(self):
        response = self.client.post('/login', data={
            'email': 'admin@college.edu',
            'password': 'admin123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Admin Dashboard", response.data)

    def test_invalid_credentials_rejected(self):
        response = self.client.post('/login', data={
            'email': 'student@college.edu',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email address or password", response.data)

    def test_student_cannot_access_admin_dashboard(self):
        """Scenario 6: Student attempts to access admin dashboard -> Access denied."""
        # Log in as student
        self.client.post('/login', data={
            'email': 'student@college.edu',
            'password': 'student123'
        }, follow_redirects=True)

        # Attempt to access /admin/dashboard
        response = self.client.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should be redirected to student dashboard with access denied flash
        self.assertIn(b"Access denied", response.data)
        self.assertIn(b"Student Dashboard", response.data)

    def test_unauthenticated_redirected_to_login(self):
        response = self.client.get('/student/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Portal Login", response.data)

if __name__ == '__main__':
    unittest.main()
