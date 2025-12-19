import frappe
from frappe.utils import getdate, add_days, nowdate

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Task ID", "fieldname": "name", "fieldtype": "Link", "options": "Task", "width": 140},
        {"label": "Subject", "fieldname": "subject", "fieldtype": "Data", "width": 200},
        {"label": "Task Owner", "fieldname": "task_owner", "fieldtype": "Link", "options": "User", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Priority", "fieldname": "priority", "fieldtype": "Data", "width": 100},
        {"label": "Type", "fieldname": "type", "fieldtype": "Data", "width": 120},
        {"label": "Expected Start Date", "fieldname": "exp_start_date", "fieldtype": "Date", "width": 130},
        {"label": "Expected End Date", "fieldname": "exp_end_date", "fieldtype": "Date", "width": 130},
		{"label": "Description", "fieldname": "description", "fieldtype": "Text", "width": 200},
        # {"label": "Progress", "fieldname": "progress", "fieldtype": "Int", "width": 90},
        # {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
    ]


def get_data(filters):
    conditions = "1=1"
    values = {}

    # Task Owner
    if filters.get("task_owner"):
        conditions += " AND task_owner = %(task_owner)s"
        values["task_owner"] = filters.get("task_owner")

    # Status
    if filters.get("status"):
        conditions += " AND status = %(status)s"
        values["status"] = filters.get("status")

    # Priority
    if filters.get("priority"):
        conditions += " AND priority = %(priority)s"
        values["priority"] = filters.get("priority")

    # Type
    if filters.get("type"):
        conditions += " AND type = %(type)s"
        values["type"] = filters.get("type")

    # Date Range Filter
    if filters.get("exp_end_date"):
        start, end = filters.get("exp_end_date")
        conditions += " AND exp_end_date BETWEEN %(start_date)s AND %(end_date)s"
        values["start_date"] = start
        values["end_date"] = end

    # Timespan Filter (today, this week, etc.)
    if filters.get("timespan"):
        timespan_conditions, span_values = get_timespan_condition(filters["timespan"])
        if timespan_conditions:
            conditions += f" AND {timespan_conditions}"
            values.update(span_values)

    query = f"""
        SELECT
            name, subject, task_owner, status, priority, type,description,
             exp_end_date AS exp_end_date,
            progress, project
        FROM `tabTask`
        WHERE {conditions}
        ORDER BY exp_end_date ASC
    """

    return frappe.db.sql(query, values, as_dict=True)


def get_timespan_condition(timespan):
    """Handle simple dynamic date filters."""
    today = getdate(nowdate())
    condition = ""
    values = {}

    if timespan == "Today":
        condition = "exp_end_date = %(today)s"
        values["today"] = today

    elif timespan == "This Week":
        start = add_days(today, -today.weekday())
        end = add_days(start, 6)
        condition = "exp_end_date BETWEEN %(start)s AND %(end)s"
        values = {"start": start, "end": end}

    elif timespan == "This Month":
        start = today.replace(day=1)
        end = add_days(start, 31)  # rough upper limit
        condition = "exp_end_date BETWEEN %(start)s AND %(end)s"
        values = {"start": start, "end": end}

    elif timespan == "Overdue":
        condition = "exp_end_date < %(today)s AND status != 'Completed'"
        values["today"] = today

    return condition, values
