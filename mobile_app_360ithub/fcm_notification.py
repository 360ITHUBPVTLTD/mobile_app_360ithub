import frappe
from frappe import _
from fcm_360ithub.fcm_functions import send_fcm_notification
def send_leave_notification(doc, method=None):
    """
    1. Automatically sets the Leave Approver from Employee Master.
    2. Collects recipients from Doc and Admin Settings.
    3. Sends FCM notification to Approvers.
    """
    
    # --- PART 1: UPDATE LEAVE APPROVER ON DOCUMENT ---
    if doc.employee and not doc.leave_approver:
        leave_approver = frappe.db.get_value("Employee", doc.employee, "leave_approver")
        
        if leave_approver:
            leave_approver_name = frappe.db.get_value("User", leave_approver, "full_name") or leave_approver
            
            # Save the value to database
            frappe.db.set_value(
                "Leave Application",
                doc.name,
                {
                    "leave_approver": leave_approver,
                    "leave_approver_name": leave_approver_name
                },
                update_modified=False # Keeps original modified timestamp
            )
            # Update current object in memory for notification harvesting
            doc.leave_approver = leave_approver

    # --- PART 2: COLLECT RECIPIENTS ---
    recipients = []

    # Recipient from the Leave Application field
    if doc.leave_approver:
        recipients.append(doc.leave_approver)

    # Recipients from 'Admin Settings' Single DocType
    admin_settings = frappe.get_single("Admin Settings")
    if hasattr(admin_settings, "leave_creation") and admin_settings.leave_creation:
        for row in admin_settings.leave_creation:
            email = row.user or row.email_id or row.email 
            if email and email not in recipients:
                recipients.append(email)

    if not recipients:
        return

    from frappe.utils import format_date
    formatted_from = format_date(doc.from_date, "dd-MMM-yyyy")
    formatted_to = format_date(doc.to_date, "dd-MMM-yyyy")
    
    employee_name = doc.employee_name or doc.employee
    title = _("Leave Approval Request")
    body = _("{0} has applied for {1} from {2} to {3} ({4} Day/s). Please review and approve.").format(
        employee_name, 
        doc.leave_type, 
        formatted_from, 
        formatted_to,
        doc.total_leave_days
    )

    # --- PART 4: FETCH FCM TOKENS & SEND ---
    for email in recipients:
        employee_data = frappe.db.get_value("Employee", 
            {"user_id": email, "status": "Active"}, 
            ["name", "custom_fcm_token"], as_dict=True)

        if employee_data and employee_data.custom_fcm_token:
            try:
                # Use send_fcm_notification helper
                send_fcm_notification(
                    token=employee_data.custom_fcm_token,
                    title=title,
                    body=body,
                    doctype="Leave Application",
                    task_id=doc.name,
                    user_doctype="User",
                    user=email,
                    notification_type="ApprovalRequest" # Passing type here
                )
            except Exception as e:
                frappe.log_error(title="FCM Approver Notification Failed", message=frappe.get_traceback())
from frappe.utils import format_date


def notify_employee_on_finish(doc, method=None):
    """
    Unified function for Leave Status Notifications.
    """
    if doc.status in ["Approved", "Rejected"]:
        trigger_employee_notification(doc, doc.status)

