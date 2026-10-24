from database.models import Grievance, DuplicateMatches

class NotificationService:
    @staticmethod
    def get_admin_notifications(session) -> list:
        """
        Retrieves real-time administrative alerts:
        - Critical/High-priority open complaints
        - Duplicate grievances flagged for review
        - Complaints awaiting staff assignment
        """
        notifications = []
        
        # 1. Unassigned complaints
        unassigned_count = session.query(Grievance).filter(
            Grievance.assigned_staff_id == None,
            Grievance.status.in_(['Submitted', 'Assigned'])
        ).count()
        if unassigned_count > 0:
            notifications.append({
                'type': 'warning',
                'title': 'Unassigned Grievances',
                'message': f"{unassigned_count} grievance(s) are awaiting staff allocation.",
                'badge': f"{unassigned_count} Pending"
            })

        # 2. Flagged duplicates
        flagged_duplicates = session.query(DuplicateMatches).filter_by(review_status='Flagged').count()
        if flagged_duplicates > 0:
            notifications.append({
                'type': 'info',
                'title': 'Potential Duplicates Detected',
                'message': f"{flagged_duplicates} grievance pair(s) flagged with high semantic similarity.",
                'badge': f"{flagged_duplicates} Review"
            })

        # 3. Urgent High-Priority open grievances
        urgent_count = session.query(Grievance).filter(
            Grievance.predicted_priority == 'High',
            Grievance.status.in_(['Submitted', 'Assigned', 'In Progress'])
        ).count()
        if urgent_count > 0:
            notifications.append({
                'type': 'danger',
                'title': 'High-Priority Complaints Active',
                'message': f"{urgent_count} critical/urgent complaint(s) require prompt resolution.",
                'badge': f"{urgent_count} Critical"
            })

        return notifications
