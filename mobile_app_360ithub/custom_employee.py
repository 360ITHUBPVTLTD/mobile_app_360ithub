import frappe
from frappe.utils import today,add_days, cint, flt, getdate,get_first_day,get_last_day,now_datetime
from datetime import datetime, timedelta, date
from frappe.utils import today, get_time
from datetime import datetime

def before_save_employee(doc, method):
    if not doc.payroll_cost_center:
        frappe.throw(("Payroll Cost Center is required in Employee."))


@frappe.whitelist()
def get_base_salary(employee):
    ctc =  frappe.get_value("Employee", employee, "ctc")
    return ctc/12


def get_employee_for_user():
    current_user = frappe.session.user
    employee = frappe.get_all("Employee", 
        filters={"user_id": current_user, "status": "Active"}, 
        fields=["name", "employee_name"]
    )
    # Return the first employee record found, or None
    return employee[0] if employee else None


@frappe.whitelist()
def get_employees_present_today():
    # Get today's date
    today_date = today()
    
    # Fetch all check-ins and check-outs for today, ordered by time
    checkins = frappe.get_all('Employee Checkin', 
                              filters={'time': ['>=', today_date]},
                              fields=['employee', 'employee_name', 'time', 'log_type'],
                              order_by='time')
    
    # Process the logs to get the first IN, last OUT, and total break hours for each employee
    employee_logs = {}
    for checkin in checkins:
        employee = checkin['employee']
        if employee not in employee_logs:
            employee_logs[employee] = {
                'employee_name': checkin['employee_name'], 
                'first_in': None, 
                'last_out': None,
                'total_break_seconds': 0  # Track break time in seconds for precise calculation
            }

        # Calculate break duration based on previous OUT and current IN
        if employee_logs[employee]['last_out'] and checkin['log_type'] == 'IN':
            out_time = employee_logs[employee]['last_out']
            break_duration_seconds = (checkin['time'] - out_time).total_seconds()
            employee_logs[employee]['total_break_seconds'] += break_duration_seconds

        # Set first IN and OUT
        if checkin['log_type'] == 'IN' and employee_logs[employee]['first_in'] is None:
            employee_logs[employee]['first_in'] = checkin['time']
        
        employee_logs[employee]['last_log'] = checkin['log_type']
        
        if checkin['log_type'] == 'OUT':
            employee_logs[employee]['last_out'] = checkin['time']
    
    # Prepare the final list
    result = []
    for employee, logs in employee_logs.items():
        last_out = logs['last_out'] if logs.get('last_log') == 'OUT' else None
        
        # Convert break time from seconds to hours and minutes (HH:MM)
        total_break_seconds = logs['total_break_seconds']
        break_hours = int(total_break_seconds // 3600)  # Full hours
        break_minutes = int((total_break_seconds % 3600) // 60)  # Remaining minutes
        
        # Format total break hours as HH:MM
        total_break_hours_formatted = f"{break_hours}h {break_minutes}m"

        # 🔥 LATE CALCULATION (MULTI SHIFT SUPPORT)
        late_formatted = "0h 0m"

        if logs['first_in']:

            # 1️⃣ Get shift from Shift Assignment
            shift_type = frappe.db.get_value(
                "Shift Assignment",
                {
                    "employee": employee,
                    "start_date": ["<=", today_date],
                    "end_date": [">=", today_date]
                },
                "shift_type"
            )

            # 2️⃣ Fallback to default shift
            if not shift_type:
                shift_type = frappe.db.get_value("Employee", employee, "default_shift")

            if shift_type:
                shift = frappe.get_doc("Shift Type", shift_type)

                shift_start = get_time(shift.start_time)
                first_in_time = logs['first_in']

                shift_start_dt = datetime.combine(first_in_time.date(), shift_start)

                diff = (first_in_time - shift_start_dt).total_seconds() / 60

                # 🔥 Apply grace period (if enabled)
                grace = shift.late_entry_grace_period or 0

                # if diff > grace:
                #     late_minutes = int(diff - grace)
                late_minutes = int(diff) if diff > 0 else 0

                hours = late_minutes // 60
                minutes = late_minutes % 60

                late_formatted = f"{hours}h {minutes}m"

        result.append({
            'employee': employee,
            'employee_name': logs['employee_name'],
            'first_in': logs['first_in'],
            'last_out': last_out,
            'total_break_hours': total_break_hours_formatted,  # Display in HH:MM format
            'late_minutes': late_formatted 
        })
    # print('resultttttttttttttttttttt',result)
    return result



@frappe.whitelist()
def get_employees_with_birthday_in_current_month():
    current_date = now_datetime().date()
    one_week_before = current_date - timedelta(days=7)
    one_week_after = current_date + timedelta(days=7)

    # Fetch employees with birthdays and custom anniversary dates
    employees = frappe.get_all("Employee",
        filters={
            "status": "Active",
        },
        fields=["name", "employee_name", "date_of_birth", "custom_anniversary_date","date_of_joining"],
    )

    curr_mon = {}
    for emp in employees:
        if emp.date_of_birth:
            dob_this_year = emp.date_of_birth.replace(year=current_date.year)
            if one_week_before <= dob_this_year <= one_week_after:
                date_key = emp.date_of_birth.strftime("%m-%d")
                if date_key in curr_mon:
                    curr_mon[date_key].append((emp.employee_name, "birthday"))
                else:
                    curr_mon[date_key] = [(emp.employee_name, "birthday")]

        if emp.custom_anniversary_date:
            anniv_this_year = emp.custom_anniversary_date.replace(year=current_date.year)
            if one_week_before <= anniv_this_year <= one_week_after:
                date_key = emp.custom_anniversary_date.strftime("%m-%d")
                if date_key in curr_mon:
                    curr_mon[date_key].append((emp.employee_name, "anniversary"))
                else:
                    curr_mon[date_key] = [(emp.employee_name, "anniversary")]
        
        if emp.date_of_joining:
            anniv_this_year = emp.date_of_joining.replace(year=current_date.year)
            if one_week_before <= anniv_this_year <= one_week_after:
                date_key = emp.date_of_joining.strftime("%m-%d")
                if date_key in curr_mon:
                    curr_mon[date_key].append((emp.employee_name, "joining"))
                else:
                    curr_mon[date_key] = [(emp.employee_name, "joining")]

    sorted_curr_mon = {key: curr_mon[key] for key in sorted(curr_mon)}
    return sorted_curr_mon



# @frappe.whitelist()
# def get_employees_with_absent():
#     cur_month = frappe.utils.now_datetime().month
#     # Fetch all employee data
#     usr=frappe.session.user
#     emp_data = frappe.get_all('Employee', filters={"user_id":usr}, fields=['name', 'employee_name','user_id'])
#     reg_req_date={}
#     # Iterate over each employee to check for absences
#     for emp in emp_data:
#         emp_name = emp.name
#         emp_mail = emp.user_id
#         # Fetch attendance regularization requests for the employee
#         attendance_regularization = frappe.get_all(
#             "Team Ticket",
#             filters={
#                 # "employee": emp_name,
#                 "created_by": emp_mail,
        
#             },
#             fields=["regularization_date","name","created_by"]
#         )

        
#         # Check if there are any requests for the employee
#         if attendance_regularization:
#             for request in attendance_regularization:
#                 date_value=(request.regularization_date)
#                 reg_req_date[date_value]= request.name
    
#     # Fetch employees with birthdays in the current month
#     employees = get_employee_for_user()
#     if employees:
#         employees_dict = {}
#         for emp in employees:
#             employees_dict[emp.name] = emp.employee_name       
#         today = date.today()

#         # Calculate the start date of the current month
#         start_date = date(today.year, today.month, 1)

#         # Calculate the end date of the current month
#         if today.month == 12:
#             end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
#         else:
#             end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)

#         leave_applications = frappe.get_all("Leave Application",
#                                              filters={
#                                                       "from_date": ("between", [str(start_date), str(end_date)]),
#                                                       "employee":employees[0].name,
#                                                       },
#                                              fields=["name", "from_date", "to_date", "employee","status"])
#         # Initialize the dictionary
#         leave_dict = {}

#         # Iterate over each leave application
#         for leave in leave_applications:
#             from_date = leave.from_date
#             to_date = leave.to_date
#             employee = leave["employee"]
#             status = leave["status"]
            
#             # Generate key-value pairs for each day in the leave application range
#             current_date = from_date
#             while current_date <= to_date or current_date<=to_date:
#                 leave_dict[(current_date, employee)] = status
#                 current_date += timedelta(days=1)
        
#         absent_date = frappe.get_all("Attendance",
#                                      filters={"docstatus": 1,
#                                               "status": "Absent",
#                                               "employee":employees[0].name,
#                                               "attendance_date": ("between", [str(start_date), str(end_date)]),
#                                               },
#                                      fields=["name", "attendance_date", "employee","working_hours"],
#                                      order_by="attendance_date desc")
#         absent_data = {}
#         for ab_date in absent_date:
#             absent_date_checkin = frappe.get_all("Employee Checkin",
#                                      filters={"attendance": ab_date.name},
#                                      fields=["name", "time", "log_type","custom_automatically_marked_by_system"],
#                                      order_by="time asc")

#             if str(ab_date.attendance_date) not in absent_data:
#                 absent_data[str(ab_date.attendance_date)] = []


#             regularization_exists = None
#             if (ab_date.attendance_date,ab_date.employee) in leave_dict:
                
#                 # if (ab_date.attendance_date) in reg_req_date:
#                 #     regularization_exists=reg_req_date[ab_date.attendance_date]

#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], False, absent_date_checkin,ab_date.working_hours,"Applied for leave but not approved"])
#             elif absent_date_checkin and (len(absent_date_checkin)%2 != 0 or absent_date_checkin[0].log_type == "OUT"):
                
#                 if (ab_date.attendance_date) in reg_req_date:
#                      regularization_exists=reg_req_date[ab_date.attendance_date]
                     
#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], True, absent_date_checkin,ab_date.working_hours,"Mismatch in Checkins",regularization_exists])
#             elif absent_date_checkin :
                
#                 if (ab_date.attendance_date) in reg_req_date:
#                     regularization_exists=reg_req_date[ab_date.attendance_date]
#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], True, absent_date_checkin,ab_date.working_hours,"Short working hours",regularization_exists])
#             else:
               
               
#                 if (ab_date.attendance_date) in reg_req_date:
#                      regularization_exists=reg_req_date[ab_date.attendance_date]

#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], False, absent_date_checkin,ab_date.working_hours,"Need to apply for Leave",regularization_exists])

#         return absent_data
#     return None


# 10 march Anurag

# @frappe.whitelist()
# def get_employees_with_absent():
#     # Fetch data for the logged-in user only
#     usr = frappe.session.user
#     employees = get_employee_for_user()
#     if not employees:
#         return None
    
#     # We get a single employee dict from our helper
#     emp_id = employees.name
#     emp_name = employees.employee_name
    
#     today = date.today()
#     # Calculate the start date of the current month
#     start_date = date(today.year, today.month, 1)
    
#     # Calculate the end date of the current month
#     if today.month == 12:
#         end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
#     else:
#         end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)

#     # Fetch leaves for this specific employee
#     leave_applications = frappe.get_all("Leave Application",
#         filters={
#             "from_date": ("between", [str(start_date), str(end_date)]),
#             "employee": emp_id,
#             "docstatus": ["<", 2]
#         },
#         fields=["from_date", "to_date", "employee", "status"]
#     )
    
#     leave_dict = {}
#     for leave in leave_applications:
#         curr_d = leave.from_date
#         while curr_d <= leave.to_date:
#             leave_dict[(curr_d, leave.employee)] = leave.status
#             curr_d += timedelta(days=1)
    
#     # Fetch Absent Attendance for this employee
#     absent_date = frappe.get_all("Attendance",
#         filters={
#             "docstatus": 1,
#             "status": "Absent",
#             "employee": emp_id,
#             "attendance_date": ("between", [str(start_date), str(end_date)]),
#         },
#         fields=["name", "attendance_date", "employee", "working_hours"],
#         order_by="attendance_date desc"
#     )

#     absent_data = {}
#     for ab in absent_date:
#         # Fetch checkins
#         checkins = frappe.get_all("Employee Checkin",
#             filters={"attendance": ab.name},
#             fields=["name", "time", "log_type"],
#             order_by="time asc"
#         )

#         date_str = str(ab.attendance_date)
#         if date_str not in absent_data:
#             absent_data[date_str] = []

#         remark = "Need to apply for Leave"
#         if (ab.attendance_date, ab.employee) in leave_dict:
#             remark = "Applied for leave but not approved"
#         elif checkins:
#             if len(checkins) % 2 != 0 or checkins[0].log_type == "OUT":
#                 remark = "Mismatch in Checkins"
#             else:
#                 remark = "Short working hours"

#         # Match the format expected by your JS
#         absent_data[date_str].append([
#             emp_name, 
#             True if checkins else False, 
#             checkins, 
#             ab.working_hours, 
#             remark,
#             None # Placeholder for the missing Team Ticket
#         ])

#     return absent_data

@frappe.whitelist()
def get_my_approved_leaves():
    emp = get_employee_for_user()
    if not emp: return []
    
    employee_id = emp.name
    current_date = now_datetime().date()

    leave_applications = frappe.get_all(
        'Leave Application',
        filters={
            'employee': employee_id,
            'status': 'Approved',
            'docstatus': 1,
            'to_date': ['>=', current_date]
        },
        fields=['employee_name', "leave_approver", 'from_date', 'to_date', 'total_leave_days', 'name']
    )
    
    for app in leave_applications:
        if app.leave_approver:
            app["leave_approver_name"] = frappe.db.get_value("Employee", {"user_id": app.leave_approver}, "employee_name")
            
    return leave_applications


# @frappe.whitelist()
# def get_my_pending_leaves():
#     emp = get_employee_for_user() # This is now a dict: {'name': 'EMP/001', ...}
#     if not emp: 
#         return []
    
#     employee_id = emp.name # Correct way to access it now

#     leave_applications = frappe.get_all(
#         'Leave Application',
#         filters={
#             'employee': employee_id,
#             'docstatus': 0,
#             "status": ("not in", ["Cancelled"]),
#         },
#         fields=['employee_name', "leave_approver", 'posting_date', 'from_date', 'to_date', 'total_leave_days', 'name']
#     )
 
#     for app in leave_applications:
#         if app.leave_approver:
#             app["leave_approver_name"] = frappe.db.get_value("Employee", {"user_id": app.leave_approver}, "employee_name") or app.leave_approver
            
#     return leave_applications



@frappe.whitelist()
def get_my_pending_leaves():
    user = frappe.session.user
    # Get employee ID for the logged-in user
    employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    # 1. Main filters (must be Draft/Open)
    filters = {
        'docstatus': 0,
        'status': ('not in', ['Cancelled', 'Rejected']),
    }
    
    # 2. OR filters (I applied OR I need to approve)
    or_filters = [
        ['leave_approver', '=', user]
    ]
    
    if employee_id:
        or_filters.append(['employee', '=', employee_id])

    leave_applications = frappe.get_all(
        'Leave Application',
        filters=filters,
        or_filters=or_filters,
        fields=['name', 'employee', 'employee_name', 'leave_approver', 'posting_date', 'from_date', 'to_date', 'total_leave_days'],
        order_by="creation desc"
    )
 
    for app in leave_applications:
        # Flag for JS to show action button
        app["is_approver"] = (app.leave_approver == user)
        
        if app.leave_approver:
            # Get Full Name of Approver from User table
            app["leave_approver_name"] = frappe.db.get_value("User", app.leave_approver, "full_name") or app.leave_approver
        else:
            app["leave_approver_name"] = "-"
            
    return leave_applications



import frappe
from frappe import _

def validate_leave_approver_on_submit(doc, method=None):
    """
    Restricts submission of Leave Application to the designated leave_approver
    or users with the 'SCHITS Administrator' role.
    """
    # 1. Allow if user has the SCHITS Administrator role
    if "SCHITS Administrator" in frappe.get_roles():
        return

    # 2. If current user is NOT the designated leave approver, throw error
    if doc.leave_approver != frappe.session.user:
        # Fetch full name of the designated approver for a clearer message
        approver_name = frappe.db.get_value("User", doc.leave_approver, "full_name") or doc.leave_approver
        
        frappe.throw(
            _("Only the designated leave approver ({0}) is authorized to submit this application.")
            .format(approver_name)
        )

# @frappe.whitelist()
# def get_my_absents_formatted():
#     # Use your existing absent logic
#     absent_data = get_employees_with_absent()
#     if not absent_data:
#         return {"absent_data": {}, "emp_count": 0}
    
#     # Calculate the count for the header (e.g., the "(1)" in the title)
#     total_count = sum(len(v) for v in absent_data.values())
    
#     return {
#         "absent_data": absent_data,
#         "emp_count": total_count
#     }


# @frappe.whitelist()
# def get_existing_logs(employee, attendance_date):
#     # Fetch ALL biometric/office logs for the whole day
#     logs = frappe.get_all("Employee Checkin", 
#         filters={
#             "employee": employee, 
#             "time": ["between", [attendance_date + " 00:00:00", attendance_date + " 23:59:59"]]
#         },
#         fields=["time", "log_type"],
#         order_by="time asc"
#     )

#     total_seconds = 0
#     last_in_time = None
    
#     html = "<table class='table table-bordered' style='font-size:12px;'><thead><tr style='background:#3498DB;color:white;'><th>System Punch</th><th>Type</th></tr></thead><tbody>"

#     for log in logs:
#         time_str = log.time.strftime("%H:%M:%S")
#         html += f"<tr><td>{time_str}</td><td>{log.log_type}</td></tr>"

#         # Correct Math: Sum every segment between an IN and an OUT
#         if log.log_type == "IN":
#             if not last_in_time:
#                 last_in_time = log.time
#         elif log.log_type == "OUT":
#             if last_in_time:
#                 total_seconds += (log.time - last_in_time).total_seconds()
#                 last_in_time = None # Reset to wait for the next IN

#     html += "</tbody></table>"
    
#     return {
#         "html": html,
#         "office_hours": round(total_seconds / 3600, 2) # Hours already in system
#     }

@frappe.whitelist()
def get_existing_logs(employee, attendance_date):
    # Fetch ALL logs for the day
    logs = frappe.get_all("Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [attendance_date + " 00:00:00", attendance_date + " 23:59:59"]]
        },
        fields=["time", "log_type", "system_generated"],
        order_by="time asc"
    )

    # --- EXPERT STEP: SEPARATE THE LOGS ---
    # Group 1: Original Biometric Punches (system_generated = 0)
    biometric_logs = [l for l in logs if l.system_generated == 0]
    
    # Group 2: Attendance Request Punches (system_generated = 1)
    requested_logs = [l for l in logs if l.system_generated == 1]

    # Header
    html = """
    <table class='table table-bordered' style='font-size:13px; border: 1px solid #d1d8dd;'>
        <thead>
            <tr style='background:#3498DB; color:white;'>
                <th style='width: 75%'>Check-in History</th>
                <th style='width: 25%'>Type</th>
            </tr>
        </thead>
        <tbody>
    """

    # 1. FIRST: Show all Biometric Punches at the top (Struck through)
    if biometric_logs:
        for log in biometric_logs:
            time_str = log.time.strftime("%H:%M:%S")
            row_style = "color: #95a5a6; text-decoration: line-through; background-color: #fcfcfc;"
            html += f"<tr style='{row_style}'><td>{time_str} <small></small></td><td>{log.log_type}</td></tr>"
    else:
        html += "<tr><td colspan='2' style='color:#7f8c8d; font-style:italic; padding:8px;'>No original biometric logs found.</td></tr>"

    # 2. SEPARATOR LINE: Clean separation between History and Request
    html += "<tr><td colspan='2' style='padding:0; border-top: 3px solid #e67e22;'></td></tr>"

    # 3. SECOND: Show all Attendance Request Punches at the bottom (Bold)
    if requested_logs:
        for log in requested_logs:
            time_str = log.time.strftime("%H:%M:%S")
            row_style = "font-weight: bold; background-color: #fff9f0;"
            label = " <span style='color:#e67e22; font-size:11px;'>(Attendance Request)</span>"
            html += f"<tr style='{row_style}'><td>{time_str}{label}</td><td>{log.log_type}</td></tr>"
    else:
        html += "<tr><td colspan='2' style='color:#e67e22; font-weight:bold; padding:8px;'>New Request Punches Pending...</td></tr>"

    html += "</tbody></table>"

    # Logic for Total Hours (Calculated based on the FINAL requested sequence)
    # We only use requested_logs for the final hour calculation if they exist
    calc_logs = requested_logs if requested_logs else biometric_logs
    total_seconds = 0
    last_in_time = None
    for log in calc_logs:
        if log["log_type"] == "IN":
            if not last_in_time: last_in_time = log["time"]
        elif log["log_type"] == "OUT":
            if last_in_time:
                total_seconds += (log["time"] - last_in_time).total_seconds()
                last_in_time = None

    return {
        "html": html,
        "office_hours": round(total_seconds / 3600, 2)
    }
# @frappe.whitelist()
# def get_existing_logs(employee, attendance_date):
#     logs = frappe.get_all("Employee Checkin",
#         filters={
#             "employee": employee,
#             "time": ["between", [attendance_date + " 00:00:00", attendance_date + " 23:59:59"]]
#         },
#         fields=["time", "log_type", "system_generated", "device_id"],
#         order_by="time asc"
#     )

#     total_seconds = 0
#     last_in_time = None

#     html = "<table class='table table-bordered' style='font-size:12px;'><thead><tr style='background:#3498DB;color:white;'><th>System Punch</th><th>Type</th></tr></thead><tbody>"

#     has_separator_shown = False
    
#     for log in logs:
#         # Identify if it is a requested log
#         # Usually identified by system_generated=1 or containing the ARQ name
#         is_requested = log.system_generated == 1 or "ARQ" in str(log.device_id)

#         # Draw the separator line before the first requested log
#         if is_requested and not has_separator_shown:
#             html += "<tr><td colspan='2' style='padding:0; border-top: 3px solid #f39c12;'></td></tr>"
#             has_separator_shown = True

#         time_str = log.time.strftime("%H:%M:%S")
#         label = " <span style='color:#d35400; font-weight:bold;'>(Attendance Request)</span>" if is_requested else ""
        
#         row_style = "background-color: #fdf2e9;" if is_requested else ""

#         html += f"<tr style='{row_style}'><td>{time_str}{label}</td><td>{log.log_type}</td></tr>"

#         # Correct Math Logic
#         if log.log_type == "IN":
#             if not last_in_time:
#                 last_in_time = log.time
#         elif log.log_type == "OUT":
#             if last_in_time:
#                 total_seconds += (log.time - last_in_time).total_seconds()
#                 last_in_time = None

#     html += "</tbody></table>"

#     return {
#         "html": html,
#         "office_hours": round(total_seconds / 3600, 2)
#     }
@frappe.whitelist()
def get_shift_thresholds(shift_type_name):
    # Fetch thresholds from the Shift Type document
    return frappe.db.get_value("Shift Type", shift_type_name, 
        ["working_hours_threshold_for_half_day", "working_hours_threshold_for_absent"], 
        as_dict=True
    )


# @frappe.whitelist()
# def get_my_absents_formatted(from_date=None, to_date=None, sort_order="desc"):
#     # 1. Date Handling
#     if not from_date or not to_date:
#         # Default to last 30 days if no filter
#         to_date = today()
#         from_date = add_days(to_date, -30)

#     # 2. Get the logged-in user's employee
#     employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "default_shift"], as_dict=True)
#     if not employee:
#         return {"data": [], "count": 0}

#     # 3. Fetch Absences
#     absents = frappe.get_all("Attendance",
#         filters={
#             "employee": employee.name,
#             "status": "Absent",
#             "docstatus": 1,
#             "attendance_date": ["between", [from_date, to_date]]
#         },
#         fields=["name", "attendance_date", "employee_name", "working_hours"],
#         order_by=f"attendance_date {sort_order}"
#     )

#     result_list = []
#     for ab in absents:
#         # 4. Fetch Logs
#         logs = frappe.get_all("Employee Checkin",
#             filters={"attendance": ab.name},
#             fields=["time", "log_type"],
#             order_by="time asc"
#         )
        
#         # 5. Check for Open Documents (Drafts)
#         open_leave = frappe.db.get_value("Leave Application", 
#             {"employee": employee.name, "docstatus": 0, "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, "name")
        
#         open_arq = frappe.db.get_value("Attendance Request", 
#             {"employee": employee.name, "docstatus": 0, "from_date": ab.attendance_date}, "name")

#         # 6. Refined Remarks Logic
#         remark = "No Leave applications or checkin mismatch"
#         if not logs:
#             remark = "No Checkins found"
#         elif len(logs) % 2 != 0 or logs[0].log_type == "OUT":
#             remark = "Checkin Mismatch (Missing IN or OUT)"
#         elif ab.working_hours and ab.working_hours < 4: # Example threshold
#             remark = "Short working hours"

#         result_list.append({
#             "date": ab.attendance_date,
#             "employee": employee.name,
#             "employee_name": ab.employee_name,
#             "shift": employee.default_shift,
#             "logs": logs,
#             "hours": ab.working_hours or 0,
#             "remark": remark,
#             "open_leave": open_leave,
#             "open_arq": open_arq
#         })

#     return {
#         "data": result_list,
#         "count": len(result_list),
#         "from_date": from_date,
#         "to_date": to_date
#     }


# @frappe.whitelist()
# def get_my_absents_formatted(from_date=None, to_date=None, sort_order="desc"):
#     # 1. Improved Date Handling
#     # Handle cases where dates might be empty strings or None
#     if not from_date or not to_date or from_date == "" or to_date == "":
#         to_date = frappe.utils.today()
#         from_date = frappe.utils.add_days(to_date, -30)

#     # 2. Get the logged-in user's employee
#     employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, ["name", "default_shift"], as_dict=True)
#     if not employee:
#         return {"data": [], "count": 0, "from_date": from_date, "to_date": to_date}

#     # 3. Fetch Absences
#     absents = frappe.get_all("Attendance",
#         filters={
#             "employee": employee.name,
#             "status": "Absent",
#             "docstatus": 1,
#             "attendance_date": ["between", [from_date, to_date]]
#         },
#         fields=["name", "attendance_date", "employee_name", "working_hours"],
#         order_by=f"attendance_date {sort_order}"
#     )

#     result_list = []
#     for ab in absents:
#         # 4. Fetch Logs
#         logs = frappe.get_all("Employee Checkin",
#             filters={"attendance": ab.name},
#             fields=["time", "log_type"],
#             order_by="time asc"
#         )
        
#         # 5. Check for Open Documents (Drafts)
#         # We fetch the first match found
#         open_leave = frappe.db.get_value("Leave Application", 
#             {"employee": employee.name, "docstatus": 0, "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, "name")
        
#         open_arq = frappe.db.get_value("Attendance Request", 
#             {"employee": employee.name, "docstatus": 0, "from_date": ab.attendance_date}, "name")

#         # 6. Refined Remarks Logic
#         remark = "No Leave applications found"
#         if not logs:
#             remark = "No Checkins found"
#         elif len(logs) % 2 != 0 or logs[0].log_type == "OUT":
#             remark = "Checkin Mismatch (Missing IN or OUT)"
#         elif ab.working_hours and ab.working_hours < 4: 
#             remark = "Short working hours"

#         result_list.append({
#             "date": ab.attendance_date,
#             "employee": employee.name,
#             "employee_name": ab.employee_name,
#             "shift": employee.default_shift,
#             "logs": logs,
#             "hours": ab.working_hours or 0,
#             "remark": remark,
#             "open_leave": open_leave,
#             "open_arq": open_arq
#         })

#     # Return the dates used so the JS can sync the Heading
#     return {
#         "data": result_list,
#         "count": len(result_list),
#         "from_date": from_date,
#         "to_date": to_date
#     }


# 12 march anurag


# from datetime import timedelta
# @frappe.whitelist()
# def get_my_absents_formatted(from_date=None, to_date=None, sort_order="desc"):
#     # 1. Get the current logged-in employee
#     emp_doc = get_employee_for_user()
#     if not emp_doc:
#         return {"data": [], "count": 0, "from_date": from_date, "to_date": to_date}

#     # 2. Call the master logic (get_employees_with_absent) filtered only for THIS employee
#     # This prevents the TypeError you saw earlier
#     return get_employees_with_absent(
#         from_date=from_date, 
#         to_date=to_date, 
#         employee=emp_doc.name, 
#         sort_order=sort_order
#     )

# @frappe.whitelist()
# def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
#     if not from_date or not to_date:
#         to_date = frappe.utils.today()
#         from_date = str(frappe.utils.add_days(to_date, -30))

#     filters = {
#         "status": ["in", ["Absent", "Half Day"]],
#         "docstatus": 1,
#         "attendance_date": ["between", [from_date, to_date]]
#     }
    
#     if employee and employee != "" and employee != "undefined":
#         filters["employee"] = employee

#     absents = frappe.get_all("Attendance",
#         filters=filters,
#         fields=["name", "attendance_date", "employee", "employee_name", "working_hours", "status"],
#         order_by=f"attendance_date {sort_order}"
#     )

#     result_list = []
#     for ab in absents:
#         start_dt = f"{ab.attendance_date} 00:00:00"
#         end_dt = f"{ab.attendance_date} 23:59:59"

#         # FETCH LOGS: We specifically include 'system_generated' from your JSON
#         logs = frappe.get_all(
#             "Employee Checkin",
#             filters={
#                 "employee": ab.employee,
#                 "time": ["between", [start_dt, end_dt]]
#             },
#             fields=["time", "log_type", "system_generated"],
#             order_by="time asc"
#         )

#         # --------- FIX: Simulate System Generated OUT ----------
#         if logs and len(logs) % 2 != 0 and not logs[-1].get("system_generated"):
#             last_log = logs[-1]

#             if last_log["log_type"] == "IN":
#                 sys_out_time = last_log["time"] + timedelta(minutes=1)

#                 logs.append({
#                     "time": sys_out_time,
#                     "log_type": "OUT",
#                     "system_generated": 1
#                 })
#         # -------------------------------------------------------


#         # Manual Hours Calculation
#         total_seconds = 0
#         last_in = None

#         for log in logs:
#             if log["log_type"] == "IN" and not last_in:
#                 last_in = log["time"]

#             elif log["log_type"] == "OUT" and last_in:
#                 total_seconds += (log["time"] - last_in).total_seconds()
#                 last_in = None

#         calc_hours = round(total_seconds / 3600, 2)
#         if logs:
#             display_hours = calc_hours
#         else:
#             display_hours = ab.working_hours or 0

#         shift = frappe.db.get_value("Employee", ab.employee, "default_shift")

#         open_leave = frappe.db.get_value(
#             "Leave Application",
#             {
#                 "employee": ab.employee,
#                 "docstatus": 0,
#                 "from_date": ["<=", ab.attendance_date],
#                 "to_date": [">=", ab.attendance_date]
#             },
#             "name"
#         )

#         open_arq = frappe.db.get_value(
#             "Attendance Request",
#             {
#                 "employee": ab.employee,
#                 "docstatus": 0,
#                 "from_date": ab.attendance_date
#             },
#             "name"
#         )

#         # Refined Remarks
#         remark = f"Resolve required ({ab.status})"

#         if not logs and ab.status == "Half Day":
#             remark = "Half Day marked, but no checkins found – Apply Leave or Attendance Request"

#         elif not logs:
#             remark = "No Checkins found"

#         elif logs and logs[-1].get("system_generated"):
#             remark = "System generated checkout"

#         elif ab.status == "Half Day":
#             remark = "Half day – Apply Leave or Attendance Request"

#         elif display_hours < 4:
#             remark = "Short working hours"

#         result_list.append({
#             "date": ab.attendance_date,
#             "employee": ab.employee,
#             "employee_name": ab.employee_name,
#             "shift": shift or "",
#             "logs": logs,
#             "hours": display_hours,
#             "remark": remark,
#             "open_leave": open_leave,
#             "open_arq": open_arq
#         })

#     return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}


# from datetime import timedelta

# @frappe.whitelist()
# def get_my_absents_formatted(from_date=None, to_date=None, sort_order="desc"):
#     # Find the employee linked to the currently logged-in user
#     emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    
#     if not emp:
#         return {"data":[], "count": 0, "from_date": from_date, "to_date": to_date}

#     # Call the master logic filtered only for THIS employee
#     return get_employees_with_absent(
#         from_date=from_date, 
#         to_date=to_date, 
#         employee=emp, 
#         sort_order=sort_order
#     )

# Hours was not calculating correct 13 march 6:30 pm commented
# @frappe.whitelist()
# def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
#     if not from_date or not to_date:
#         to_date = frappe.utils.today()
#         from_date = str(frappe.utils.add_days(to_date, -30))

#     filters = {
#         "status":["in", ["Absent", "Half Day"]],
#         "docstatus": 1,
#         "attendance_date": ["between", [from_date, to_date]]
#     }
    
#     if employee and employee not in ["", "undefined"]:
#         filters["employee"] = employee

#     absents = frappe.get_all("Attendance",
#         filters=filters,
#         fields=["name", "attendance_date", "employee", "employee_name", 
#                 "working_hours", "status", "shift"],
#         order_by=f"attendance_date {sort_order}"
#     )

#     result_list =[]
#     HALF_DAY_THRESHOLD = 4.0 

#     for ab in absents:
#         start_dt = f"{ab.attendance_date} 00:00:00"
#         end_dt = f"{ab.attendance_date} 23:59:59"

#         logs = frappe.get_all("Employee Checkin", 
#             filters={"employee": ab.employee, "time":["between", [start_dt, end_dt]]}, 
#             fields=["time", "log_type", "system_generated"], 
#             order_by="time asc"
#         )

#         if logs and len(logs) % 2 != 0 and not logs[-1].get("system_generated"):
#             last_log = logs[-1]
#             if last_log["log_type"] == "IN":
#                 logs.append({
#                     "time": last_log["time"] + timedelta(minutes=1),
#                     "log_type": "OUT",
#                     "system_generated": 1
#                 })

#         total_seconds = 0
#         last_in = None
#         for log in logs:
#             if log["log_type"] == "IN" and not last_in:
#                 last_in = log["time"]
#             elif log["log_type"] == "OUT" and last_in:
#                 total_seconds += (log["time"] - last_in).total_seconds()
#                 last_in = None
        
#         calc_hours = round(total_seconds / 3600, 2)
#         display_hours = ab.working_hours if ab.working_hours > 0 else calc_hours
#         shift = ab.shift or frappe.db.get_value("Employee", ab.employee, "default_shift")

#         # --- FETCH ACTUAL STATUS OF DOCUMENTS ---
#         leave_info = frappe.db.get_value("Leave Application", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date":["<=", ab.attendance_date], "to_date":[">=", ab.attendance_date]},["name", "status", "docstatus"], as_dict=True)
            
#         arq_info = frappe.db.get_value("Attendance Request", 
#             {"employee": ab.employee, "docstatus":["<", 2], "from_date": ab.attendance_date},["name", "docstatus"], as_dict=True)

#         has_leave = bool(leave_info)
#         leave_approved = bool(has_leave and leave_info.get("status") == "Approved")
#         leave_status = leave_info.get("status") if has_leave else ""
        
#         has_arq = bool(arq_info)
#         arq_approved = bool(has_arq and arq_info.get("docstatus") == 1)
#         arq_status = "Submitted" if arq_approved else ("Draft" if has_arq else "")

#         requires_action = True
#         remark = "Resolve required"

#         # --- THE STRICT RESOLUTION LOGIC ---
#         if ab.status == "Half Day":
#             if display_hours >= HALF_DAY_THRESHOLD:
#                 if leave_approved or arq_approved:
#                     requires_action = False # It is APPROVED! (Hides from list)
#                 elif has_leave:
#                     requires_action = True
#                     remark = f"Leave is {leave_status} - Waiting for Approval"
#                 elif has_arq:
#                     requires_action = True
#                     remark = f"ARQ is {arq_status} - Waiting for Approval"
#                 else:
#                     requires_action = True
#                     remark = "Threshold met - Apply Leave/ARQ for remaining half"
#             else:
#                 requires_action = True
#                 if has_leave:
#                     remark = f"Short Hours ({display_hours}h) - Leave is {leave_status} but threshold not met"
#                 elif has_arq:
#                     remark = f"Short Hours ({display_hours}h) - ARQ is {arq_status} but threshold not met"
#                 else:
#                     remark = f"Short Hours ({display_hours}h) - Needs Regularization"

#         elif ab.status == "Absent":
#             if leave_approved or arq_approved:
#                 requires_action = False # Approved! (Hides from list)
#             elif has_leave:
#                 requires_action = True
#                 remark = f"Leave is {leave_status} - Waiting for Approval"
#             elif has_arq:
#                 requires_action = True
#                 remark = f"ARQ is {arq_status} - Waiting for Approval"
#             else:
#                 requires_action = True
#                 remark = "Absent - Needs Regularization"
                
#         if requires_action and logs and logs[-1].get("system_generated"):
#             remark += " (System generated checkout)"

#         if requires_action:
#             result_list.append({
#                 "date": ab.attendance_date,
#                 "employee": ab.employee,
#                 "employee_name": ab.employee_name,
#                 "shift": shift or "",
#                 "logs": logs,
#                 "hours": display_hours,
#                 "remark": remark,
#                 "leave_name": leave_info.get("name") if has_leave else None,
#                 "leave_status": leave_status,
#                 "arq_name": arq_info.get("name") if has_arq else None,
#                 "arq_status": arq_status,
#                 "requires_action": requires_action
#             })

#     return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}

# this commenting on 14 march 1:23 pm

# @frappe.whitelist()
# def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
#     if not from_date or not to_date:
#         to_date = frappe.utils.today()
#         from_date = str(frappe.utils.add_days(to_date, -30))

#     filters = {
#         "status": ["in", ["Absent", "Half Day"]],
#         "docstatus": 1,
#         "attendance_date": ["between", [from_date, to_date]]
#     }
    
#     if employee and employee not in ["", "undefined"]:
#         filters["employee"] = employee

#     absents = frappe.get_all("Attendance",
#         filters=filters,
#         fields=["name", "attendance_date", "employee", "employee_name", 
#                 "working_hours", "status", "shift"],
#         order_by=f"attendance_date {sort_order}"
#     )

#     result_list = []
#     HALF_DAY_THRESHOLD = 4.0 

#     for ab in absents:
#         start_dt = f"{ab.attendance_date} 00:00:00"
#         end_dt = f"{ab.attendance_date} 23:59:59"

#         logs = frappe.get_all("Employee Checkin", 
#             filters={"employee": ab.employee, "time": ["between", [start_dt, end_dt]]}, 
#             fields=["time", "log_type", "system_generated"], 
#             order_by="time asc"
#         )

#         # Auto-fill missing checkout for calculation
#         temp_logs = list(logs)
#         if temp_logs and len(temp_logs) % 2 != 0:
#             last_log = temp_logs[-1]
#             if last_log["log_type"] == "IN":
#                 temp_logs.append({"time": last_log["time"] + timedelta(minutes=1), "log_type": "OUT"})

#         # Calculate Hours Fresh from Logs
#         total_seconds = 0
#         last_in = None
#         for log in temp_logs:
#             if log["log_type"] == "IN" and not last_in:
#                 last_in = log["time"]
#             elif log["log_type"] == "OUT" and last_in:
#                 total_seconds += (log["time"] - last_in).total_seconds()
#                 last_in = None
        
#         # FIX 1: Always use calculated hours for the dashboard display
#         display_hours = round(total_seconds / 3600, 2)
#         shift = ab.shift or frappe.db.get_value("Employee", ab.employee, "default_shift")

#         # Fetch Documents
#         leave_info = frappe.db.get_value("Leave Application", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, 
#             ["name", "status", "docstatus"], as_dict=True)
            
#         arq_info = frappe.db.get_value("Attendance Request", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date": ab.attendance_date}, 
#             ["name", "docstatus"], as_dict=True)

#         has_leave = bool(leave_info)
#         leave_approved = bool(has_leave and leave_info.get("status") == "Approved")
#         leave_status = leave_info.get("status") if has_leave else ""
        
#         has_arq = bool(arq_info)
#         arq_approved = bool(has_arq and arq_info.get("docstatus") == 1)
#         arq_status = "Submitted" if arq_approved else ("Draft" if has_arq else "")

#         # --- FIX 2: IMPROVED LOGIC ---
#         requires_action = True
#         remark = ""

#         # RULE A: If HR has already approved a document, it is RESOLVED. Remove from list.
#         if leave_approved or arq_approved:
#             requires_action = False 

#         # RULE B: Document exists but is not yet approved (Waiting)
#         elif has_leave:
#             remark = f"Leave is {leave_status} - Waiting for Approval"
#         elif has_arq:
#             remark = f"ARQ is {arq_status} - Waiting for Approval"

#         # RULE C: No document exists, determine what is needed
#         else:
#             if ab.status == "Half Day":
#                 if display_hours >= HALF_DAY_THRESHOLD:
#                     remark = "Threshold met - Apply Leave/ARQ for remaining half"
#                 else:
#                     remark = f"Short Hours ({display_hours}h) - Needs Regularization"
#             else:
#                 remark = "Absent - Needs Regularization"

#         # Additional hint for system checkouts
#         if requires_action and logs and logs[-1].get("system_generated"):
#             remark += " (System generated checkout)"

#         if requires_action:
#             result_list.append({
#                 "date": ab.attendance_date,
#                 "employee": ab.employee,
#                 "employee_name": ab.employee_name,
#                 "shift": shift or "",
#                 "logs": logs,
#                 "hours": display_hours,
#                 "remark": remark,
#                 "leave_name": leave_info.get("name") if has_leave else None,
#                 "leave_status": leave_status,
#                 "arq_name": arq_info.get("name") if has_arq else None,
#                 "arq_status": arq_status
#             })

#     return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}

import frappe

from datetime import timedelta
from frappe.utils import getdate, add_days, date_diff, today
from hrms.hr.utils import get_holiday_dates_for_employee

@frappe.whitelist()
def get_my_absents_formatted(from_date=None, to_date=None, sort_order="desc"):
    """Entry point for the Employee Dashboard"""
    user = frappe.session.user
    # user = "venkatesh@shanthalachits.com"
    # Find the employee linked to the currently logged-in user
    emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    if not emp:
        return {"data":[], "count": 0, "from_date": from_date, "to_date": to_date}

    # Call the master logic filtered only for THIS employee
    return get_employees_with_absent(
        from_date=from_date, 
        to_date=to_date, 
        employee=emp, 
        sort_order=sort_order
    )



@frappe.whitelist()
def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
    if not from_date or not to_date or from_date == "undefined":
        to_date = today()
        from_date = str(add_days(to_date, -30))

    if not employee or employee in ["", "undefined", "null"]:
        return {"data": [], "count": 0}

    yesterday = add_days(today(), -1)
    # We shouldn't ask employees to regularize future dates
    end_date = min(getdate(to_date), getdate(yesterday))
    start_date = getdate(from_date)

    # 1. Fetch Holidays & Weekends for this employee
    holiday_dates = get_holiday_dates_for_employee(employee, start_date, end_date)
    holiday_dates_str = [str(d) for d in holiday_dates]

    # Fetch Employee Details once
    emp_details = frappe.db.get_value("Employee", employee, ["employee_name", "default_shift"], as_dict=True)
    employee_name = emp_details.employee_name if emp_details else ""
    shift = emp_details.default_shift if emp_details else ""

    calc_rule = "Every Valid Check-in and Check-out" # Default fallback
    if shift:
        fetched_rule = frappe.db.get_value("Shift Type", shift, "working_hours_calculation_based_on")
        if fetched_rule:
            calc_rule = fetched_rule

    result_list = []
    HALF_DAY_THRESHOLD = 4.0 

    # 2. THE FIX: Iterate over CALENDAR DAYS, not database records
    total_days = date_diff(end_date, start_date) + 1
    
    for i in range(total_days):
        current_date = add_days(start_date, i)
        date_str = str(current_date)

        # 3. Check for existing Attendance
        # Notice we ignore Cancelled (docstatus 2) records. They are ghosts to us.
        att = frappe.db.get_value("Attendance", 
            {"employee": employee, "attendance_date": date_str, "docstatus": ["<", 2]}, 
            ["name", "status", "docstatus"], as_dict=True)

        # --- HIDE PERFECT DAYS ---
        if att and att.status in ["Present", "On Leave", "Work From Home"] and att.docstatus == 1:
            continue

        # --- HIDE GHOST HOLIDAYS ---
        # If no attendance exists, and it's a holiday, skip it. They don't need to regularize Sunday.
        if not att and date_str in holiday_dates_str:
            continue

        # If we reach here, it's a day that REQUIRES attention!
        # It is either Absent, Half Day, or Completely Missing (Ghost Day)
        current_status = att.status if att else "Missing Record"

        start_dt = f"{date_str} 00:00:00"
        end_dt = f"{date_str} 23:59:59"

        logs = frappe.get_all("Employee Checkin", 
            filters={"employee": employee, "time": ["between", [start_dt, end_dt]],"skip_auto_attendance":0,"system_generated":0}, 
            fields=["time", "log_type", "system_generated"], order_by="time asc")

        temp_logs = list(logs)
        if temp_logs and len(temp_logs) % 2 != 0:
            if temp_logs[-1]["log_type"] == "IN":
                temp_logs.append({"time": temp_logs[-1]["time"] + timedelta(minutes=1), "log_type": "OUT"})

        total_seconds = 0
        display_hours = 0
        if temp_logs:
            if calc_rule == "First Check-in and Last Check-out":
                # Fetch absolute first IN and absolute last OUT
                first_in = next((l["time"] for l in temp_logs if l["log_type"] == "IN"), None)
                last_out = next((l["time"] for l in reversed(temp_logs) if l["log_type"] == "OUT"), None)
                
                if first_in and last_out and last_out > first_in:
                    total_seconds = (last_out - first_in).total_seconds()
            else:
                # "Every Valid Check-in and Check-out" logic
                last_in = None
                for log in temp_logs:
                    if log["log_type"] == "IN" and not last_in: 
                        last_in = log["time"]
                    elif log["log_type"] == "OUT" and last_in:
                        total_seconds += (log["time"] - last_in).total_seconds()
                        last_in = None

        # Trust Frappe's official record first, fallback to raw log math if Missing/Ghost day
        if att and att.get("working_hours"):
            display_hours = frappe.utils.flt(att.working_hours)
        else:
            display_hours = round(total_seconds / 3600, 2)
            
        # total_seconds = 0
        # display_hours = 0
        # last_in = None
        # for log in temp_logs:
        #     if log["log_type"] == "IN" and not last_in: last_in = log["time"]
        #     elif log["log_type"] == "OUT" and last_in:
        #         total_seconds += (log["time"] - last_in).total_seconds()
        #         last_in = None
        # if att and att.get("working_hours"):
        #     display_hours = frappe.utils.flt(att.working_hours)
        # else:
        #     display_hours = round(total_seconds / 3600, 2)

        # --- FETCH DOCUMENTS ---
        all_leaves = frappe.get_all("Leave Application", 
            filters={"employee": employee, "docstatus": ["<", 2], "from_date": ["<=", date_str], "to_date": [">=", date_str]}, 
            fields=["name", "status", "half_day"])
            
        arq_info = frappe.db.get_value("Attendance Request", 
            {"employee": employee, "docstatus": ["<", 2], "from_date": date_str}, 
            ["name", "docstatus", "half_day", "custom_status"], as_dict=True)

        has_leave = len(all_leaves) > 0
        has_arq = bool(arq_info)

        leave_is_approved = has_leave and all(l.status == "Approved" for l in all_leaves)
        leave_is_draft = has_leave and any(l.status in ["Draft", "Open"] for l in all_leaves)
        is_full_day_leave = has_leave and (any(not l.half_day for l in all_leaves) or len(all_leaves) >= 2)
        
        arq_is_rejected = has_arq and arq_info.get("custom_status") == "Rejected"
        arq_is_submitted = has_arq and arq_info.get("docstatus") == 1 and not arq_is_rejected

        is_full_day_doc = is_full_day_leave or (has_arq and not arq_info.get("half_day") and not arq_is_rejected)

        # --- RESOLUTION LOGIC ---
        day_value = 0.0
        
        # 1. Add Leave Value
        if has_leave and leave_is_approved:
            day_value += 1.0 if is_full_day_leave else 0.5
            
        # 2. Add ARQ Value
        if has_arq and arq_is_submitted:
            day_value += 1.0 if not arq_info.get("half_day") else 0.5
            
        # 3. Add Worked Hours Value
        if display_hours >= HALF_DAY_THRESHOLD:
            day_value += 0.5

        # Draft/Rejected states always require action
        is_any_draft = leave_is_draft or (has_arq and arq_info.docstatus == 0)
        
        # VERDICT: If the day doesn't add up to 1.0, or there are drafts/rejections, show it!
        requires_action = is_any_draft or arq_is_rejected or day_value < 1.0

        if requires_action:
            l_status = ""
            if has_leave:
                l_status = "Leave Approved" if leave_is_approved else ("Leave in Draft" if leave_is_draft else "Leave Awaiting Approval")
            
            a_status = ""
            if has_arq:
                if arq_is_rejected:
                    a_status = "On-Duty Req Rejected"
                elif arq_is_submitted:
                    a_status = "On-Duty Req Approved"
                elif arq_info.docstatus == 0:
                    a_status = "On-Duty Req in Draft"
                else:
                    a_status = "On-Duty Req Awaiting Approval"

            # --- REMARK & SUFFIX LOGIC ---
            combined = " & ".join(filter(None, [l_status, a_status]))
            
            if not combined:
                if not att:
                    if display_hours:
                        remark = f"Missing Attendance Record ({display_hours}h): Regularization Required"
                    else:
                        remark = "Absent (No Checkins): Regularization Required"
                elif att.status == "Absent":
                    if display_hours == 0:
                        remark = "Absent (No Checkins): Regularization Required"
                    else:
                        remark = f"Absent (Short Attendance: {display_hours}h): Regularization Required"
                elif att.status == "Half Day":
                    remark = f"Half Day Marked ({display_hours}h): Apply Leave for remaining Half Day \nor Apply Full day On-Duty Req"
            else:
                suffix = ""
                if arq_is_rejected:
                    suffix = " (Action needed)"
                elif day_value < 1.0 and not is_any_draft:
                    # If it's mathematically incomplete and no drafts are pending, tell them to apply
                    suffix = " (Remaining half pending)"
                
                remark = f"{combined}{suffix}"
        # requires_action = True
        # is_any_draft = leave_is_draft or (has_arq and arq_info.docstatus == 0)

        # if is_any_draft or arq_is_rejected:
        #     requires_action = True 
        # elif is_full_day_doc and (leave_is_approved or arq_is_submitted):
        #     requires_action = False 
        # elif display_hours >= HALF_DAY_THRESHOLD and ((has_leave and leave_is_approved) or arq_is_submitted):
        #     requires_action = False
        # elif (has_leave and leave_is_approved) and arq_is_submitted:
        #     requires_action = False

        # if requires_action:
        #     l_status = ""
        #     if has_leave:
        #         l_status = "Leave Approved" if leave_is_approved else ("Leave in Draft" if leave_is_draft else "Leave Awaiting Approval")
            
        #     a_status = ""
        #     if has_arq:
        #         if arq_is_rejected:
        #             a_status = "On-Duty Req Rejected"
        #         elif arq_is_submitted:
        #             a_status = "On-Duty Req Approved"
        #         elif arq_info.docstatus == 0:
        #             a_status = "On-Duty Req in Draft"
        #         else:
        #             a_status = "On-Duty Req Awaiting Approval"

        #     # --- REMARK & SUFFIX LOGIC ---
        #     combined = " & ".join(filter(None, [l_status, a_status]))
            
        #     if not combined:
        #         if not att:
        #             if display_hours:
        #                 remark = f"Missing Attendance Record ({display_hours}h): Regularization Required"
        #             else:
        #                 remark = "Absent (No Checkins): Regularization Required"
        #         elif att.status == "Absent":
        #             if display_hours == 0:
        #                 remark = "Absent (No Checkins): Regularization Required"
        #             else:
        #                 remark = f"Absent (Short Attendance: {display_hours}h): Regularization Required"
        #         elif att.status == "Half Day":
        #             remark = f"Half Day Marked ({display_hours}h): Apply for remaining half"
        #     else:
        #         suffix = ""
        #         if arq_is_rejected:
        #             suffix = " (Action needed)"
        #         elif display_hours < HALF_DAY_THRESHOLD and not is_full_day_doc:
        #             if not (has_leave and has_arq):
        #                 suffix = " (Remaining half pending)"
                
        #         remark = f"{combined}{suffix}"

            leave_names_str = ", ".join([l.name for l in all_leaves]) if has_leave else None
            leave_status_str = ", ".join([l.status for l in all_leaves]) if has_leave else None
            final_arq_status = "Rejected" if arq_is_rejected else ("Submitted" if arq_is_submitted else ("Draft" if has_arq else None))

            result_list.append({
                "date": date_str,
                "employee": employee,
                "employee_name": employee_name,
                "shift": shift,
                "logs": logs,
                "hours": display_hours,
                "remark": remark,
                # Include the current status so the UI can show if it's "Absent", "Half Day", or "Missing Record"
                "current_status": current_status, 
                "leave_name": leave_names_str,
                "leave_status": leave_status_str,
                "arq_name": arq_info.get("name") if has_arq else None,
                "arq_status": final_arq_status,
                "is_full_day_doc": is_full_day_doc
            })

    # Optional: Reverse the list so the newest dates are at the top (since we iterated chronologically)
    if sort_order == "desc":
        result_list.reverse()

    return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}

