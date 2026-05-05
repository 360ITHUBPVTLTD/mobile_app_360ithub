import frappe
from datetime import timedelta
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    
    # Do not return raw HTML/JS here. Use the .js file for DOM manipulation.
    # Standard return format: columns, data, message, chart, report_summary
    return columns, data


def get_columns():
    return[
        {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 142},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        # {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 150},
        # {"label": "Designation", "fieldname": "designation", "fieldtype": "Data", "width": 150},
        {"label": "Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 120},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 80},
        {"label": "First Login", "fieldname": "first_login", "fieldtype": "Time", "width": 100},
        {"label": "Last Logout", "fieldname": "last_logout", "fieldtype": "Time", "width": 100},

        {"label": "Actual Working Hours", "fieldname": "actual_working_hours", "fieldtype": "Data", "width": 150},
        {"label": "Ideal Shift Hours", "fieldname": "shift_hours", "fieldtype": "Data", "width": 150},
        {"label": "Variance", "fieldname": "variance_hours", "fieldtype": "Data", "width": 180},

        {"label": "Total Login Duration", "fieldname": "total_duration", "fieldtype": "Data", "width": 100},
        {"label": "Total Break Hours", "fieldname": "total_break_hours", "fieldtype": "Data", "width": 100},
        {"label": "Late Entry", "fieldname": "late_entry", "fieldtype": "Data", "width": 80},
        {"label": "Late Minutes", "fieldname": "late_minutes", "fieldtype": "Data", "width": 80},
        {"label": "Early Exit", "fieldname": "early_exit", "fieldtype": "Data", "width": 80},
        {"label": "Early Exit Minutes", "fieldname": "early_exit_minutes", "fieldtype": "Data", "width": 100},
        
        # {"label": "Test", "fieldname": "test", "fieldtype": "Small Text", "width": 800},
    ]

def get_data(filters):
    conditions = " WHERE emp.status = 'Active' AND att.docstatus = 1"
    params = {}

    if filters.get("date_range") and len(filters.get("date_range")) == 2:
        conditions += " AND att.attendance_date BETWEEN %(start_date)s AND %(end_date)s"
        params.update({
            "start_date": filters["date_range"][0], 
            "end_date": filters["date_range"][1]
        })

    if filters.get("late_entry"):
        conditions += " AND att.late_entry = 1"

    if filters.get("early_exit"):
        conditions += " AND att.early_exit = 1"

    if filters.get("employee"):
        conditions += " AND att.employee = %(employee)s"
        params["employee"] = filters["employee"]
    
    if filters.get("status"):
        conditions += " AND att.status = %(status)s"
        params["status"] = filters["status"]

    # Joined tabShift Type directly to prevent the N+1 Query issue
    attendance_query = f"""
        SELECT 
            emp.name AS employee,
            emp.employee_name,
            emp.department,
            emp.designation,
            att.attendance_date,
            att.status,
            TIME(att.in_time) AS first_login,
            TIME(att.out_time) AS last_logout,
            att.working_hours AS total_duration,
            att.name AS attendance_id,
            att.late_entry,
            att.early_exit,
            att.shift,
            sh.start_time AS shift_start_time,
            sh.end_time AS shift_end_time,
            sh.custom_lunch_break
        FROM `tabEmployee` emp
        JOIN `tabAttendance` att ON att.employee = emp.name
        LEFT JOIN `tabShift Type` sh ON sh.name = att.shift
        {conditions}
        ORDER BY att.attendance_date DESC
    """

    attendance_data = frappe.db.sql(attendance_query, params, as_dict=True)
    
    if not attendance_data:
        return []

    attendance_ids = tuple(d["attendance_id"] for d in attendance_data)
    
    # Fetch all relevant Checkin Logs in one go
    checkin_query = """
        SELECT ec.employee, ec.time, ec.log_type, ec.attendance
        FROM `tabEmployee Checkin` ec
        WHERE ec.attendance IN %(attendance_ids)s
        ORDER BY ec.employee, ec.time
    """
    checkin_logs = frappe.db.sql(checkin_query, {"attendance_ids": attendance_ids}, as_dict=True)

    # Map logs to attendance ID
    checkin_map = frappe._dict()
    for log in checkin_logs:
        checkin_map.setdefault(log.attendance,[]).append(log)

    # Process all calculations in a SINGLE loop
    for record in attendance_data:
        attendance_id = record["attendance_id"]
        
        # 1. Calculate Break Hours
        break_seconds = 0
        if attendance_id in checkin_map:
            logs = checkin_map[attendance_id]
            last_out_time = None

            for log in logs:
                if log.log_type == "OUT":
                    last_out_time = log.time
                elif log.log_type == "IN" and last_out_time:
                    # direct datetime subtraction
                    break_seconds += (log.time - last_out_time).total_seconds()
                    last_out_time = None
                    
        record["total_break_hours"] = format_break_hours(break_seconds)

        # ✅ Get login/logout
        first_login = record.get("first_login")
        last_logout = record.get("last_logout")

        # Convert to datetime safely
        actual_seconds = 0

        if first_login and last_logout:
            actual_seconds = (last_logout - first_login).total_seconds()

        # Subtract break
        break_hours_str = record.get("total_break_hours") or "0h 0m"

        # Convert "Xh Ym" → seconds
        import re
        match = re.match(r"(\d+)h\s*(\d+)m", break_hours_str)
        if match:
            bh = int(match.group(1))
            bm = int(match.group(2))
            break_seconds = bh * 3600 + bm * 60
        else:
            break_seconds = 0

        # Final actual working
        actual_seconds = actual_seconds - break_seconds

        record["actual_working_hours"] = format_break_hours(actual_seconds)

        # Shift timing
        shift_start = record.get("shift_start_time")
        shift_end = record.get("shift_end_time")

        # Lunch break (your field is HOURS → 0.5 = 30 min)
        lunch_hours = record.get("custom_lunch_break") or 0
        lunch_seconds = lunch_hours * 3600

        if shift_start and shift_end:
            shift_seconds = (shift_end - shift_start).total_seconds()
            
            # ✅ FIX: subtract lunch
            ideal_seconds = shift_seconds - lunch_seconds
        else:
            ideal_seconds = 0

        record["shift_hours"] = format_break_hours(ideal_seconds)
        # Variance
        variance_seconds = ideal_seconds - actual_seconds

        if variance_seconds < 0:
            record["variance_hours"] = f"<span style='color:green;font-weight:bold;'>+ {format_break_hours(abs(variance_seconds))}</span>"
        elif variance_seconds > 0:
            record["variance_hours"] = f"<span style='color:red;font-weight:bold;'>- {format_break_hours(abs(variance_seconds))}</span>"
        else:
            record["variance_hours"] = format_break_hours(0)

        # 2. Process Late Entry / Early Exit Math (Handling timedeltas correctly)
        first_login = record.get("first_login")
        last_logout = record.get("last_logout")
        shift_start = record.get("shift_start_time")
        shift_end = record.get("shift_end_time")

        is_late = record["late_entry"] == 1
        is_early = record["early_exit"] == 1

        record["late_entry"] = "Yes" if is_late else "No"
        record["early_exit"] = "Yes" if is_early else "No"

        # Calculate late minutes
        if is_late and first_login and shift_start and first_login > shift_start:
            late_secs = (first_login - shift_start).total_seconds()
            record["late_minutes"] = format_break_hours(late_secs)
        else:
            record["late_minutes"] = "0h 0m"

        # Calculate early exit minutes
        if is_early and last_logout and shift_end and last_logout < shift_end:
            early_secs = (shift_end - last_logout).total_seconds()
            record["early_exit_minutes"] = format_break_hours(early_secs)
        else:
            record["early_exit_minutes"] = "0h 0m"
        # record["test"] = "Convert seconds to 'Xh Ym' format cleanly. from frappe.utils import time_diff_in_seconds. Fetch all relevant Checkin Logs in one go."
    
    return attendance_data

def format_break_hours(seconds):
    """ Convert seconds to 'Xh Ym' format cleanly """
    seconds = flt(seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"


# import frappe
# from datetime import timedelta
# from frappe.utils import time_diff_in_seconds, flt, get_datetime

# def format_break_hours(seconds):
#     """ Convert seconds to 'Xh Ym' format """
#     hours = seconds // 3600
#     minutes = (seconds % 3600) // 60
#     return f"{int(hours)}h {int(minutes)}m"

# def execute(filters=None):
#     if not filters:
#         filters = {}

#     html = """
#     <script>
#     document.addEventListener('click', function(event) {
#         var clickedCell = event.target.closest('.dt-cell__content');
#         if (clickedCell) {
#             var previouslyHighlightedCells = document.querySelectorAll('.highlighted-cell');
#             previouslyHighlightedCells.forEach(function(cell) {
#                 cell.classList.remove('highlighted-cell');
#                 cell.style.backgroundColor = '';
#                 cell.style.border = '';
#                 cell.style.fontWeight = '';
#             });
            
#             var clickedRow = event.target.closest('.dt-row');
#             var cellsInClickedRow = clickedRow.querySelectorAll('.dt-cell__content');
#             cellsInClickedRow.forEach(function(cell) {
#                 cell.classList.add('highlighted-cell');
#                 cell.style.backgroundColor = '#d7eaf9';
#                 cell.style.border = '2px solid #90c9e3';
#                 cell.style.fontWeight = 'bold';
#             });
#         }
#     });
#     </script>
#     """

#     columns = get_columns()
#     data = get_data(filters)

#     return columns, data, html

# def get_columns():
#     return [
#         {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
#         {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
#         {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 150},
#         {"label": "Designation", "fieldname": "designation", "fieldtype": "Data", "width": 150},
#         {"label": "Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 120},
#         {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 80},
#         {"label": "First Login", "fieldname": "first_login", "fieldtype": "Time", "width": 100},
#         {"label": "Last Logout", "fieldname": "last_logout", "fieldtype": "Time", "width": 100},
#         {"label": "Total Login Duration", "fieldname": "total_duration", "fieldtype": "Data", "width": 100},
#         {"label": "Total Break Hours", "fieldname": "total_break_hours", "fieldtype": "Data", "width": 100},
#         {"label": "Late Entry", "fieldname": "late_entry", "fieldtype": "Data", "width": 80},
#         {"label": "Late Minutes", "fieldname": "late_minutes", "fieldtype": "Data", "width": 80},
#         {"label": "Early Exit", "fieldname": "early_exit", "fieldtype": "Data", "width": 80},
#         {"label": "Early Exit Minutes", "fieldname": "early_exit_minutes", "fieldtype": "Data", "width": 100}
#     ]

# def get_data(filters):
#     conditions = " WHERE emp.status = 'Active' AND att.docstatus = 1"
#     params = {}

#     if filters.get("date_range") and isinstance(filters["date_range"], (list, tuple)) and len(filters["date_range"]) == 2:
#         start_date, end_date = filters["date_range"]
#         conditions += " AND att.attendance_date BETWEEN %(start_date)s AND %(end_date)s"
#         params.update({"start_date": start_date, "end_date": end_date})

#     if filters.get("employee"):
#         conditions += " AND att.employee = %(employee)s"
#         params["employee"] = filters["employee"]
    
#     if filters.get("status"):
#         conditions += " AND att.status = %(status)s"
#         params["status"] = filters["status"]

#     attendance_query = f"""
#         SELECT 
#             emp.name AS employee,
#             emp.employee_name,
#             emp.department,
#             emp.designation,
#             att.attendance_date,
#             att.status,
#             TIME(att.in_time) AS first_login,
#             TIME(att.out_time) AS last_logout,
#             att.working_hours AS total_duration,
#             att.name AS attendance_id,
#             att.late_entry,
#             att.early_exit,
#             att.shift
#         FROM `tabEmployee` emp
#         JOIN `tabAttendance` att ON att.employee = emp.name
#         {conditions}
#         ORDER BY att.attendance_date DESC
#     """

#     attendance_data = frappe.db.sql(attendance_query, params, as_dict=True)
    
#     if not attendance_data:
#         return []  # No data to process

#     attendance_ids = tuple(d["attendance_id"] for d in attendance_data)
    
#     # Fetch Employee Checkin Logs based on attendance IDs
#     checkin_query = """
#         SELECT 
#             ec.employee, 
#             ec.time, 
#             ec.log_type,
#             ec.attendance
#         FROM `tabEmployee Checkin` ec
#         WHERE ec.attendance IN %(attendance_ids)s
#         ORDER BY ec.employee, ec.time
#     """
    
#     checkin_logs = frappe.db.sql(checkin_query, {"attendance_ids": attendance_ids}, as_dict=True)

#     # Process Check-in Data and Map Break Hours to Attendance ID
#     checkin_map = {}
#     for log in checkin_logs:
#         att_id = log["attendance"]
#         if att_id not in checkin_map:
#             checkin_map[att_id] = []
#         checkin_map[att_id].append(log)

#     # Calculate Break Hours Properly
#     for record in attendance_data:
#         attendance_id = record["attendance_id"]
#         break_seconds = 0

#         if attendance_id in checkin_map:
#             logs = checkin_map[attendance_id]
#             last_out_time = None

#             for log in logs:
#                 if log["log_type"] == "OUT":
#                     last_out_time = log["time"]
#                 elif log["log_type"] == "IN" and last_out_time:
#                     break_seconds += time_diff_in_seconds(log["time"], last_out_time)
#                     last_out_time = None  # Reset after pairing

#         # Format Break Hours as "Xh Ym"
#         record["total_break_hours"] = format_break_hours(break_seconds)

#     for record in attendance_data:
#         shift = frappe.db.get_value("Shift Type", record["shift"], ["start_time", "end_time"], as_dict=True) if record["shift"] else None
#         shift_start_time = get_datetime(shift["start_time"]) if shift and shift.get("start_time") else None
#         shift_end_time = get_datetime(shift["end_time"]) if shift and shift.get("end_time") else None

#         record["late_entry"] = "Yes" if record["late_entry"] == 1 else "No"
#         record["early_exit"] = "Yes" if record["early_exit"] == 1 else "No"
        
#         if record["late_entry"] == "Yes" and record["first_login"] and shift_start_time:
#             first_login = get_datetime(record["first_login"])
#             record["late_minutes"] = format_break_hours(time_diff_in_seconds(first_login, shift_start_time))
#         else:
#             record["late_minutes"] = "0h 0m"

#         if record["early_exit"] == "Yes" and record["last_logout"] and shift_end_time:
#             last_logout = get_datetime(record["last_logout"])
#             record["early_exit_minutes"] = format_break_hours(time_diff_in_seconds(shift_end_time, last_logout))
#         else:
#             record["early_exit_minutes"] = "0h 0m"
    
#     return attendance_data


# import frappe
# from datetime import timedelta
# from frappe.utils import time_diff_in_seconds, flt

# def format_break_hours(seconds):
#     """ Convert seconds to 'Xh Ym' format """
#     hours = seconds // 3600
#     minutes = (seconds % 3600) // 60
#     return f"{int(hours)}h {int(minutes)}m"

# def execute(filters=None):
#     if not filters:
#         filters = {}

#     html = """
#     <script>
#     document.addEventListener('click', function(event) {
#         // Check if the clicked element is a cell
#         var clickedCell = event.target.closest('.dt-cell__content');
#         if (clickedCell) {
#             // Remove highlight from previously highlighted cells
#             var previouslyHighlightedCells = document.querySelectorAll('.highlighted-cell');
#             previouslyHighlightedCells.forEach(function(cell) {
#                 cell.classList.remove('highlighted-cell');
#                 cell.style.backgroundColor = ''; // Remove background color
#                 cell.style.border = ''; // Remove border
#                 cell.style.fontWeight = '';
#             });
            
#             // Highlight the clicked row's cells
#             var clickedRow = event.target.closest('.dt-row');
#             var cellsInClickedRow = clickedRow.querySelectorAll('.dt-cell__content');
#             cellsInClickedRow.forEach(function(cell) {
#                 cell.classList.add('highlighted-cell');
#                 cell.style.backgroundColor = '#d7eaf9'; // Light blue background color
#                 cell.style.border = '2px solid #90c9e3'; // Border color
#                 cell.style.fontWeight = 'bold';
#             });
#         }
#     });
#     </script>
#     """

#     columns = get_columns()
#     data = get_data(filters)

#     return columns, data, html

# def get_columns():
#     return [
#         {"label": "Employee ID", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
#         {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
#         {"label": "Department", "fieldname": "department", "fieldtype": "Data", "width": 150},
#         {"label": "Designation", "fieldname": "designation", "fieldtype": "Data", "width": 150},
#         {"label": "Date", "fieldname": "attendance_date", "fieldtype": "Date", "width": 120},
#         {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 80},
#         {"label": "First Login", "fieldname": "first_login", "fieldtype": "Time", "width": 100},
#         {"label": "Last Logout", "fieldname": "last_logout", "fieldtype": "Time", "width": 100},
#         {"label": "Total Login Duration", "fieldname": "total_duration", "fieldtype": "Data", "width": 100},
#         {"label": "Total Break Hours", "fieldname": "total_break_hours", "fieldtype": "Data", "width": 100}
#     ]

# def get_data(filters):
#     conditions = " WHERE emp.status = 'Active' AND att.docstatus = 1"
#     params = {}

#     # Apply date range filter only if provided
#     if filters.get("date_range") and isinstance(filters["date_range"], (list, tuple)) and len(filters["date_range"]) == 2:
#         start_date, end_date = filters["date_range"]
#         conditions += " AND att.attendance_date BETWEEN %(start_date)s AND %(end_date)s"
#         params.update({"start_date": start_date, "end_date": end_date})

#     if filters.get("employee"):
#         conditions += " AND att.employee = %(employee)s"
#         params["employee"] = filters["employee"]
    
#     if filters.get("status"):
#         conditions += " AND att.status = %(status)s"
#         params["status"] = filters["status"]

#     # Fetch Attendance Data
#     attendance_query = f"""
#         SELECT 
#             emp.name AS employee,
#             emp.employee_name,
#             emp.department,
#             emp.designation,
#             att.attendance_date,
#             att.status,
#             TIME(att.in_time) AS first_login,
#             TIME(att.out_time) AS last_logout,
#             att.working_hours AS total_duration,
#             att.name AS attendance_id
#         FROM `tabEmployee` emp
#         JOIN `tabAttendance` att ON att.employee = emp.name
#         {conditions}
#         ORDER BY att.attendance_date DESC
#     """
    
#     attendance_data = frappe.db.sql(attendance_query, params, as_dict=True)

#     # Ensure employees exist before running check-in query
#     attendance_ids = [d["attendance_id"] for d in attendance_data]
    
    # if not attendance_ids:
    #     return attendance_data  # No data to process

    # # Fetch Employee Checkin Logs based on attendance IDs
    # checkin_query = """
    #     SELECT 
    #         ec.employee, 
    #         ec.time, 
    #         ec.log_type,
    #         ec.attendance
    #     FROM `tabEmployee Checkin` ec
    #     WHERE ec.attendance IN %(attendance_ids)s
    #     ORDER BY ec.employee, ec.time
    # """

#     checkin_logs = frappe.db.sql(checkin_query, {"attendance_ids": tuple(attendance_ids)}, as_dict=True)

#     # Process Check-in Data and Map Break Hours to Attendance ID
#     checkin_map = {}
#     for log in checkin_logs:
#         att_id = log["attendance"]
#         if att_id not in checkin_map:
#             checkin_map[att_id] = []
#         checkin_map[att_id].append(log)

#     # Calculate Break Hours Properly
#     for record in attendance_data:
#         attendance_id = record["attendance_id"]
#         break_seconds = 0

#         if attendance_id in checkin_map:
#             logs = checkin_map[attendance_id]
#             last_out_time = None

#             for log in logs:
#                 if log["log_type"] == "OUT":
#                     last_out_time = log["time"]
#                 elif log["log_type"] == "IN" and last_out_time:
#                     break_seconds += time_diff_in_seconds(log["time"], last_out_time)
#                     last_out_time = None  # Reset after pairing

#         # Format Break Hours as "Xh Ym"
#         record["total_break_hours"] = format_break_hours(break_seconds)

#     return attendance_data



