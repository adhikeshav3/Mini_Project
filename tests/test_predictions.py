import os
import sys
import unittest

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from config import Config
from ml.preprocessing import clean_text
from ml.predict import predict_grievance, check_safety_escalation
from ml.duplicate_detection import find_duplicate_grievances
from ml.routing import route_and_assign_grievance
from database.db import db_session, init_db, seed_demo_data
from database.models import Grievance, Department, User

class TestPredictionsAndAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        seed_demo_data()

    def test_text_preprocessing(self):
        sample = "The projector in Hall 2 is NOT working!!! http://test.com"
        cleaned = clean_text(sample, remove_stopwords=True)
        self.assertNotIn("http", cleaned)
        self.assertNotIn("!", cleaned)
        self.assertIn("projector", cleaned)

    def test_category_and_priority_prediction(self):
        title = "Switchboard sparking in Lab"
        desc = "The electrical switchboard in Classroom 204 is damaged and sparks are coming from it."
        result = predict_grievance(title, desc)
        
        self.assertIn('category', result)
        self.assertIn('priority', result)
        self.assertIn('sentiment', result)
        self.assertEqual(result['category'], 'Infrastructure')
        self.assertEqual(result['priority'], 'High')
        self.assertEqual(result['sentiment'], 'Negative')

    def test_safety_escalation_mechanism(self):
        # Even if a complaint has ambiguous wording, physical danger keywords MUST escalate priority to High
        hazard_desc = "There is a short circuit in the ground floor panel."
        is_escalated, reason = check_safety_escalation(hazard_desc)
        self.assertTrue(is_escalated)
        self.assertIn("short circuit", reason)

        pred = predict_grievance("Emergency alert", hazard_desc)
        self.assertEqual(pred['priority'], 'High')
        self.assertTrue(pred['is_safety_escalated'])

    def test_duplicate_grievance_detection(self):
        session = db_session()
        existing = session.query(Grievance).all()
        
        # Test grievance very similar to seeded sample:
        # "There has been no running water in Hostel Block B 3rd floor bathrooms"
        new_title = "Water problem in Hostel Block B"
        new_desc = "No running water in Hostel Block B floor bathrooms since yesterday."
        
        duplicates = find_duplicate_grievances(new_title, new_desc, existing, threshold=0.35)
        self.assertIsInstance(duplicates, list)
        self.assertGreater(len(duplicates), 0)
        self.assertIn('similarity_score', duplicates[0])
        self.assertGreaterEqual(duplicates[0]['similarity_score'], 0.35)

    def test_intelligent_routing_and_workload(self):
        session = db_session()
        # Test routing for Hostel category
        routing = route_and_assign_grievance(session, 'Hostel')
        self.assertEqual(routing['department_name'], 'Hostel Administration')
        self.assertIsNotNone(routing['staff_id'])
        self.assertEqual(routing['routing_status'], 'Assigned')

if __name__ == '__main__':
    unittest.main()