@frappe.whitelist()
def get_simple_logs_for_leave(employee, attendance_date):
    """
    Returns a clean, simple HTML table of punches without 
    strikethroughs or regularization labels.
    """
    if not employee or not attendance_date:
        return None

    logs = frappe.get_all("Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [attendance_date + " 00:00:00", attendance_date + " 23:59:59"]]
        },
        fields=["time", "log_type"],
        order_by="time asc"
    )

    if not logs:
        return None

    html = """
    <table class='table table-bordered' style='font-size:13px; border: 1px solid #d1d8dd; margin: 0;'>
        <thead>
            <tr style='background:#3498DB; color:white;'>
                <th style='width: 70%'>Punch Time</th>
                <th style='width: 30%'>Type</th>
            </tr>
        </thead>
        <tbody>
    """

    for log in logs:
        time_str = log.time.strftime("%H:%M:%S")
        html += f"<tr><td>{time_str}</td><td>{log.log_type}</td></tr>"

    html += "</tbody></table>"
    return html

@frappe.whitelist()
def get_approver_name_service(user_id):
    """
    Expert Helper: Fetches Employee Name from User ID.
    Bypasses client-side permission restrictions.
    """
    if not user_id:
        return None
    return frappe.db.get_value("Employee", {"user_id": user_id}, "employee_name")