def trigger_employee_notification(doc, status):
    # 1. Fetch Employee Details
    employee_data = frappe.db.get_value("Employee", doc.employee, 
        ["custom_fcm_token", "user_id"], as_dict=True)

    if not employee_data or not employee_data.custom_fcm_token:
        return

    # 2. Date Formatting (dd-MMM-yyyy)
    formatted_from = format_date(doc.from_date, "dd-MMM-yyyy")
    formatted_to = format_date(doc.to_date, "dd-MMM-yyyy")

    # 3. Content Composition (No Comments included)
    if status == "Approved":
        title = _("Leave Approved! ✅")
        body = _("Your {0} application for {1} day(s) ({2} to {3}) has been Approved.").format(
            doc.leave_type, 
            doc.total_leave_days, 
            formatted_from, 
            formatted_to
        )
        notif_type = "Approval"
    else:
        title = _("Leave Rejected ❌")
        body = _("Your {0} application for {1} to {2} was Rejected.").format(
            doc.leave_type, 
            formatted_from, 
            formatted_to
        )
        notif_type = "Rejection"

    # 4. Call Notification Function
    try:
        send_fcm_notification(
            token=employee_data.custom_fcm_token,
            title=title,
            body=body,
            doctype="Leave Application",
            task_id=doc.name,
            user_doctype="User",
            user=employee_data.user_id,
            notification_type=notif_type
        )
    except Exception:
        frappe.log_error("FCM Send Detailed Notif Failed", frappe.get_traceback())








# ==========================================
# EXPENSE CLAIM LOGIC
# ==========================================

def send_expense_notification(doc, method=None):
    """
    Sets Expense Approver and notifies relevant people on new Expense Claim
    """
    # 1. Auto-set Expense Approver from Employee (if not set)
    # Assumes you have 'expense_approver' field in Employee doctype
    if doc.employee and not doc.expense_approver:
        exp_approver = frappe.db.get_value("Employee", doc.employee, "expense_approver") or \
                       frappe.db.get_value("Employee", doc.employee, "leave_approver")
        
        if exp_approver:
            frappe.db.set_value("Expense Claim", doc.name, "expense_approver", exp_approver, update_modified=False)
            doc.expense_approver = exp_approver

    recipients = []
    if doc.expense_approver:
        recipients.append(doc.expense_approver)

    # 2. Get from Admin Settings (expense_creation table)
    admin_settings = frappe.get_single("Admin Settings")
    if hasattr(admin_settings, "expense_creation") and admin_settings.expense_creation:
        for row in admin_settings.expense_creation:
            email = row.user or row.email_id or row.email 
            if email and email not in recipients:
                recipients.append(email)

    if not recipients: return

    # 3. Build Notification
    formatted_date = format_date(doc.posting_date, "dd-MMM-yyyy")
    employee_name = doc.employee_name or doc.employee
    title = _("Expense Claim Approval Request")
    body = _("{0} has submitted an Expense Claim of {1} on {2}. Please approve.").format(
        employee_name, frappe.format(doc.total_claimed_amount, "Currency"), formatted_date)

    for email in recipients:
        token = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"}, "custom_fcm_token")
        if token:
            try:
                send_fcm_notification(token=token, title=title, body=body, doctype="Expense Claim",
                    task_id=doc.name, user_doctype="User", user=email, notification_type="ExpenseRequest")
            except Exception: pass

def notify_employee_on_expense_finish(doc, method=None):
    """
    Notifies employee when Expense is Approved/Rejected
    Note: status 'Approved' usually happens on Submit, 'Rejected' on Manual change or Workflow
    """
    # Expense status values are typically: Approved, Rejected, Paid, Unpaid
    if doc.approval_status in ["Approved", "Rejected"]:
        employee_data = frappe.db.get_value("Employee", doc.employee, ["custom_fcm_token", "user_id"], as_dict=True)
        if not employee_data or not employee_data.custom_fcm_token: return

        amount = frappe.format(doc.total_sanctioned_amount or doc.total_claimed_amount, "Currency")
        
        if doc.approval_status == "Approved":
            title, body = _("Expense Claim Approved! ✅"), _("Your claim for {0} has been approved.").format(amount)
        else:
            title, body = _("Expense Claim Rejected ❌"), _("Your claim for {0} was rejected.").format(amount)

        try:
            send_fcm_notification(token=employee_data.custom_fcm_token, title=title, body=body,
                doctype="Expense Claim", task_id=doc.name, user=employee_data.user_id, notification_type="ExpenseStatus")
        except Exception: pass



# Add Task notification logic at the end of fcm_notification.py

