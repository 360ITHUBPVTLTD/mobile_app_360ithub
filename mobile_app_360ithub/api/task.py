import frappe
from .common import get_doc_with_filters
from frappe.utils import getdate, today
 
@frappe.whitelist()
def get_task_summary():
    # user = frappe.session.user

    pending_tasks = get_doc_with_filters("Task", filters=
[["status","not in",["Template", "Completed", "Cancelled"]]],  limit=9999999)
 
    task_without_due_date = [task for task in pending_tasks if not task.get('exp_end_date')]
    overdue_tasks = [
        task
        for task in pending_tasks
        if task.get("exp_end_date")
        and getdate(task.get("exp_end_date")) < getdate(today())
    ]
    todays_tasks = [task for task in pending_tasks if task.get("exp_end_date") == getdate(today())]
    upcoming_seven_days_tasks = [task for task in pending_tasks if task.get("exp_end_date") and getdate(task.get("exp_end_date")) > getdate(today()) and getdate(task.get("exp_end_date")) <= getdate(frappe.utils.add_days(today(), 7))]
 
    total_todo = [
        task
        for task in pending_tasks
        if task.get("status") == "Open"
    ]
    total_in_progress = [
        task
        for task in pending_tasks
        if task.get("status") == "Working"
    ]
    total_review = [
        task
        for task in pending_tasks
        if task.get("status") == "Pending Review"
    ]
    total_completed = get_doc_with_filters("Task", filters=[["status", "=", "Completed"]], limit=9999999)
 
    total_urgent = [task for task in pending_tasks if task.get("priority") == "Urgent"]
    total_high = [task for task in pending_tasks if task.get("priority") == "High"]
    total_medium = [task for task in pending_tasks if task.get("priority") == "Medium"]
    total_low = [task for task in pending_tasks if task.get("priority") == "Low"]
 
    return {
        "total_tasks_count": len(pending_tasks),
        "tasks_without_due_date_count": len(task_without_due_date),
        "overdue_tasks_count": len(overdue_tasks),
        "todays_tasks_count": len(todays_tasks),
        "upcoming_seven_days_tasks_count": len(upcoming_seven_days_tasks),
        "total_todo_count": len(total_todo),
        "total_in_progress_count": len(total_in_progress),
        "total_review_count": len(total_review),
        "total_completed_count": len(total_completed),
        "total_urgent_count": len(total_urgent),
        "total_high_count": len(total_high),
        "total_medium_count": len(total_medium),
        "total_low_count": len(total_low),
    }
 