import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, get_first_day, get_last_day, nowdate
from typing import Any, Dict, List, Optional
from .utils import get_employee_by_user
from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period
from hrms.hr.report.employee_leave_balance.employee_leave_balance import (
	get_allocated_and_expired_leaves,
	get_opening_balance,
)


@frappe.whitelist()
def get_leave_data(year: Optional[int] = None) -> List[Dict[str, Any]]:
	"""Get leave data for the current employee for a specific year.

	Args:
		year (Optional[int]): Year to fetch leave data for. Defaults to current year.

	Returns:
		List[Dict[str, Any]]: List of leave data dictionaries
	"""
	try:
		current_user = frappe.session.user
		if not current_user:
			frappe.throw(_("No active user session found"))

		# Get current year if not provided
		if not year:
			year = getdate(nowdate()).year

		# Validate year
		if not isinstance(year, int) or year < 1900 or year > 2100:
			frappe.throw(_("Invalid year provided: {0}").format(year))

		# Calculate date range for the year
		from_date = get_first_day(f"{year}-01-01")
		to_date = get_last_day(f"{year}-12-31")

		# Get employee data
		employee_data = get_employee_by_user(current_user)
		if not employee_data:
			frappe.throw(_("Employee data not found for current user"))

		return get_employee_leave_data([employee_data], to_date, from_date)

	except Exception as e:
		frappe.log_error(f"Error fetching leave data: {str(e)}")
		frappe.throw(_("Failed to fetch leave data {0}").format(str(e)))

@frappe.whitelist()
def get_employee_leave_data(
	employees: List[Dict], to_date: str, from_date: str
) -> List[Dict[str, Any]]:
	"""Get comprehensive leave data for employees.

	Args:
		employees (List[Dict]): List of employee dictionaries
		to_date (str): End date for leave data
		from_date (str): Start date for leave data

	Returns:
		List[Dict[str, Any]]: List of leave data for each employee and leave type
	"""
	try:
		if not employees:
			return []

		if not from_date or not to_date:
			frappe.throw(_("From date and to date are required"))

		# Get system precision for float calculations
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

		# Get all leave types
		leave_types = frappe.get_all("Leave Type", pluck="name", order_by="name")

		if not leave_types:
			frappe.throw(_("No leave types found"))

		data = []

		for employee in employees:
			if not employee or not employee.get("name"):
				continue

			employee_name = employee.get("name")
			employee_display_name = employee.get("employee_name", employee_name)

			for leave_type in leave_types:
				try:
					leave_data = _calculate_leave_balance(
						employee_name=employee_name,
						employee_display_name=employee_display_name,
						leave_type=leave_type,
						from_date=from_date,
						to_date=to_date,
						precision=precision,
					)

					if leave_data:
						data.append(leave_data)

				except Exception as e:
					frappe.log_error(
						f"Error calculating leave data for {employee_name}, {leave_type}: {str(e)}"
					)
					continue

		return data

	except Exception as e:
		frappe.log_error(f"Error in get_employee_leave_data: {str(e)}")
		raise


def _calculate_leave_balance(
	employee_name: str,
	employee_display_name: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	precision: int,
) -> Optional[Dict[str, Any]]:
	"""Calculate leave balance for a specific employee and leave type.

	Args:
		employee_name (str): Employee ID
		employee_display_name (str): Employee display name
		leave_type (str): Leave type name
		from_date (str): Start date
		to_date (str): End date
		precision (int): Float precision for calculations

	Returns:
		Optional[Dict[str, Any]]: Leave balance data or None if calculation fails
	"""
	try:
		# Calculate leaves taken (negative value from system)
		leaves_taken = get_leaves_for_period(employee_name, leave_type, from_date, to_date) * -1

		# Get allocation and expiry data
		new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
			from_date, to_date, employee_name, leave_type
		)

		# Calculate opening balance
		filters = frappe._dict({"from_date": from_date, "to_date": to_date})
		opening_balance = get_opening_balance(
			employee_name, leave_type, filters, carry_forwarded_leaves
		)

		# Calculate closing balance
		closing_balance = new_allocation + opening_balance - (expired_leaves + leaves_taken)

		# Special handling for Leave Without Pay
		if leave_type == "Leave Without Pay":
			closing_balance = 0

		# Prepare result dictionary
		result = frappe._dict(
			{
				"employee": employee_name,
				"employee_name": employee_display_name,
				"leave_type": leave_type,
				"leaves_allocated": flt(new_allocation, precision),
				"leaves_expired": flt(expired_leaves, precision),
				"opening_balance": flt(opening_balance, precision),
				"leaves_taken": flt(leaves_taken, precision),
				"closing_balance": flt(closing_balance, precision),
				"indent": 1,
			}
		)

		return result

	except Exception as e:
		frappe.log_error(
			f"Error calculating leave balance for {employee_name}, {leave_type}: {str(e)}"
		)
		return None