# def send_task_notification(doc, method=None):
#     """
#     Notifies the Task Owner when a new task is created and assigned.
#     """
#     if not doc.task_owner:
#         return

#     recipient_email = doc.task_owner

#     # 1. Fetch recipient FCM token from Employee doctype
#     employee_data = frappe.db.get_value("Employee", 
#         {"user_id": recipient_email, "status": "Active"}, 
#         ["custom_fcm_token", "employee_name"], 
#         as_dict=True
#     )

#     if not employee_data or not employee_data.custom_fcm_token:
#         # Optional: Log if token is missing
#         # frappe.log_error("FCM Task Error", f"No token found for user: {recipient_email}")
#         return

#     # 2. Prepare Detailed Content
#     formatted_start = format_date(doc.exp_start_date, "dd-MMM-yyyy") if doc.exp_start_date else "Not set"
    
#     title = _("New Task Assigned: {0}").format(doc.subject)
#     body = _("You have been assigned a new task.\nPriority: {0}\nExpected Start: {1}\nProject: {2}").format(
#         doc.priority or "Normal",
#         formatted_start,
#         doc.project or _("No Project")
#     )

#     # 3. Send Notification
#     try:
#         send_fcm_notification(
#             token=employee_data.custom_fcm_token,
#             title=title,
#             body=body,
#             doctype="Task",
#             task_id=doc.name,
#             user_doctype="User",
#             user=recipient_email,
#             notification_type="TaskAssignment"
#         )
#     except Exception:
#         frappe.log_error("FCM Task Notification Failed", frappe.get_traceback())



# from frappe.utils import format_date, html2text
# from frappe import _

# def send_task_notification(doc, method=None):
#     """
#     Notifies the Task Owner via FCM and WhatsApp with Task details.
#     """
#     if not doc.task_owner:
#         return

#     recipient_email = doc.task_owner

#     # 1. Fetch FCM token and Cell Number from Employee doctype
#     employee_data = frappe.db.get_value("Employee", 
#         {"user_id": recipient_email, "status": "Active"}, 
#         ["custom_fcm_token", "employee_name", "cell_number"], 
#         as_dict=True
#     )

#     if not employee_data:
#         return

#     # 2. Prepare Detailed Content
#     formatted_start = format_date(doc.exp_start_date, "dd-MMM-yyyy") if doc.exp_start_date else "Not set"
#     formatted_end = format_date(doc.exp_end_date, "dd-MMM-yyyy") if doc.exp_end_date else "Not set"
    
#     # Convert HTML description to plain text and limit length
#     plain_description = html2text(doc.description or "")[:150] + "..." if doc.description else "No description"
    
#     title = _("Task Notification: {0}").format(doc.subject)
    
#     # Content body used for FCM
#     body = _("Priority: {0}\nDue Date: {1}\nComp. By: {2}\nDesc: {3}").format(
#         doc.priority or "Normal",
#         formatted_end,
#         doc.completed_by or "Not completed",
#         plain_description
#     )

#     # 3. Send FCM Notification (Existing)
#     if employee_data.custom_fcm_token:
#         try:
#             send_fcm_notification(
#                 token=employee_data.custom_fcm_token,
#                 title=title,
#                 body=body,
#                 doctype="Task",
#                 task_id=doc.name,
#                 user_doctype="User",
#                 user=recipient_email,
#                 notification_type="TaskAssignment"
#             )
#         except Exception:
#             frappe.log_error("FCM Task Notification Failed", frappe.get_traceback())

#     # 4. Send WhatsApp Notification (Clean Design)
#     if employee_data.get("cell_number"):
#         try:
#             wa_message = (
#                 f"*Task:* {doc.subject}\n"
#                 f"*Priority:* {doc.priority or 'Normal'}\n"
#                 f"*Due Date:* {formatted_end}\n"
#                 f"*Completed By:* {doc.completed_by or '--'}\n"
#                 f"*Description:* {plain_description}"
#             )
            
