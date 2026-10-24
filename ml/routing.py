from config import Config
from database.models import Department, User, Grievance

def route_and_assign_grievance(session, predicted_category: str, confidence: float = 1.0) -> dict:
    """
    Intelligently routes a grievance based on:
    1. Predicted ML category mapped to responsible department
    2. Verification of department existence
    3. Staff availability in that department
    4. Workload balancing: assigns staff member with least active (Assigned / In Progress) grievances
    5. Fallback: If confidence is low (< 0.25) or category is unassigned/Other, routes to Administrative Office or flags for Admin review.
    """
    target_dept_name = Config.CATEGORY_DEPARTMENT_MAPPING.get(predicted_category, 'Administrative Office')
    
    # Check if department exists in DB
    dept = session.query(Department).filter_by(department_name=target_dept_name).first()
    if not dept:
        # Fallback to any administrative department
        dept = session.query(Department).first()

    if not dept:
        return {
            'department_id': None,
            'department_name': 'Awaiting Manual Routing',
            'staff_id': None,
            'staff_name': 'Unassigned',
            'routing_status': 'Needs Admin Assignment',
            'routing_reason': 'No active department found in database.'
        }

    # Fetch available staff members for this department
    staff_members = session.query(User).filter_by(role='staff', department_id=dept.department_id).all()

    if not staff_members:
        return {
            'department_id': dept.department_id,
            'department_name': dept.department_name,
            'staff_id': None,
            'staff_name': 'Awaiting Staff Allocation',
            'routing_status': 'Needs Staff Assignment',
            'routing_reason': f"No staff members currently configured for {dept.department_name}."
        }

    # Workload Balancing: Count open grievances (Assigned or In Progress) for each staff member
    best_staff = None
    min_workload = float('inf')

    for staff in staff_members:
        workload = session.query(Grievance).filter(
            Grievance.assigned_staff_id == staff.user_id,
            Grievance.status.in_(['Assigned', 'In Progress'])
        ).count()

        if workload < min_workload:
            min_workload = workload
            best_staff = staff

    return {
        'department_id': dept.department_id,
        'department_name': dept.department_name,
        'staff_id': best_staff.user_id if best_staff else None,
        'staff_name': best_staff.name if best_staff else 'Unassigned',
        'active_workload': min_workload if best_staff else 0,
        'routing_status': 'Assigned',
        'routing_reason': f"Automatically routed to {dept.department_name} based on '{predicted_category}' category; assigned to {best_staff.name} (active workload: {min_workload})."
    }