# on 20 march at 6:18pm------------------------------------

# @frappe.whitelist()
# @frappe.whitelist()
# def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
#     # 1. Handle Date Defaults
#     if not from_date or not to_date or from_date == "undefined":
#         to_date = frappe.utils.today()
#         from_date = str(frappe.utils.add_days(to_date, -30))

#     # Include docstatus 2 (Cancelled) so rows don't vanish during Draft stage
#     filters = {
#         "status": ["in", ["Absent", "Half Day"]],
#         "docstatus": ["in", [1, 2]], 
#         "attendance_date": ["between", [from_date, to_date]]
#     }
    
#     if employee and employee not in ["", "undefined", "null"]:
#         filters["employee"] = employee

#     absents = frappe.get_all("Attendance", filters=filters,
#         fields=["name", "attendance_date", "employee", "employee_name", "working_hours", "status", "shift", "docstatus"],
#         order_by=f"attendance_date {sort_order}, docstatus asc")

#     result_list = []
#     processed_days = set()
#     HALF_DAY_THRESHOLD = 4.0 

#     for ab in absents:
#         # --- EXPERT ADDITION: HIDE IF PRESENT ---
#         # If any record for this day is already 'Present', skip this day entirely
#         if frappe.db.exists("Attendance", {
#             "employee": ab.employee, 
#             "attendance_date": ab.attendance_date, 
#             "status": "Present", 
#             "docstatus": 1
#         }):
#             continue