#             send_custom_whatsapp_message(
#                 mobile_number=employee_data.cell_number,
#                 message=wa_message
#             )
#         except Exception:
#             frappe.log_error("WhatsApp Task Notification Failed", frappe.get_traceback())



# def send_task_notification(doc, method=None):
#     """
#     Notifies Task Owner on creation and on reassignment.
#     """
#     if not doc.task_owner:
#         return

#     # --- DETERMINING IF WE SHOULD SEND ---
#     should_send = False

#     if method == "after_insert":
#         # Always send on first creation
#         should_send = True
    
#     elif method == "on_update":
#         # Get the document state BEFORE the save button was clicked
#         prev_doc = doc.get_doc_before_save()
        
#         # If there was a previous state AND the owner is different from the current one
#         if prev_doc and prev_doc.task_owner != doc.task_owner:
#             should_send = True
        
#         # Fallback for some workflows where get_doc_before_save is null
#         elif not prev_doc:
#             db_owner = frappe.db.get_value("Task", doc.name, "task_owner")
#             if db_owner != doc.task_owner:
#                 should_send = True

#     if not should_send:
#         return

#     # --- START NOTIFICATION LOGIC ---
#     recipient_email = doc.task_owner

#     # Fetch token
#     employee_data = frappe.db.get_value("Employee", 
#         {"user_id": recipient_email, "status": "Active"}, 
#         ["custom_fcm_token"], as_dict=True)

#     if not employee_data or not employee_data.custom_fcm_token:
#         return

#     # Content
#     title_prefix = _("New Task") if method == "after_insert" else _("Task Reassigned")
#     title = f"{title_prefix}: {doc.subject}"
    
#     body = _("Priority: {0}\nStatus: {1}").format(
#         doc.priority,
#         doc.status
#     )

#     try:
#         send_fcm_notification(
#             token=employee_data.custom_fcm_token,
#             title=title,
#             body=body,
#             doctype="Task",
#             task_id=doc.name,
#             user=recipient_email,
#             notification_type="TaskAssignment"
#         )
#     except Exception:
#         frappe.log_error("FCM Task Update Error", frappe.get_traceback())

# def send_task_notification(doc, method=None):
#     """
#     Notifies Task Owner on creation, reassignment, and completion.
#     """
#     if not doc.task_owner:
#         return

#     # --- DETERMINING IF WE SHOULD SEND ---
#     should_send = False
#     notification_event = None # To track which message to send

#     if method == "after_insert":
#         should_send = True
#         notification_event = "created"
    
#     elif method == "on_update":
#         prev_doc = doc.get_doc_before_save()
        
#         # 1. Check for Reassignment
#         if prev_doc and prev_doc.task_owner != doc.task_owner:
#             should_send = True
#             notification_event = "reassigned"
        
#         # 2. Check for Completion (New Logic)
#         elif doc.status == "Completed" and (not prev_doc or prev_doc.status != "Completed"):
#             should_send = True
#             notification_event = "completed"
        
#         # Fallback for owner check if get_doc_before_save is missing
#         elif not prev_doc:
#             db_owner = frappe.db.get_value("Task", doc.name, "task_owner")
#             if db_owner != doc.task_owner:
#                 should_send = True
#                 notification_event = "reassigned"

#     if not should_send:
#         return

#     # --- START NOTIFICATION LOGIC ---
#     recipient_email = doc.task_owner
    
#     # Content Logic based on the event
#     if notification_event == "created":
#         title_prefix = _("New Task")
#     elif notification_event == "reassigned":
#         title_prefix = _("Task Reassigned")
#     elif notification_event == "completed":
#         title_prefix = _("Task Completed")
#     else:
#         title_prefix = _("Task Update")

#     title = f"{title_prefix}: {doc.subject}"
    
#     body = _("Priority: {0}\nStatus: {1}").format(
#         doc.priority,
#         doc.status
#     )

