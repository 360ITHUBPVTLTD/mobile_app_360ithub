# Copyright (c) 2026, 360ithub and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

LEAVE_TYPES = ["Sick Leave", "Casual Leave"]


def execute(filters=None):
	filters = frappe._dict(filters or {})

	if not filters.fiscal_year:
		frappe.throw(_("Please select a Fiscal Year."))

	# The leave year runs Apr-Mar, matching the Fiscal Year record, so the
	# reporting window is taken straight from it.
	filters.from_date, filters.to_date = frappe.db.get_value(
		"Fiscal Year", filters.fiscal_year, ["year_start_date", "year_end_date"]
	)

	if not (filters.from_date and filters.to_date):
		frappe.throw(_("Fiscal Year {0} has no start/end date set.").format(filters.fiscal_year))

	data = get_data(filters)
	return get_columns(), data


def get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 120,
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch", "width": 120},
		{
			"fieldname": "department",
			"label": _("Department"),
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"fieldname": "leave_type",
			"label": _("Leave Type"),
			"fieldtype": "Link",
			"options": "Leave Type",
			"width": 130,
		},
		{"fieldname": "allocated", "label": _("Allocated"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "claimed", "label": _("Claimed"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "unused", "label": _("Unused / Lapsed"), "fieldtype": "Float", "precision": 1, "width": 130},
		{"fieldname": "balance", "label": _("Balance"), "fieldtype": "Float", "precision": 1, "width": 100},
	]


def get_data(filters):
	employees = get_employees(filters)
	if not employees:
		return []

	ledger = get_ledger_totals(filters, list(employees))
	leave_types = [filters.leave_type] if filters.leave_type else LEAVE_TYPES

	data = []
	for emp_id, emp in employees.items():
		for leave_type in leave_types:
			totals = ledger.get((emp_id, leave_type))
			if not totals:
				continue

			allocated = flt(totals["allocated"], 2)
			claimed = flt(totals["claimed"], 2)
			unused = flt(totals["unused"], 2)

			data.append(
				{
					"employee": emp_id,
					"employee_name": emp.employee_name,
					"branch": emp.branch,
					"department": emp.department,
					"leave_type": leave_type,
					"allocated": allocated,
					"claimed": claimed,
					"unused": unused,
					"balance": flt(allocated - claimed - unused, 2),
				}
			)

	data.sort(key=lambda row: (row["branch"] or "", row["employee_name"] or "", row["leave_type"]))
	return data


def get_employees(filters):
	# Default to every status: employees who have Left still have unused leave
	# to be encashed at exit, so hiding them by default would lose them.
	emp_filters = {}
	if filters.employee_status:
		emp_filters["status"] = filters.employee_status

	if filters.employee:
		emp_filters["name"] = filters.employee
	if filters.branch:
		emp_filters["branch"] = filters.branch
	if filters.department:
		emp_filters["department"] = filters.department
	if filters.company:
		emp_filters["company"] = filters.company

	employees = frappe.get_all(
		"Employee",
		filters=emp_filters,
		fields=["name", "employee_name", "branch", "department"],
	)
	return {emp.name: emp for emp in employees}


def get_ledger_totals(filters, employees):
	"""Aggregate the leave ledger into allocated / claimed / lapsed buckets.

	Leave Ledger Entry is the source of truth: allocations are positive, leave
	applications negative, and expiry entries negative with is_expired = 1.
	"""
	conditions = {
		"docstatus": 1,
		"employee": ["in", employees],
		"from_date": ["<=", filters.to_date],
		"to_date": [">=", filters.from_date],
		"leave_type": ["in", [filters.leave_type] if filters.leave_type else LEAVE_TYPES],
	}

	entries = frappe.get_all(
		"Leave Ledger Entry",
		filters=conditions,
		fields=["employee", "leave_type", "leaves", "transaction_type", "is_expired"],
	)

	totals = {}
	for entry in entries:
		key = (entry.employee, entry.leave_type)
		bucket = totals.setdefault(key, {"allocated": 0.0, "claimed": 0.0, "unused": 0.0})

		leaves = flt(entry.leaves)
		if entry.is_expired:
			# Expiry entries are negative; report the lapsed amount as positive.
			bucket["unused"] += abs(leaves)
		elif entry.transaction_type == "Leave Allocation":
			bucket["allocated"] += leaves
		else:
			# Leave Application (and any other consumption) is negative.
			bucket["claimed"] += abs(leaves)

	return totals