#         # DE-DUPLICATION (Fixed: Only one check needed)
#         day_key = f"{ab.employee}_{ab.attendance_date}"
#         if day_key in processed_days: continue
#         processed_days.add(day_key)

#         start_dt = f"{ab.attendance_date} 00:00:00"
#         end_dt = f"{ab.attendance_date} 23:59:59"

#         logs = frappe.get_all("Employee Checkin", 
#             filters={"employee": ab.employee, "time": ["between", [start_dt, end_dt]]}, 
#             fields=["time", "log_type", "system_generated"], order_by="time asc")

#         # Calculate Display Hours
#         temp_logs = list(logs)
#         if temp_logs and len(temp_logs) % 2 != 0:
#             if temp_logs[-1]["log_type"] == "IN":
#                 temp_logs.append({"time": temp_logs[-1]["time"] + timedelta(minutes=1), "log_type": "OUT"})

#         total_seconds = 0
#         last_in = None
#         for log in temp_logs:
#             if log["log_type"] == "IN" and not last_in: last_in = log["time"]
#             elif log["log_type"] == "OUT" and last_in:
#                 total_seconds += (log["time"] - last_in).total_seconds()
#                 last_in = None
#         display_hours = round(total_seconds / 3600, 2)

#         # FETCH DOCUMENTS
#         leave_info = frappe.db.get_value("Leave Application", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, 
#             ["name", "status", "half_day"], as_dict=True)
            
