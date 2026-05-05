import frappe
from frappe import _
from frappe.utils import getdate, date_diff, add_days, format_time, flt, cint
from frappe.utils import today

def execute(filters=None):
    if not filters: filters = {}
    
    filters.from_date = getdate(filters.get("from_date"))
    filters.to_date = getdate(filters.get("to_date"))
    
    columns = get_columns(filters)
    data = get_data(filters)
    
    return columns, data

def get_columns(filters):
    from_date = filters.from_date
    to_date = filters.to_date

    columns = [
        {
            "label": _("Employee Name"),
            "fieldname": "employee",
            "fieldtype": "HTML",
            "options": "Employee",
            "width": 180
        },
    ]

    diff = date_diff(to_date, from_date) + 1

    for i in range(diff):
        curr_date = add_days(from_date, i)
        day_name = curr_date.strftime("%a")
        day_num = curr_date.strftime("%d")

        # Replaced <b> with <span> to stop ** markdown in exports
        columns.append({
            "label": f"<div style='line-height:1.4'>{day_name}<br><span style='color:#3498db; font-weight:bold;'>{day_num}</span></div>",
            "fieldname": f"day_{curr_date.strftime('%Y%m%d')}",
            "fieldtype": "HTML",
            "width": 75
        })

    return columns

def get_data(filters):
    from_date, to_date = filters.from_date, filters.to_date
    
    emp_filters = {"status": "Active"}
    if filters.get("employee"): emp_filters["name"] = filters.get("employee")
    if filters.get("company"): emp_filters["company"] = filters.get("company")
    
    employees = frappe.get_all("Employee", filters=emp_filters, fields=["name", "employee_name", "holiday_list"], limit=0)
    
    attendance = frappe.get_all("Attendance", filters={
        "attendance_date": ["between", [from_date, to_date]],
        "docstatus": ["!=", 2]
    }, fields=["employee", "attendance_date", "status", "leave_type", "late_entry", "early_exit"], limit=0)
    
    checkins = frappe.get_all("Employee Checkin", filters={
        "time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]],
        "skip_auto_attendance": 0
    }, fields=["employee", "time", "log_type"], order_by="time asc", limit=0)

    att_map = {(a.employee, getdate(a.attendance_date)): a for a in attendance}
    
    log_map = {}
    for c in checkins:
        d = getdate(c.time)
        key = (c.employee, d)
        if key not in log_map: log_map[key] = {"in": None, "out": None}
        if c.log_type == "IN" and not log_map[key]["in"]: log_map[key]["in"] = c.time
        if c.log_type == "OUT": log_map[key]["out"] = c.time

    data = []
    diff = date_diff(to_date, from_date) + 1

    for emp in employees:
        row = {
            "employee": f"""
            <a href="/app/employee/{emp.name}" 
            style="font-weight:600; color:#1f2937;">
                {emp.employee_name}
            </a>
            """
        }
        
        today_date = getdate(today())

        for i in range(diff):
            curr_date = add_days(from_date, i)
            day_key = f"day_{curr_date.strftime('%Y%m%d')}"

            if curr_date > today_date:
                row[day_key] = "<div class='attendance-cell'></div>"
                continue
            
            att = att_map.get((emp.name, curr_date))
            logs = log_map.get((emp.name, curr_date))
            
            content = ""
            if att:
                if att.status == "Present":
                    in_t = format_time(logs["in"], "HH:mm") if logs and logs["in"] else "10:00"
                    out_t = format_time(logs["out"], "HH:mm") if logs and logs["out"] else "18:30"
                    
                    in_clr = "#e74c3c" if att.late_entry else "#2c3e50"
                    out_clr = "#e74c3c" if att.early_exit else "#2c3e50"
                    
                    content = f"""
                        <span style='color:{in_clr}; font-weight:600;'>{in_t}</span>
                        <span style='color:{out_clr}; font-weight:600;'>{out_t}</span>
                        """
                
                # Replaced <b> with <span> to stop ** markdown in exports
                elif att.status == "Absent":
                    content = "<span style='color:#c0392b; font-weight:bold;'>A</span>"
                
                elif att.status == "On Duty":
                    content = "<span style='color:#0288d1; font-weight:bold;'>OD</span>"
                
                elif att.status == "Half Day":
                    in_t = format_time(logs["in"], "HH:mm") if logs and logs["in"] else "--:--"
                    content = f"{in_t}<br><span style='color:#f39c12; font-weight:bold;'>HD</span>"
                
                elif att.status in ["Leave", "On Leave"]:
                    l_code = "".join([w[0] for w in att.leave_type.split()]) if att.leave_type else "L"
                    content = f"<span style='color:#2e7d32; font-weight:bold;'>{l_code}</span>"
            else:
                if emp.holiday_list and frappe.db.exists("Holiday", {"parent": emp.holiday_list, "holiday_date": curr_date}):
                    content = "<span style='color:#95a5a6; font-weight:bold; font-size:10px;'>WO-I</span>"

            row[day_key] = f"""
            <div class="attendance-cell">
                {content}
            </div>
            """
            
        data.append(row)
        
    return data

# import frappe
# from frappe import _
# from frappe.utils import getdate, date_diff, add_days, format_time, flt, cint
# from frappe.utils import today

# def execute(filters=None):
#     if not filters: filters = {}
    
#     # Ensure dates are proper objects
#     filters.from_date = getdate(filters.get("from_date"))
#     filters.to_date = getdate(filters.get("to_date"))
    