#     # Fetch token
#     employee_data = frappe.db.get_value("Employee", 
#         {"user_id": recipient_email, "status": "Active"}, 
#         ["custom_fcm_token"], as_dict=True)

#     if not employee_data or not employee_data.custom_fcm_token:
#         return

#     try:
#         send_fcm_notification(
#             token=employee_data.custom_fcm_token,
#             title=title,
#             body=body,
#             doctype="Task",
#             task_id=doc.name,
#             user=recipient_email,
#             notification_type="TaskUpdate" # Changed to generic TaskUpdate
#         )
#     except Exception:
#         frappe.log_error("FCM Task Update Error", frappe.get_traceback())


# CHANGE: Import strip_html instead of html2text
import frappe
from frappe.utils import format_date, strip_html
from frappe import _
from webtoolex_whatsapp.webtoolex_whatsapp.doctype.whatsapp_instance.whatsapp_instance import send_custom_whatsapp_message

def send_task_notification(doc, method=None):
    if not doc.task_owner:
        return

    # Fetch settings from Admin Settings Single Doctype
    settings = frappe.get_cached_doc("Admin Settings")

    # 1. Determine Event type
    notification_event = None
    prev_doc = doc.get_doc_before_save() if method == "on_update" else None

    if method == "after_insert":
        notification_event = "created"
    elif method == "on_update":
        if prev_doc and prev_doc.task_owner != doc.task_owner:
            notification_event = "reassigned"
        elif doc.status == "Completed" and (not prev_doc or prev_doc.status != "Completed"):
            notification_event = "completed"

    if not notification_event:
        return

    # 2. Get Employee Notification Data
    emp = frappe.db.get_value("Employee", {"user_id": doc.task_owner, "status": "Active"}, 
        ["custom_fcm_token", "cell_number"], as_dict=True)
    
    if not emp: return

    # Prepare Data
    due_date = format_date(doc.exp_end_date, "dd-MMM-yyyy") if doc.exp_end_date else "--"
    description = strip_html(doc.description or "")[:120].strip() + ".."
    
    prefix_map = {
        "created": _("New Task Assigned"),
        "reassigned": _("Task Reassigned"),
        "completed": _("Task Completed")
    }
    event_label = prefix_map.get(notification_event, "Task Update")

    # 3. Send FCM
    if emp.custom_fcm_token:
        try:
            send_fcm_notification(
                token=emp.custom_fcm_token,
                doctype="Task",
                task_id=doc.name,
                title=f"{event_label}: {doc.subject}",
                body=_("Status: {0} | Due: {1}").format(doc.status, due_date),
                user=doc.task_owner
            )
        except: pass

    # 4. Send WhatsApp with Admin Settings Check
    if settings.enable_whatsapp and emp.cell_number:
        # Toggle Logic
        wa_allowed = False
        if notification_event in ["created", "reassigned"] and settings.send_on_task_creation:
            wa_allowed = True
        elif notification_event == "completed" and settings.send_on_task_completion:
            wa_allowed = True
        
        if wa_allowed:
            try:
                wa_message = (
                    f"*{event_label}*\n\n"
                    f"*Subject:* {doc.subject}\n"
                    f"*Status:* {doc.status}\n"
                    f"*Due Date:* {due_date}\n"
                    f"*Details:* {description}"
                )
                send_custom_whatsapp_message(mobile_number=emp.cell_number, message=wa_message)
            except Exception:
                frappe.log_error(f"WhatsApp Error for Task {doc.name}", frappe.get_traceback())

from frappe.utils import today, getdate

# def send_daily_task_summary():
#     """
#     Cron Job: Runs daily at 9 AM.
#     Gathers active tasks for every owner and sends a summary FCM.
#     """
#     current_date = getdate(today())
    
#     # 1. Fetch all active tasks with owners
#     active_tasks = frappe.get_all("Task", 
#         filters={
#             "status": ["in", ["Open", "Working", "Pending Review", "Overdue"]],
#             "task_owner": ["is", "set"]
#         }, 
#         fields=["name", "subject", "task_owner", "status", "exp_end_date"]
#     )