#         arq_info = frappe.db.get_value("Attendance Request", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date": ab.attendance_date}, 
#             ["name", "docstatus", "half_day"], as_dict=True)

#         has_leave = bool(leave_info)
#         leave_is_approved = bool(has_leave and leave_info.get("status") == "Approved")
#         has_arq = bool(arq_info)
#         arq_is_submitted = bool(has_arq and arq_info.get("docstatus") == 1)

#         is_full_day_doc = (has_leave and not leave_info.get("half_day")) or (has_arq and not arq_info.get("half_day"))

#         # --- DRAFT-AWARE RESOLUTION LOGIC ---
#         requires_action = True
#         is_any_draft = (has_leave and leave_info.status in ["Draft", "Open"]) or (has_arq and arq_info.docstatus == 0)

#         if is_any_draft:
#             requires_action = True
#         elif (leave_is_approved and not leave_info.get("half_day")) or (arq_is_submitted and not arq_info.get("half_day")):
#             requires_action = False 
#         elif display_hours >= HALF_DAY_THRESHOLD and (leave_is_approved or arq_is_submitted):
#             requires_action = False
#         elif leave_is_approved and arq_is_submitted:
#             requires_action = False

#         if requires_action:
#             l_status = ""
#             if has_leave:
#                 l_status = "Leave Approved" if leave_is_approved else ("Leave in Draft" if leave_info.status=="Draft" else "Leave Awaiting Approval")
            
