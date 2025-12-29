import frappe
from frappe import _
from typing import Any, Dict
from .utils import get_employee_by_user, get_last_log_details



@frappe.whitelist()
def get_home_page() -> Dict[str, Any]:
	"""Get home page data including employee and log details.

	Returns:
		Dict[str, Any]: Dictionary containing employee data and log details
	"""
	try:
		current_user = frappe.session.user
		if not current_user:
			frappe.throw(_("No active user session found"))

		emp_data = get_employee_by_user(current_user)
		if not emp_data:
			frappe.throw(_("Employee data not found for current user"))

		log_details = get_last_log_details(emp_data.get("name"))

		return {"emp_data": emp_data, "log_details": log_details}
	except Exception as e:
		frappe.log_error(f"Error fetching home page data: {str(e)}")
		frappe.throw(_("Failed to fetch home page data {0}").format(str(e)))
