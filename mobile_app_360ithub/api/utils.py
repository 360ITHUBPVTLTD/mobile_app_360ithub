import frappe


@frappe.whitelist()
def get_employee_by_user(user, fields=["*"]):
    if isinstance(fields, str):
        fields = [fields]
    emp_data = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        fields,
        as_dict=1,
    )
    return emp_data
@frappe.whitelist()
def get_last_log_details(emp_id=None):
    """
    Get the last log type and time of the given employee

    Args:
        emp_id (str): The employee id for which the last log needs to be retrieved.
            If not provided, the employee id of the current user is used.

    Returns:
        dict: The last log's type and time.
    """
    if not emp_id:
        emp_id = get_employee_by_user(frappe.session.user).get("name")
    last_log = frappe.db.get_value(
        "Employee Checkin",
        {"employee": emp_id},
        ["log_type", "time"],
        order_by="time DESC",
        as_dict=1,
    )
    return last_log



import frappe

@frappe.whitelist()
def update_leave_status_and_submit(leave_application_id, status):
    """
    Updates the status of a Leave Application and submits it.
    Only allowed for users with the "Leave Approver" role (or Administrator).

    :param leave_application_id: The name (ID) of the Leave Application document.
    :param status: The new status ('Approved' or 'Rejected').
    """
    # --- ROLE CHECK (Compatible with older Frappe versions) ---
    current_user_roles = frappe.get_roles(frappe.session.user)

    # Check if the user is Administrator OR if "Leave Approver" is in their roles
    if not (frappe.session.user == "Administrator" or "Leave Approver" in current_user_roles):
        frappe.throw("Permission Denied: Only Leave Approvers or Administrator can approve or reject leave applications using this function.")
    # --- END ROLE CHECK ---

    if status not in ["Approved", "Rejected"]:
        frappe.throw("Invalid status. Must be 'Approved' or 'Rejected'.")

    try:
        leave_app = frappe.get_doc("Leave Application", leave_application_id)

        if leave_app.status not in ["Open", "Pending", "Rejected", "Approved"]:
            frappe.throw(f"Leave Application {leave_application_id} cannot be updated from status '{leave_app.status}'. "
                         "It must be 'Open' or 'Pending' to be processed.")

        # Set the new status
        leave_app.status = status
        leave_app.save()

        # Submit the Leave Application if it's currently a draft
        if leave_app.docstatus == 0:
            leave_app.submit()
        # If already submitted (docstatus == 1), the save() above handles the status change
        # without needing a re-submit.

        # frappe.msgprint(f"Leave Application {leave_application_id} status updated to {status} and submitted successfully.")
        return {"status": "success", "message": f"Leave Application {leave_application_id} updated to {status} and submitted."}

    except frappe.exceptions.DocstatusTransitionError as e:
        frappe.throw(f"Docstatus Transition Error for {leave_application_id}: {e}")
    except frappe.exceptions.ValidationError as e:
        frappe.throw(f"Validation Error for {leave_application_id}: {e}")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_leave_status_and_submit_error")
        frappe.throw(f"An unexpected error occurred: {e}")



import frappe

@frappe.whitelist()
def update_expense_claim_status_and_submit(expense_claim_id, status):
    """
    Updates the approval_status of an Expense Claim and submits it.
    Only allowed for users with the "Expense Approver" role (or Administrator).

    :param expense_claim_id: The name (ID) of the Expense Claim document.
    :param status: The new approval status ('Approved', 'Rejected', etc.).
                                 Commonly 'Approved' or 'Rejected'.
    """
    # --- ROLE CHECK ---
    current_user_roles = frappe.get_roles(frappe.session.user)

    # Check if the user is Administrator OR if "Expense Approver" is in their roles
    if not (frappe.session.user == "Administrator" or "Expense Approver" in current_user_roles):
        frappe.throw("Permission Denied: Only Expense Approvers or Administrator can approve or reject expense claims using this function.")
    # --- END ROLE CHECK ---

    # Validate the new approval status
    # Frappe's Expense Claim has specific statuses: Draft, Submitted, Approved, Rejected, Paid, Cancelled
    # The 'approval_status' field itself can be 'Pending', 'Approved', 'Rejected'
    valid_approval_statuses = ["Pending", "Approved", "Rejected"]
    if status not in valid_approval_statuses:
        frappe.throw(f"Invalid approval status. Must be one of: {', '.join(valid_approval_statuses)}.")

    try:
        expense_claim = frappe.get_doc("Expense Claim", expense_claim_id)

        # Check current document status to prevent updating already paid/cancelled claims
        # You might adjust this based on your specific workflow.
        # Typically, you'd approve/reject when the docstatus is Submitted (1)
        # or approval_status is 'Pending'.
        if expense_claim.docstatus == 2: # Cancelled
            frappe.throw(f"Expense Claim {expense_claim_id} is Cancelled and cannot be updated.")
        # if expense_claim.docstatus == 0: # If it's a draft, it needs to be submitted first
        #      frappe.throw(f"Expense Claim {expense_claim_id} is a Draft. Please submit it before approving or rejecting.")
        # # If it's already approved/rejected, you might not want to change it again via this function
        # Uncomment the following if you want to prevent re-approving/re-rejecting
        # if expense_claim.approval_status in ["Approved", "Rejected"] and status != expense_claim.approval_status:
        #     frappe.throw(f"Expense Claim {expense_claim_id} is already {expense_claim.approval_status}. Status cannot be changed via this function.")


        # Set the new approval status
        expense_claim.approval_status = status
        expense_claim.status = "Unpaid"
        expense_claim.save()

        # If the Expense Claim is a Draft (docstatus 0) and the new status implies submission, submit it.
        # In Frappe's Expense Claim, 'approval_status' is typically updated *after* submission.
        # If your workflow requires submitting a draft and then setting approval_status,
        # you might do it like this:
        if expense_claim.docstatus == 0:
            expense_claim.submit()
            # After submission, the approval_status might be 'Pending' by default,
            # so you may need to save again if setting directly to Approved/Rejected upon submission.
            # However, typically the submission itself sets it to Pending, and then an Approver changes it.
            # The current logic assumes it's already submitted (docstatus=1) or will be submitted.
            expense_claim.save() # Save the approval_status again after initial submit if it's a new doc

        # frappe.msgprint(f"Expense Claim {expense_claim_id} approval status updated to {status} and document processed successfully.")
        return {"status": "success", "message": f"Expense Claim {expense_claim_id} updated to {status} and processed."}

    except frappe.exceptions.DocstatusTransitionError as e:
        frappe.throw(f"Docstatus Transition Error for {expense_claim_id}: {e}")
    except frappe.exceptions.ValidationError as e:
        frappe.throw(f"Validation Error for {expense_claim_id}: {e}")
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_expense_claim_status_and_submit_error")
        frappe.throw(f"An unexpected error occurred: {e}")