#             a_status = ""
#             if has_arq:
#                 a_status = "On-Duty Req Approved" if arq_is_submitted else ("On-Duty Req in Draft" if arq_info.docstatus==0 else "On-Duty Req Awaiting Approval")

#             # --- UPDATED REMARK LOGIC (FIXED SUFFIX) ---
#             combined = " & ".join(filter(None, [l_status, a_status]))
            
#             if not combined:
#                 # No documents applied yet
#                 if display_hours == 0:
#                     remark = "No Checkins: Regularization Required"
#                 elif display_hours < HALF_DAY_THRESHOLD:
#                     remark = f"Short Attendance ({display_hours}h): Regularization Required"
#                 else:
#                     remark = f"Half Day Threshold Met ({display_hours}h): Apply for remaining half"
#             else:
#                 # Documents exist
#                 suffix = ""
#                 # THE FIX: Only show 'Remaining' if hours are SHORT 
#                 # AND they have NOT YET applied for BOTH types of documents.
#                 # We check 'has_leave' and 'has_arq' (Existence) instead of approval status.
#                 if display_hours < HALF_DAY_THRESHOLD and not is_full_day_doc:
#                     if not (has_leave and has_arq):
#                         suffix = " (Remaining half pending)"
                
#                 remark = f"{combined}{suffix}"