#     if not active_tasks:
#         return

#     # 2. Group tasks by owner
#     user_summaries = {}
#     for task in active_tasks:
#         owner = task.task_owner
#         if owner not in user_summaries:
#             user_summaries[owner] = {"total": 0, "overdue": 0, "due_today": 0}
        
#         user_summaries[owner]["total"] += 1
        
#         # Check deadline status
#         if task.exp_end_date:
#             due_date = getdate(task.exp_end_date)
#             if due_date < current_date:
#                 user_summaries[owner]["overdue"] += 1
#             elif due_date == current_date:
#                 user_summaries[owner]["due_today"] += 1

#     # 3. Iterate through summaries and send notifications
#     for email, counts in user_summaries.items():
#         # Only send if they have any active tasks
#         if counts["total"] == 0:
#             continue

#         # Get Token
#         token = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"}, "custom_fcm_token")
        
#         if not token:
#             continue

#         # 4. Prepare Message
#         title = _("📋 Daily Task Summary")
        
#         body = _("Good morning! Here is your task update:\n")
#         body += _("• Total Active: {0}\n").format(counts["total"])
        
#         if counts["due_today"] > 0:
#             body += _("• Ending Today: {0} 🕒\n").format(counts["due_today"])
            
#         if counts["overdue"] > 0:
#             body += _("• Overdue: {0} ⚠️").format(counts["overdue"])
#         else:
#             body += _("Keep up the great work!")

#         # 5. Send Notification
#         try:
#             send_fcm_notification(
#                 token=token,
#                 title=title,
#                 body=body,
#                 user=email,
#                 notification_type="DailySummary"
#             )
#         except Exception:
#             frappe.log_error(f"Daily Cron FCM Failed for {email}", frappe.get_traceback())





import frappe
from frappe.utils import getdate, today
from frappe import _
from webtoolex_whatsapp.webtoolex_whatsapp.doctype.whatsapp_instance.whatsapp_instance import send_custom_whatsapp_message

def send_daily_task_summary():
    """Daily summary at 9 AM with Admin Settings Control."""
    
    # Fetch Settings from 'Admin Settings' Single Doctype
    settings = frappe.get_cached_doc("Admin Settings")
    current_date = getdate(today())
    
    # 1. Fetch active tasks
    active_tasks = frappe.get_all("Task", 
        filters={
            "status": ["in", ["Open", "Working", "Pending Review", "Overdue"]],
            "task_owner": ["is", "set"]
        }, 
        fields=["name", "subject", "task_owner", "status", "exp_end_date"]
    )

    if not active_tasks:
        return

    # 2. Group by owner
    user_summaries = {}
    for task in active_tasks:
        owner = task.task_owner
        if owner not in user_summaries:
            user_summaries[owner] = {"total": 0, "overdue": 0, "due_today": 0}
        
        user_summaries[owner]["total"] += 1
        if task.exp_end_date:
            due_date = getdate(task.exp_end_date)
            if due_date < current_date:
                user_summaries[owner]["overdue"] += 1
            elif due_date == current_date:
                user_summaries[owner]["due_today"] += 1

    # 3. Notification Loop
    for email, counts in user_summaries.items():
        emp = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"}, 
            ["custom_fcm_token", "cell_number", "employee_name"], as_dict=True)
        
        if not emp: continue

        # FCM - Standard sending
        if emp.custom_fcm_token:
            try:
                send_fcm_notification(
                    token=emp.custom_fcm_token,
                    title=_("📋 Daily Task Summary"),
                    body=_("Active: {0} | Due Today: {1}").format(counts["total"], counts["due_today"]),
                    user=email
                )
            except: pass

        # WhatsApp - Controlled by Admin Settings
        if settings.enable_whatsapp and settings.send_daily_summary_wa and emp.cell_number:
            try:
                wa_msg = (
                    f"🌞 *Daily Task Summary*\n\n"
                    f"📝 *Total Tasks:* {counts['total']}\n"
                    f"🕒 *Due Today:* {counts['due_today']}\n"
                    f"⚠️ *Overdue:* {counts['overdue']}"
                )
                send_custom_whatsapp_message(mobile_number=emp.cell_number, message=wa_msg)
            except Exception:
                frappe.log_error(f"Daily Cron WA Error for {email}", frappe.get_traceback())


