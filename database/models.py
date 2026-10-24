from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

class User(Base, UserMixin):
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # 'student', 'staff', 'admin'
    department_id = Column(Integer, ForeignKey('departments.department_id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    department = relationship('Department', back_populates='staff_members')
    submitted_grievances = relationship('Grievance', foreign_keys='Grievance.student_id', back_populates='student')
    assigned_grievances = relationship('Grievance', foreign_keys='Grievance.assigned_staff_id', back_populates='assigned_staff')
    history_updates = relationship('GrievanceStatusHistory', back_populates='updater')
    feedbacks = relationship('Feedback', back_populates='student')

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'department_id': self.department_id,
            'department_name': self.department.department_name if self.department else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None
        }


class Department(Base):
    __tablename__ = 'departments'
    
    department_id = Column(Integer, primary_key=True, autoincrement=True)
    department_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Relationships
    staff_members = relationship('User', back_populates='department')
    grievances = relationship('Grievance', back_populates='assigned_department')

    def to_dict(self):
        return {
            'department_id': self.department_id,
            'department_name': self.department_name,
            'description': self.description,
            'staff_count': len(self.staff_members)
        }


class Grievance(Base):
    __tablename__ = 'grievances'
    
    grievance_id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # AI Predictions
    predicted_category = Column(String(50), nullable=True)
    predicted_priority = Column(String(20), nullable=True)
    predicted_sentiment = Column(String(20), nullable=True)
    category_confidence = Column(Float, nullable=True)
    
    # Assignments & Status
    assigned_department_id = Column(Integer, ForeignKey('departments.department_id'), nullable=True, index=True)
    assigned_staff_id = Column(Integer, ForeignKey('users.user_id'), nullable=True, index=True)
    status = Column(String(30), default='Submitted', nullable=False, index=True)  # Submitted, Assigned, In Progress, Resolved
    attachment_path = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship('User', foreign_keys=[student_id], back_populates='submitted_grievances')
    assigned_department = relationship('Department', back_populates='grievances')
    assigned_staff = relationship('User', foreign_keys=[assigned_staff_id], back_populates='assigned_grievances')
    status_history = relationship('GrievanceStatusHistory', back_populates='grievance', order_by='GrievanceStatusHistory.updated_at.asc()', cascade='all, delete-orphan')
    duplicate_matches = relationship('DuplicateMatches', foreign_keys='DuplicateMatches.grievance_id', back_populates='grievance', cascade='all, delete-orphan')
    matched_as_duplicate = relationship('DuplicateMatches', foreign_keys='DuplicateMatches.similar_grievance_id', back_populates='similar_grievance')
    feedback = relationship('Feedback', back_populates='grievance', uselist=False, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'grievance_id': self.grievance_id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else 'Unknown',
            'title': self.title,
            'description': self.description,
            'predicted_category': self.predicted_category,
            'predicted_priority': self.predicted_priority,
            'predicted_sentiment': self.predicted_sentiment,
            'category_confidence': round(self.category_confidence, 2) if self.category_confidence else None,
            'assigned_department_id': self.assigned_department_id,
            'department_name': self.assigned_department.department_name if self.assigned_department else 'Unassigned',
            'assigned_staff_id': self.assigned_staff_id,
            'staff_name': self.assigned_staff.name if self.assigned_staff else 'Unassigned',
            'status': self.status,
            'attachment_path': self.attachment_path,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M') if self.created_at else None,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M') if self.updated_at else None,
            'resolved_at': self.resolved_at.strftime('%Y-%m-%d %H:%M') if self.resolved_at else None
        }


class GrievanceStatusHistory(Base):
    __tablename__ = 'grievance_status_history'
    
    history_id = Column(Integer, primary_key=True, autoincrement=True)
    grievance_id = Column(Integer, ForeignKey('grievances.grievance_id'), nullable=False, index=True)
    updated_by = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    previous_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=False)
    remarks = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    grievance = relationship('Grievance', back_populates='status_history')
    updater = relationship('User', back_populates='history_updates')


class DuplicateMatches(Base):
    __tablename__ = 'duplicate_matches'
    
    match_id = Column(Integer, primary_key=True, autoincrement=True)
    grievance_id = Column(Integer, ForeignKey('grievances.grievance_id'), nullable=False, index=True)
    similar_grievance_id = Column(Integer, ForeignKey('grievances.grievance_id'), nullable=False)
    similarity_score = Column(Float, nullable=False)
    review_status = Column(String(30), default='Flagged')  # Flagged, Confirmed, Dismissed
    
    # Relationships
    grievance = relationship('Grievance', foreign_keys=[grievance_id], back_populates='duplicate_matches')
    similar_grievance = relationship('Grievance', foreign_keys=[similar_grievance_id], back_populates='matched_as_duplicate')


class Feedback(Base):
    __tablename__ = 'feedback'
    
    feedback_id = Column(Integer, primary_key=True, autoincrement=True)
    grievance_id = Column(Integer, ForeignKey('grievances.grievance_id'), unique=True, nullable=False)
    student_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    grievance = relationship('Grievance', back_populates='feedback')
    student = relationship('User', back_populates='feedbacks')