#             result_list.append({
#                 "date": ab.attendance_date,
#                 "employee": ab.employee,
#                 "employee_name": ab.employee_name,
#                 "shift": ab.shift or "",
#                 "logs": logs,
#                 "hours": display_hours,
#                 "remark": remark,
#                 "leave_name": leave_info.get("name") if has_leave else None,
#                 "leave_status": leave_info.get("status") if has_leave else None,
#                 "arq_name": arq_info.get("name") if has_arq else None,
#                 "arq_status": "Submitted" if arq_is_submitted else ("Draft" if has_arq else None),
#                 "is_full_day_doc": is_full_day_doc
#             })

#     return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}


# @frappe.whitelist()
# def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
#     if not from_date or not to_date or from_date == "undefined":
#         to_date = frappe.utils.today()
#         from_date = str(frappe.utils.add_days(to_date, -30))

#     filters = {
#         "status": ["in", ["Absent", "Half Day"]],
#         "docstatus": 1,
#         "attendance_date": ["between", [from_date, to_date]]
#     }
    
#     if employee and employee not in ["", "undefined", "null"]:
#         filters["employee"] = employee

#     absents = frappe.get_all("Attendance", filters=filters,
#         fields=["name", "attendance_date", "employee", "employee_name", "working_hours", "status", "shift"],
#         order_by=f"attendance_date {sort_order}")