#     columns = get_columns(filters)
#     data = get_data(filters)
    
#     return columns, data

# def get_columns(filters):

#     from_date = filters.from_date
#     to_date = filters.to_date

#     columns = [
#         {
#             "label": _("Employee Name"),
#             "fieldname": "employee",
#             "fieldtype": "HTML",
#             "options": "Employee",
#             "width": 180
#         },
#     ]

#     diff = date_diff(to_date, from_date) + 1

#     for i in range(diff):
#         curr_date = add_days(from_date, i)

#         day_name = curr_date.strftime("%a")
#         day_num = curr_date.strftime("%d")

#         columns.append({
#             "label": f"<div style='line-height:1.4'>{day_name}<br><b style='color:#3498db'>{day_num}</b></div>",
#             "fieldname": f"day_{curr_date.strftime('%Y%m%d')}",
#             "fieldtype": "HTML",
#             "width": 75
#         })

#     return columns

# def get_data(filters):
#     from_date, to_date = filters.from_date, filters.to_date
    
#     # 1. Fetch ALL Employees
#     emp_filters = {"status": "Active"}
#     if filters.get("employee"): emp_filters["name"] = filters.get("employee")
#     if filters.get("company"): emp_filters["company"] = filters.get("company")
    
#     # limit=0 ensures we get ALL employees
#     employees = frappe.get_all("Employee", filters=emp_filters, fields=["name", "employee_name", "holiday_list"], limit=0)
    
#     # 2. Fetch ALL Attendance records for the range (limit=0 is critical here)
#     attendance = frappe.get_all("Attendance", filters={
#         "attendance_date": ["between", [from_date, to_date]],
#         "docstatus": ["!=", 2]
#     }, fields=["employee", "attendance_date", "status", "leave_type", "late_entry", "early_exit"], limit=0)
    
#     # 3. Fetch ALL Checkins for the range (limit=0 is critical here)
#     checkins = frappe.get_all("Employee Checkin", filters={
#         "time": ["between", [f"{from_date} 00:00:00", f"{to_date} 23:59:59"]],
#         "skip_auto_attendance": 0
#     }, fields=["employee", "time", "log_type"], order_by="time asc", limit=0)

#     # Map data for fast lookup
#     att_map = {(a.employee, getdate(a.attendance_date)): a for a in attendance}
    
#     log_map = {}
#     for c in checkins:
#         d = getdate(c.time)
#         key = (c.employee, d)
#         if key not in log_map: log_map[key] = {"in": None, "out": None}
#         if c.log_type == "IN" and not log_map[key]["in"]: log_map[key]["in"] = c.time
#         if c.log_type == "OUT": log_map[key]["out"] = c.time

#     data = []
#     diff = date_diff(to_date, from_date) + 1

#     for emp in employees:
#         row = {
#             "employee": f"""
#             <a href="/app/employee/{emp.name}" 
#             style="font-weight:600; color:#1f2937;">
#                 {emp.employee_name}
#             </a>
#             """
#         }
        
#         today_date = getdate(today())

#         for i in range(diff):
#             curr_date = add_days(from_date, i)
#             day_key = f"day_{curr_date.strftime('%Y%m%d')}"

#             # ✅ STOP FUTURE DATES
#             if curr_date > today_date:
#                 row[day_key] = "<div class='attendance-cell'></div>"
#                 continue
            
#             att = att_map.get((emp.name, curr_date))
#             logs = log_map.get((emp.name, curr_date))
            
#             content = ""
#             if att:
#                 if att.status == "Present":
#                     # Get Times or Defaults
#                     in_t = format_time(logs["in"], "HH:mm") if logs and logs["in"] else "10:00"
#                     out_t = format_time(logs["out"], "HH:mm") if logs and logs["out"] else "18:30"
                    
#                     # Red color for violation
#                     in_clr = "#e74c3c" if att.late_entry else "#2c3e50"
#                     out_clr = "#e74c3c" if att.early_exit else "#2c3e50"
                    
#                     content = f"""
#                         <span style='color:{in_clr}; font-weight:600;'>{in_t}</span>
#                         <span style='color:{out_clr}; font-weight:600;'>{out_t}</span>
#                         """
                
#                 elif att.status == "Absent":
#                     content = "<b style='color:#c0392b;'>A</b>"
                
#                 elif att.status == "On Duty":
#                     content = "<b style='color:#0288d1;'>OD</b>"
                
#                 elif att.status == "Half Day":
#                     in_t = format_time(logs["in"], "HH:mm") if logs and logs["in"] else "--:--"
#                     content = f"{in_t}<br><b style='color:#f39c12;'>HD</b>"
                
#                 elif att.status in ["Leave", "On Leave"]:
#                     l_code = "".join([w[0] for w in att.leave_type.split()]) if att.leave_type else "L"
#                     content = f"<b style='color:#2e7d32;'>{l_code}</b>"
#             else:
#                 # Weekly Off Check
#                 if emp.holiday_list and frappe.db.exists("Holiday", {"parent": emp.holiday_list, "holiday_date": curr_date}):
#                     content = "<span style='color:#95a5a6; font-weight:bold; font-size:10px;'>WO-I</span>"

#             row[day_key] = f"""
#             <div class="attendance-cell">
#                 {content}
#             </div>
#             """
            
#         data.append(row)
        
#     return data