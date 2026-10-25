import os
from datetime import datetime
from werkzeug.utils import secure_filename
from config import Config
from database.models import Grievance, GrievanceStatusHistory, DuplicateMatches, Feedback, Department, User
from ml.predict import predict_grievance
from ml.duplicate_detection import find_duplicate_grievances
from ml.routing import route_and_assign_grievance

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

class GrievanceService:
    @staticmethod
    def submit_grievance(session, student_id: int, title: str, description: str, file_obj=None) -> tuple[Grievance, list]:
        """
        Executes end-to-end atomic submission pipeline:
        1. AI Predictions (Category, Priority, Sentiment, Safety Check)
        2. Intelligent Department & Staff Routing
        3. Cosine-Similarity Duplicate Detection
        4. Attachment validation and storage
        5. Atomic database transaction
        """
        try:
            # 1. AI Predictions
            prediction = predict_grievance(title, description)

            # 2. Duplicate Detection (check against existing unresolved/active grievances)
            existing_active = session.query(Grievance).filter(
                Grievance.status.in_(['Submitted', 'Assigned', 'In Progress'])
            ).all()
            duplicates = find_duplicate_grievances(title, description, existing_active)

            # 3. Intelligent Routing
            routing_info = route_and_assign_grievance(
                session, 
                prediction['category'], 
                prediction.get('confidence', 1.0)
            )

            # 4. Handle Attachment if provided
            attachment_filename = None
            if file_obj and file_obj.filename and allowed_file(file_obj.filename):
                os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
                safe_name = secure_filename(file_obj.filename)
                timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                attachment_filename = f"{timestamp_str}_{safe_name}"
                save_path = os.path.join(Config.UPLOAD_FOLDER, attachment_filename)
                file_obj.save(save_path)

            # Determine initial status
            initial_status = "Assigned" if routing_info['staff_id'] else "Submitted"

            # 5. Create Grievance Record
            grievance = Grievance(
                student_id=student_id,
                title=title.strip(),
                description=description.strip(),
                predicted_category=prediction['category'],
                predicted_priority=prediction['priority'],
                predicted_sentiment=prediction['sentiment'],
                category_confidence=prediction['confidence'],
                assigned_department_id=routing_info['department_id'],
                assigned_staff_id=routing_info['staff_id'],
                status=initial_status,
                attachment_path=attachment_filename,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(grievance)
            session.flush()

            # 6. Add Initial History Log
            history_remarks = (
                f"Grievance formally registered. "
                f"Classification: Domain='{prediction['category']}' ({prediction['confidence']*100:.0f}% confidence), "
                f"Priority='{prediction['priority']}' ({'Escalated due to critical hazard keywords' if prediction['is_safety_escalated'] else 'Assessed urgency'}), "
                f"Tone='{prediction['sentiment']}'. "
                f"{routing_info['routing_reason']}"
            )
            history_entry = GrievanceStatusHistory(
                grievance_id=grievance.grievance_id,
                updated_by=student_id,
                previous_status=None,
                new_status=initial_status,
                remarks=history_remarks,
                updated_at=datetime.utcnow()
            )
            session.add(history_entry)

            # 7. Record Duplicate Matches if detected
            for dup in duplicates:
                dup_record = DuplicateMatches(
                    grievance_id=grievance.grievance_id,
                    similar_grievance_id=dup['similar_grievance_id'],
                    similarity_score=dup['similarity_score'],
                    review_status='Flagged'
                )
                session.add(dup_record)

            session.commit()
            return grievance, duplicates

        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def update_status(session, grievance_id: int, user_id: int, new_status: str, remarks: str) -> Grievance:
        """
        Updates status of grievance, maintains timeline history and sets resolved_at if applicable.
        """
        try:
            grievance = session.query(Grievance).filter_by(grievance_id=grievance_id).first()
            if not grievance:
                raise ValueError("Grievance not found.")

            previous_status = grievance.status
            grievance.status = new_status
            grievance.updated_at = datetime.utcnow()

            if new_status == 'Resolved':
                grievance.resolved_at = datetime.utcnow()
            elif previous_status == 'Resolved' and new_status != 'Resolved':
                grievance.resolved_at = None

            history = GrievanceStatusHistory(
                grievance_id=grievance.grievance_id,
                updated_by=user_id,
                previous_status=previous_status,
                new_status=new_status,
                remarks=remarks.strip() if remarks else f"Status changed to {new_status}.",
                updated_at=datetime.utcnow()
            )
            session.add(history)
            session.commit()
            return grievance

        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def reassign_grievance(session, grievance_id: int, admin_id: int, new_category: str, new_dept_id: int, new_staff_id: int, remarks: str) -> Grievance:
        """
        Administrator manual override for AI misclassifications or staff reassignment.
        """
        try:
            grievance = session.query(Grievance).filter_by(grievance_id=grievance_id).first()
            if not grievance:
                raise ValueError("Grievance not found.")

            old_cat = grievance.predicted_category
            old_dept = grievance.assigned_department.department_name if grievance.assigned_department else 'None'
            old_staff = grievance.assigned_staff.name if grievance.assigned_staff else 'None'

            grievance.predicted_category = new_category
            grievance.assigned_department_id = new_dept_id
            grievance.assigned_staff_id = new_staff_id
            grievance.updated_at = datetime.utcnow()
            
            # If it was unassigned, move to Assigned
            if grievance.status == 'Submitted' and new_staff_id:
                grievance.status = 'Assigned'

            dept_obj = session.query(Department).filter_by(department_id=new_dept_id).first()
            staff_obj = session.query(User).filter_by(user_id=new_staff_id).first() if new_staff_id else None

            log_notes = (
                f"Admin Manual Reassignment: Category changed from '{old_cat}' to '{new_category}'. "
                f"Dept changed from '{old_dept}' to '{dept_obj.department_name if dept_obj else 'None'}'. "
                f"Staff changed from '{old_staff}' to '{staff_obj.name if staff_obj else 'Unassigned'}'. "
                f"Reason: {remarks.strip() if remarks else 'Administrative review'}"
            )

            history = GrievanceStatusHistory(
                grievance_id=grievance.grievance_id,
                updated_by=admin_id,
                previous_status=grievance.status,
                new_status=grievance.status,
                remarks=log_notes,
                updated_at=datetime.utcnow()
            )
            session.add(history)
            session.commit()
            return grievance

        except Exception as e:
            session.rollback()
            raise e

    @staticmethod
    def add_feedback(session, grievance_id: int, student_id: int, rating: int, comments: str) -> Feedback:
        """
        Allows student to submit 1-5 rating & feedback on resolved grievances.
        """
        try:
            grievance = session.query(Grievance).filter_by(grievance_id=grievance_id, student_id=student_id).first()
            if not grievance:
                raise ValueError("Grievance not found or unauthorized.")
            if grievance.status != 'Resolved':
                raise ValueError("Feedback can only be provided for resolved grievances.")

            existing_fb = session.query(Feedback).filter_by(grievance_id=grievance_id).first()
            if existing_fb:
                existing_fb.rating = rating
                existing_fb.comments = comments.strip()
                existing_fb.submitted_at = datetime.utcnow()
                fb = existing_fb
            else:
                fb = Feedback(
                    grievance_id=grievance_id,
                    student_id=student_id,
                    rating=rating,
                    comments=comments.strip() if comments else "",
                    submitted_at=datetime.utcnow()
                )
                session.add(fb)

            session.commit()
            return fb

        except Exception as e:
            session.rollback()
            raise e