#     result_list = []
#     processed_days = set()
#     HALF_DAY_THRESHOLD = 4.0 

#     for ab in absents:
#         day_key = f"{ab.employee}_{ab.attendance_date}"
#         if day_key in processed_days: continue
#         processed_days.add(day_key)

#         start_dt = f"{ab.attendance_date} 00:00:00"
#         end_dt = f"{ab.attendance_date} 23:59:59"

#         logs = frappe.get_all("Employee Checkin", 
#             filters={"employee": ab.employee, "time": ["between", [start_dt, end_dt]]}, 
#             fields=["time", "log_type", "system_generated"], order_by="time asc")

#         # Calculate Display Hours
#         temp_logs = list(logs)
#         if temp_logs and len(temp_logs) % 2 != 0:
#             if temp_logs[-1]["log_type"] == "IN":
#                 temp_logs.append({"time": temp_logs[-1]["time"] + timedelta(minutes=1), "log_type": "OUT"})

#         total_seconds = 0
#         last_in = None
#         for log in temp_logs:
#             if log["log_type"] == "IN" and not last_in: last_in = log["time"]
#             elif log["log_type"] == "OUT" and last_in:
#                 total_seconds += (log["time"] - last_in).total_seconds()
#                 last_in = None
        
#         display_hours = round(total_seconds / 3600, 2)

#         # FETCH DOCUMENTS WITH FULL/HALF DAY CHECK
#         leave_info = frappe.db.get_value("Leave Application", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, 
#             ["name", "status", "half_day"], as_dict=True)
            
#         arq_info = frappe.db.get_value("Attendance Request", 
#             {"employee": ab.employee, "docstatus": ["<", 2], "from_date": ab.attendance_date}, 
#             ["name", "docstatus", "half_day"], as_dict=True)

#         has_leave = bool(leave_info)
#         # Check if it's a Full Day Leave (half_day is 0)
#         is_full_leave = bool(has_leave and not leave_info.get("half_day"))
#         leave_approved = bool(has_leave and leave_info.get("status") == "Approved")
        
#         has_arq = bool(arq_info)
#         is_full_arq = bool(has_arq and not arq_info.get("half_day"))
#         arq_approved = bool(has_arq and arq_info.get("docstatus") == 1)

#         # RESOLUTION LOGIC
#         requires_action = True
        
#         # 1. If a FULL DAY document is approved, hide it!
#         if (leave_approved and is_full_leave) or (arq_approved and is_full_arq):
#             requires_action = False
#         # 2. If it's a Half Day Attendance and one document is approved, hide it!
#         elif (leave_approved or arq_approved) and display_hours >= HALF_DAY_THRESHOLD:
#             requires_action = False
#         # 3. If BOTH half-day documents are approved, hide it!
#         elif leave_approved and arq_approved:
#             requires_action = False

#          # Determine if any existing document is a Full Day document
#         is_full_day_doc = (has_leave and not leave_info.get("half_day")) or \
#                          (has_arq and not arq_info.get("half_day"))   

#         if requires_action:
#             # --- PROFESSIONAL REMARK LOGIC (FIXED) ---
#             l_status = ""
#             if has_leave:
#                 l_status = "Leave Approved" if leave_approved else ("Leave in Draft" if leave_info.status=="Draft" else "Leave Awaiting Approval")
            
#             a_status = ""
#             if has_arq:
#                 a_status = "ARQ Approved" if arq_approved else ("Attendance Request in Draft" if arq_info.docstatus==0 else "ARQ Awaiting Approval")

#             combined = " & ".join(filter(None, [l_status, a_status]))
            
#             if not combined:
#                 # No documents applied yet
#                 if display_hours == 0:
#                     remark = "No Checkins: Regularization Required"
#                 elif display_hours < HALF_DAY_THRESHOLD:
#                     # Actually Short (e.g. 2.5h)
#                     remark = f"Short Hours ({display_hours}h): Regularization Required"
#                 else:
#                     # Threshold Met (e.g. 5.18h)
#                     remark = f"Half Day Threshold Met ({display_hours}h): Apply for remaining half"

#             else:
#                 # Documents exist, handle the "Remaining" message
#                 suffix = ""
#                 # FIX: Only show 'Remaining' if the office hours are SHORT (< 4h)
#                 # If hours are >= 4.0, one Half Day doc is enough, so no suffix needed.
#                 if display_hours < HALF_DAY_THRESHOLD and not (is_full_leave or is_full_arq) and not (has_leave and has_arq):
#                     suffix = " (Remaining half pending)"
#                 remark = f"{combined}{suffix}"
#             # else:
#             #     # Documents exist, handle the "Remaining" message
#             #     suffix = ""
#             #     # Only show remaining if it's not a full day doc and only one part is applied
#             #     if not (is_full_leave or is_full_arq) and not (has_leave and has_arq):
#             #         suffix = " (Remaining half pending)"
#             #     remark = f"{combined}{suffix}"

#             result_list.append({
#                 "date": ab.attendance_date,
#                 "employee": ab.employee,
#                 "employee_name": ab.employee_name,
#                 "shift": ab.shift or "",
#                 "logs": logs,
#                 "hours": display_hours,
#                 "remark": remark,
#                 "leave_name": leave_info.get("name") if has_leave else None,
#                 "leave_status": leave_info.get("status") if has_leave else None,
#                 "arq_name": arq_info.get("name") if has_arq else None,
#                 "arq_status": "Submitted" if arq_approved else ("Draft" if has_arq else None),
#                 "is_full_day_doc": is_full_day_doc  # <-- ADD THIS LINE
#             })

#     return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}


@frappe.whitelist()
def get_simple_logs_for_leave(employee, attendance_date):
    """
    Returns a clean, simple HTML table of punches without
    strikethroughs or regularization labels.
    """
    if not employee or not attendance_date:
        return None
 
    logs = frappe.get_all("Employee Checkin",
        filters={
            "employee": employee,
            "time": ["between", [attendance_date + " 00:00:00", attendance_date + " 23:59:59"]]
        },
        fields=["time", "log_type"],
        order_by="time asc"
    )
 
    if not logs:
        return None
 
    html = """
    <table class='table table-bordered' style='font-size:13px; border: 1px solid #d1d8dd; margin: 0;'>
        <thead>
            <tr style='background:#3498DB; color:white;'>
                <th style='width: 70%'>Punch Time</th>
                <th style='width: 30%'>Type</th>
            </tr>
        </thead>
        <tbody>
    """
 
    for log in logs:
        time_str = log.time.strftime("%H:%M:%S")
        html += f"<tr><td>{time_str}</td><td>{log.log_type}</td></tr>"
 
    html += "</tbody></table>"
    return html
 
@frappe.whitelist()
def get_approver_name_service(user_id):
    """
    Expert Helper: Fetches Employee Name from User ID.
    Bypasses client-side permission restrictions.
    """
    if not user_id:
        return None
    return frappe.db.get_value("Employee", {"user_id": user_id}, "employee_name")


@frappe.whitelist()
def get_my_pending_arq():
    user = frappe.session.user
    # Get employee ID for the logged-in user
    employee_id = frappe.db.get_value("Employee", {"user_id": user}, "name")
    
    # 1. Main filters: Must be Draft (docstatus 0) 
    filters = {
        'docstatus': 0,
        'custom_status': ['not in', ['Rejected', 'Cancelled']]
    }
    
    # 2. OR filters: (I am the Approver) OR (I am the Applicant)
    or_filters = [
        ['custom_attendance_request_approver', '=', user]
    ]
    
    if employee_id:
        or_filters.append(['employee', '=', employee_id])

    # 3. Fetch the requests
    arq_list = frappe.get_all(
        'Attendance Request',
        filters=filters,
        or_filters=or_filters,
        fields=['name', 'employee', 'employee_name', 'custom_attendance_request_approver', 'from_date', 'half_day', 'reason'],
        order_by="creation desc"
    )
 
    for req in arq_list:
        # Check if the logged-in user is the one who needs to click 'Approve'
        req["is_approver"] = (req.custom_attendance_request_approver == user)
        
        if req.custom_attendance_request_approver:
            req["approver_display_name"] = frappe.db.get_value("User", req.custom_attendance_request_approver, "full_name") or req.custom_attendance_request_approver
        else:
            req["approver_display_name"] = "-"
            
    return arq_list