def send_activity_creation_notification(doc, method=None):
    """
    Fires when a new Event Activity is created to notify the assigned user.
    """
    if not doc.assigned_to:
        return
    if not doc.status == "Open":
        return
    # Get Token
    token = frappe.db.get_value("Employee", {"user_id": doc.assigned_to, "status": "Active"}, "custom_fcm_token")
    if not token:
        return

    # Content
    ref_info = f" ({doc.reference_type})" if doc.reference_type else ""
    title = _("New Activity Assigned: {0}").format(doc.category or "Activity")
    body = _("Subject: {0}\nAssigned to you for {1}{2}.\nStarts: {3}").format(
        doc.subject,
        doc.category or "Follow-up",
        ref_info,
        format_date(doc.starts_on, "dd-MMM-yyyy") if doc.starts_on else _("Not set")
    )

    try:
        send_fcm_notification(
            token=token,
            title=title,
            body=body,
            doctype="Event Activity",
            task_id=doc.name,
            user=doc.assigned_to,
            notification_type="ActivityAssignment"
        )
    except Exception:
        frappe.log_error("Activity Creation FCM Failed", frappe.get_traceback())




from frappe.utils import getdate, today, now_datetime

def send_daily_activity_summary():
    """
    9:15 AM Summary: breakdown of Today and Overdue Activities.
    """
    curr_date = getdate(today())
    
    # 1. Fetch Open Activities
    activities = frappe.get_all("Event Activity",
        filters={
            "status": "Open",
            "assigned_to": ["is", "set"],
            "starts_on": ["is", "set"]
        },
        fields=["name", "category", "reference_type", "starts_on", "assigned_to"]
    )

    if not activities:
        return

    # 2. Group data per user
    summary_map = {} # Structure: { user: { 'overdue': [], 'today': [] } }

    for act in activities:
        user = act.assigned_to
        start_date = getdate(act.starts_on)
        
        if user not in summary_map:
            summary_map[user] = {"overdue": [], "today": []}
        
        # Determine status bucket
        # Storing dicts of Category & Reference Type
        info = {"cat": act.category or "Meeting", "ref": act.reference_type or "Misc"}
        
        if start_date < curr_date:
            summary_map[user]["overdue"].append(info)
        elif start_date == curr_date:
            summary_map[user]["today"].append(info)

    # 3. Construct and Send messages
    for email, buckets in summary_map.items():
        if not buckets["overdue"] and not buckets["today"]:
            continue
            
        token = frappe.db.get_value("Employee", {"user_id": email, "status": "Active"}, "custom_fcm_token")
        if not token:
            continue

        title = _("🌞 Daily Activity Brief")
        body = ""

        # Construct Today's Breakdown
        if buckets["today"]:
            body += _("📍 Scheduled for Today ({0}):\n").format(len(buckets["today"]))
            for item in buckets["today"]:
                body += f"• {item['cat']} [{item['ref']}]\n"
        
        # Construct Overdue Breakdown
        if buckets["overdue"]:
            if body: body += "\n" # Add gap
            body += _("⚠️ OVERDUE ({0}):\n").format(len(buckets["overdue"]))
            for item in buckets["overdue"]:
                body += f"• {item['cat']} [{item['ref']}]\n"

        try:
            send_fcm_notification(
                token=token,
                title=title,
                body=body.strip(),
                user=email,
                notification_type="ActivitySummary"
            )
        except Exception:
            frappe.log_error(f"Daily Activity Summary FCM Failed for {email}", frappe.get_traceback())