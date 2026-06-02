import frappe
from datetime import datetime, timedelta, date
from frappe.utils import get_first_day, get_last_day, add_months, getdate, add_days, now_datetime


@frappe.whitelist()
def get_approved_leave_applications():
    all_emp = frappe.get_all("Employee",fields=["name","employee_name","user_id"])
    emp_dict = {i.user_id: i.employee_name for i in all_emp}

    current_date = now_datetime().date()  # Get the current date in YYYY-MM-DD format
    leave_applications = frappe.get_all(
        'Leave Application',
        filters={
            'status': 'Approved',
            'docstatus': 1,
            'to_date': ['>=', current_date]  # Filter to get only to_date greater than or equal to current date
        },
        fields=["name",'employee_name', "leave_approver", 'from_date', 'to_date', 'total_leave_days','name']
    )
    for app in leave_applications:
        if app.leave_approver and app.leave_approver in emp_dict:
            
            app["leave_approver_name"]=emp_dict[app.leave_approver]
    
    return leave_applications



@frappe.whitelist()
def get_unapproved_leave_applications_hr():
    all_emp = frappe.get_all("Employee",fields=["name","employee_name","user_id"])
    emp_dict = {i.user_id: i.employee_name for i in all_emp}

    leave_applications = frappe.get_all(
        'Leave Application',
        filters={
            'docstatus': 0,
            "status": ("not in", ["Cancelled"]),
            # 'to_date': ['>=', current_date]  # Filter to get only to_date greater than or equal to current date
        },
        fields=['employee_name',"leave_approver",'posting_date','from_date', 'to_date', 'total_leave_days','name']
    )
 
    

    for app in leave_applications:
        if app.leave_approver and app.leave_approver in emp_dict:
            
            app["leave_approver_name"]=emp_dict[app.leave_approver]
    return leave_applications




# @frappe.whitelist()
# def get_employees_with_absent():

#     cur_month = frappe.utils.now_datetime().month

#     # Fetch employees with birthdays in the current month
#     employees = frappe.get_all("Employee", 
#                                    filters={"status":"Active"}, 
#                                    fields=["name","employee_name","company","designation","department"])
#     if employees:
#         employees_dict = {}
#         for emp in employees:
#             employees_dict[emp.name] = emp.employee_name
        
#         today = date.today()

#         if today.month == 1:
#             start_date = date(today.year - 1, 12, 1)
#         else:
#             start_date = date(today.year, today.month - 1, 1)

#         # Calculate the end date of the current month
#         if today.month == 12:
#             end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
#         else:
#             end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)


#         leave_applications = frappe.get_all("Leave Application",
#                                              filters={
#                                                       "from_date": ("between", [str(start_date), str(end_date)]),
#                                                       },
#                                              fields=["name", "from_date", "to_date", "employee","status"])
        

#         # Initialize the dictionary
#         leave_dict = {}

#         # Iterate over each leave application
#         for leave in leave_applications:
#             # from_date = datetime.strptime(str(leave["from_date"]), "%Y-%m-%d")
#             # to_date = datetime.strptime(str(leave["to_date"]), "%Y-%m-%d")
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
#                                               "attendance_date": ("between", [str(start_date), str(end_date)]),
#                                               },
#                                      fields=["name", "attendance_date", "employee","working_hours"],
#                                      order_by="attendance_date desc")
#         absent_data = {}
#         emp_count = {}
#         for ab_date in absent_date:
#             absent_date_checkin = frappe.get_all("Employee Checkin",
#                                      filters={"attendance": ab_date.name},
#                                      fields=["name", "time", "log_type","system_generated"],
#                                      order_by="time asc")

#             if str(ab_date.attendance_date) not in absent_data:
#                 absent_data[str(ab_date.attendance_date)] = []

#             if ab_date.employee not in employees_dict :
#                 continue
#             if employees_dict[ab_date.employee] not in emp_count:
#                 emp_count[employees_dict[ab_date.employee]]=0
#             emp_count[employees_dict[ab_date.employee]]+=1

#             if (ab_date.attendance_date,ab_date.employee) in leave_dict:
#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], False, absent_date_checkin,ab_date.working_hours,"Applied for leave but not approved"])
#             elif absent_date_checkin and (len(absent_date_checkin)%2 != 0 or absent_date_checkin[0].log_type == "OUT"):
#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], True, absent_date_checkin,ab_date.working_hours,"Mismatch in Checkins"])
#             elif absent_date_checkin :
#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], True, absent_date_checkin,ab_date.working_hours,"Short working hours"])
#             else:
#                 absent_data[str(ab_date.attendance_date)].append([employees_dict[ab_date.employee], False, absent_date_checkin,ab_date.working_hours,"Need to apply for Leave"])

#         return {"absent_data":absent_data,"emp_count":emp_count}
#     return None




# @frappe.whitelist()
# def get_employees_with_absent(from_date=None, to_date=None, employee=None, sort_order="desc"):
#     print("DDDDDDDDDDDDDDDDDDDdddddddddddddddddddddd",from_date, to_date)
#     # 1. Standard Date Setup
#     if not from_date or not to_date:
#         to_date = today()
#         from_date = str(add_days(to_date, -30))

#     # 2. Build Filters
#     filters = {
#         "status": "Absent",
#         "docstatus": 1,
#         "attendance_date": ["between", [from_date, to_date]]
#     }
    
#     # Apply Employee filter if selected
#     if employee and employee != "" and employee != "undefined":
#         filters["employee"] = employee

#     # 3. Fetch Absences
#     absents = frappe.get_all("Attendance",
#         filters=filters,
#         fields=["name", "attendance_date", "employee", "employee_name", "working_hours"],
#         order_by=f"attendance_date {sort_order}"
#     )

#     result_list = []
#     for ab in absents:
#         # Fetch Logs
#         # logs = frappe.get_all("Employee Checkin", filters={"attendance": ab.name}, fields=["time", "log_type"], order_by="time asc")
#         start_date = f"{ab.attendance_date} 00:00:00"
#         end_date = f"{ab.attendance_date} 23:59:59"

#         # Fetch Logs based on Employee and Time range
#         logs = frappe.get_all("Employee Checkin", 
#             filters={
#                 "employee": ab.employee,
#                 "time": ["between", [start_date, end_date]]
#             }, 
#             fields=["time", "log_type", "name","system_generated"], 
#             order_by="time asc"
#         )

#         # Get Shift
#         shift = frappe.db.get_value("Employee", ab.employee, "default_shift")

#         # Check for Open Documents (Drafts)
#         open_leave = frappe.db.get_value("Leave Application", 
#             {"employee": ab.employee, "docstatus": 0, "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, "name")
        
#         open_arq = frappe.db.get_value("Attendance Request", 
#             {"employee": ab.employee, "docstatus": 0, "from_date": ab.attendance_date}, "name")

#         # Remarks Logic
#         remark = "No Leave application found"
#         if not logs:
#             remark = "No Checkins found"
#         elif len(logs) % 2 != 0 or logs[0].log_type == "OUT":
#             remark = "Checkin Mismatch"
#         elif ab.working_hours and ab.working_hours < 4: 
#             remark = "Short working hours"

#         result_list.append({
#             "date": ab.attendance_date,
#             "employee": ab.employee,
#             "employee_name": ab.employee_name,
#             "shift": shift or "",
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

# from datetime import timedelta
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
#         logs = frappe.get_all("Employee Checkin", 
#             filters={
#                 "employee": ab.employee,
#                 "time": ["between", [start_dt, end_dt]]
#             }, 
#             fields=["time", "log_type", "system_generated"], 
#             order_by="time asc"
#         )

#         # If mismatch logs (odd count), simulate system generated OUT
#         if logs and len(logs) % 2 != 0:
#             last_log = logs[-1]

#             if last_log["log_type"] == "IN":
#                 sys_out_time = last_log["time"] + timedelta(minutes=1)

#                 logs.append({
#                     "time": sys_out_time,
#                     "log_type": "OUT",
#                     "system_generated": 1
#                 })

#         # Manual Hours Calculation
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
#         display_hours = ab.working_hours if ab.working_hours > 0 else calc_hours

#         shift = frappe.db.get_value("Employee", ab.employee, "default_shift")
#         open_leave = frappe.db.get_value("Leave Application", {"employee": ab.employee, "docstatus": ["in",[0,1]], "from_date": ["<=", ab.attendance_date], "to_date": [">=", ab.attendance_date]}, "name")
#         open_arq = frappe.db.get_value("Attendance Request", {"employee": ab.employee, "docstatus":  ["in",[0,1]], "from_date": ab.attendance_date}, "name")

#         # Refined Remarks
#         remark = f"Resolve required ({ab.status})"

#         if not logs:
#             remark = "No Checkins found"

#         if ab.status == "Half Day" and display_hours > 0:
#             remark = "Half day present – Apply Leave for remaining"

#         elif ab.status == "Half Day" and display_hours == 0:
#             remark = "Half day absent – resolve attendance"

#         elif logs and logs[-1].get("system_generated"):
#             remark = "System generated checkout"

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



from mobile_app_360ithub.custom_employee import get_employees_with_absent


@frappe.whitelist()
def get_hr_absent_dashboard_data(from_date=None, to_date=None, employee=None, sort_order="desc"):
    """
    This is the single source of truth for both Employee and HR dashboards.
    - If 'employee' is passed, it runs for that employee (for HR filter).
    - If 'employee' is NOT passed, it runs for the logged-in user's employee record.
    - An HR Manager (or user with read access to all Attendance) can pass an empty 'employee'
      to fetch data for ALL employees.
    """
    if not from_date or not to_date or from_date == "undefined":
        to_date = today()
        from_date = str(add_days(to_date, -30))

    end_date = min(getdate(to_date), getdate(today()))
    start_date = getdate(from_date)
    
    employee_list = []
    if employee and employee not in ["", "undefined", "null"]:
        is_active = frappe.db.get_value("Employee", employee, "status") == "Active"
        if not is_active:
            return {"data": [], "count": 0, "from_date": from_date, "to_date": to_date}
        # Case 1: HR has filtered for a specific employee
        employee_list.append(employee)
    else:
        # Case 2: No specific employee filtered. Who is calling?
        if frappe.has_permission("Attendance", "read"): # Check if user can see others' attendance
            # User is likely HR/Manager. Fetch all active employees.
            employee_list = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name")
        else:
            # User is a regular employee. Fetch only their own record.
            my_employee_id = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
            if my_employee_id:
                employee_list.append(my_employee_id)

    if not employee_list:
        return {"data": [], "count": 0, "from_date": from_date, "to_date": to_date}

    result_list = []
    
    # Iterate through the list of employees to process
    for emp in employee_list:
        
        resp_data = get_employees_with_absent(
                                            from_date=from_date, 
                                            to_date=to_date, 
                                            employee=emp, 
                                            sort_order=sort_order
                                        )
        emp_result_list = resp_data["data"]
        result_list.extend(emp_result_list)
        

    if sort_order == "desc":
        result_list.sort(key=lambda x: x['date'], reverse=True)
    else:
        result_list.sort(key=lambda x: x['date'])

    return {"data": result_list, "count": len(result_list), "from_date": from_date, "to_date": to_date}

# on 20 march at 6:18pm------------------------------------

# from datetime import timedelta
# from frappe.utils import getdate
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
#         "docstatus": ["!=", 2],
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
    


# For Management Team auto attendance 13 march

from frappe.utils import get_first_day, today, add_days, getdate

def mark_management_attendance():
    """Run daily via scheduler to mark attendance for management (Month-to-Date)"""
    
    # Update these with actual Employee IDs
    management_employees =[
        "HR-EMP-00001", # Sridhar
        "HR-EMP-00003", # Swarup
        "HR-EMP-00007", # Sridevi
        "HR-EMP-00008", # Pathy
        "HR-EMP-00009"  # Shivalingu
    ]

    # Check from the 1st of the current month up to today
    start_date = get_first_day(today())
    end_date = today()

    for emp_id in management_employees:
        emp = frappe.get_doc("Employee", emp_id)
        if emp.status != "Active":
            continue

        holiday_list = emp.holiday_list or frappe.db.get_value("Company", emp.company, "default_holiday_list")

        current_date = getdate(start_date)
        while current_date <= getdate(end_date):
            date_str = str(current_date)

            # 1. Skip if on Approved Leave
            if frappe.db.exists("Leave Application", {"employee": emp_id, "docstatus": 1, "from_date":["<=", date_str], "to_date": [">=", date_str]}):
                current_date = add_days(current_date, 1)
                continue

            # 2. Skip if Holiday
            if holiday_list and frappe.db.exists("Holiday", {"parent": holiday_list, "holiday_date": date_str}):
                current_date = add_days(current_date, 1)
                continue

            # 3. Check existing attendance for this specific date
            existing_att = frappe.db.exists("Attendance", {"employee": emp_id, "attendance_date": date_str, "docstatus":["<", 2]})
            
            if existing_att:
                att_status = frappe.db.get_value("Attendance", existing_att, "status")
                if att_status == "Present":
                    # Already correct, move to the next day!
                    current_date = add_days(current_date, 1)
                    continue
                else:
                    # It is Absent or Half Day! We must cancel it to fix it.
                    doc = frappe.get_doc("Attendance", existing_att)
                    if doc.docstatus == 1:
                        doc.cancel()
                    else:
                        frappe.delete_doc("Attendance", existing_att)

            # 4. Create the correct "Present" Attendance
            att = frappe.get_doc({
                "doctype": "Attendance",
                "employee": emp_id,
                "attendance_date": date_str,
                "status": "Present",
                "company": emp.company
            })
            att.insert(ignore_permissions=True)
            att.submit()

            # Move to next day
            current_date = add_days(current_date, 1)





# from frappe import _

# def clear_attendance_request_conflict(doc, method=None):
#     """
#     EXPERT PATH CLEARER:
#     Cancels existing attendance so the ARQ can overwrite it.
#     """
#     # Look for existing attendance (Draft or Submitted)
#     existing_att = frappe.db.get_value("Attendance", {
#         "employee": doc.employee,
#         "attendance_date": doc.from_date,
#         "docstatus": ["<", 2] 
#     }, ["name", "docstatus"], as_dict=True)

#     if existing_att:
#         if existing_att.docstatus == 1:
#             att_doc = frappe.get_doc("Attendance", existing_att.name)
#             att_doc.cancel()
#         else:
#             frappe.delete_doc("Attendance", existing_att.name)
        
#         # CRITICAL: Force DB to save and clear cache 
#         # so standard HRMS validation sees the record is GONE.
#         frappe.db.commit()
#         frappe.clear_cache()
        
#         frappe.msgprint(_("Note: Biometric record {0} cleared to allow regularization.").format(existing_att.name))

from frappe import _

def clear_attendance_request_conflict(doc, method=None):
    """
    EXPERT PATH CLEARER (Corrected Permission Bypass):
    Cancels existing attendance so the ARQ can overwrite it.
    Uses flags.ignore_permissions to bypass user role restrictions.
    """
    # -------------------------------
    # 🔹 PART 1: Set Approver Employee
    # -------------------------------
    if doc.custom_attendance_request_approver:
        employee = frappe.db.get_value(
            "Employee",
            {"user_id": doc.custom_attendance_request_approver},
            "name"
        )

        if employee:
            doc.custom_attendance_request_approver_employee = employee
        else:
            doc.custom_attendance_request_approver_employee = None
            # Optional strict validation:
            # frappe.throw("No Employee found for selected Approver User")

    # Look for existing attendance (Draft or Submitted)
    existing_att = frappe.db.get_value("Attendance", {
        "employee": doc.employee,
        "attendance_date": doc.from_date,
        "docstatus": ["<", 2] 
    }, ["name", "docstatus"], as_dict=True)

    if existing_att:
        if existing_att.docstatus == 1:
            # For Submitted records: MUST use cancel()
            att_doc = frappe.get_doc("Attendance", existing_att.name)
            att_doc.flags.ignore_permissions = True
            att_doc.cancel()
        else:
            # For Draft records: Use delete_doc
            # delete_doc DOES accept ignore_permissions as a direct argument
            frappe.delete_doc("Attendance", existing_att.name, ignore_permissions=True)
        
        # CRITICAL: Force DB to save and clear cache 
        # so standard HRMS validation sees the record is GONE.
        frappe.db.commit()
        frappe.clear_cache()
        
        # frappe.msgprint(_("Note: Biometric record {0} cleared to allow regularization.").format(existing_att.name))


@frappe.whitelist()
def auto_submit_on_approval(doc, method=None):
    """
    Expert Hook: Triggered when a manager clicks 'Save'.
    If the status is 'Approved' and the user is the designated approver,
    the system forces a SUBMIT to bypass role permission limits.
    """
    # 1. Only run if the document is a Draft and the status is set to Approved
    if doc.docstatus == 0 and doc.custom_status == "Approved":
        
        current_user = frappe.session.user
        
        master_roles = set()
        master_roles.add("System Manager")
        try:
            clarity_settings = frappe.get_cached_doc("Mobile App Admin Settings")
            master_roles = set([row.role for row in clarity_settings.get("hr_admin_role", [])])
        except frappe.DoesNotExistError:
            # Fallback if settings document has not been initialized yet
            pass
        
        user_roles = set(frappe.get_roles(current_user))
        
        # 2. Authorization Evaluation
        is_admin = bool(user_roles.intersection(master_roles))
        is_approver = (current_user == doc.custom_attendance_request_approver)
        
        # If the user is neither an authorized admin nor the designated approver, block the action
        if not (is_admin or is_approver):
            approver_name = frappe.db.get_value("User", doc.custom_attendance_request_approver, "full_name") or doc.custom_attendance_request_approver
            frappe.throw(
                _("Only the designated approver ({0}) or an authorized HR Admin is permitted to approve this request.")
                .format(approver_name)
            )
        
            # 3. FORCE SUBMIT: This bypasses the need for the "Submit" checkbox in Role Permissions
        doc.flags.ignore_permissions = True
        doc.submit()
        
        # Add a comment for the audit trail
        frappe.msgprint(frappe._("Attendance Request for {0} has been officially Approved and Submitted.").format(doc.employee_name))


def validate_approver_authority(doc, method=None):
    """
    Expert Authority Hook:
    Prevents unauthorized users from changing the status to Approved or Rejected.
    """
    # 1. We only care if someone is trying to Approve or Reject
    if doc.custom_status in ["Approved", "Rejected"]:
        
        current_user = frappe.session.user
        
        # 2. Bypass check for Administrator (System override)
        if current_user == "Administrator":
            return
        
        user_roles = set(frappe.get_roles())
        clarity_settings = frappe.get_cached_doc("Mobile App Admin Settings")
        master_roles = set([row.role for row in clarity_settings.get("hr_admin_role", [])])
        if user_roles.intersection(master_roles):
            return

        # 3. Check if the logged-in user is NOT the designated approver
        if current_user != doc.custom_attendance_request_approver:
            
            # Fetch the actual Name of the designated approver for the message
            approver_full_name = frappe.db.get_value("User", doc.custom_attendance_request_approver, "full_name") or doc.custom_attendance_request_approver
            
            # 4. Throw a hard error to block the save
            frappe.throw(
                frappe._("Only the designated approver ({0}) is authorized to {1} this request.").format(
                    frappe.bold(approver_full_name), 
                    doc.custom_status.lower()
                )
            )




from frappe import _
from frappe.utils import getdate, today, format_date

# --- HELPERS ---

def get_dt_fmt(d):
    """Formats date strictly as DD-MM-YYYY (e.g., 17-04-2026)"""
    return getdate(d).strftime("%d-%m-%Y")

def get_user_full_name(user_id):
    """Fetches the actual Full Name of a User ID (Email)"""
    return frappe.db.get_value("User", user_id, "full_name") or "User"

def get_hr_manager_emails():
    """Fetches all emails of users with the HR Manager role"""
    return [u.parent for u in frappe.get_all("Has Role", filters={"role": "HR Manager"}, fields=["parent"])]

def get_employee_email(employee):
    """Fetches employee email from master"""
    return frappe.db.get_value("Employee", employee, "prefered_email") or \
           frappe.db.get_value("Employee", employee, "user_id")

# --- 1. LEAVE TRIGGERS ---

def handle_leave_email_triggers(doc, method=None):
    # Rule: Backdated applications do NOT trigger mail
    if getdate(doc.from_date) < getdate(today()):
        return

    # A. On Application -> Send to Approver
    if method == "after_insert" and doc.leave_approver:
        approver_name = get_user_full_name(doc.leave_approver)
        subject = _("New Leave Application: {0}").format(doc.employee_name)
        message = f"""
            <div style="font-family: sans-serif; color: #333;">
                <p>Dear <b>{approver_name}</b>,</p>
                <p>A new leave request from <b>{doc.employee_name}</b> is pending your approval.</p>
                <p><b>Dates:</b> {get_dt_fmt(doc.from_date)} to {get_dt_fmt(doc.to_date)}</p>
                <p><b>Type:</b> {doc.leave_type}</p>
                <p><a href="{frappe.utils.get_url_to_form(doc.doctype, doc.name)}"style="background-color: #3498DB; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">Click here to View & Approve</a></p>
            </div>
        """
        frappe.sendmail(recipients=[doc.leave_approver], subject=subject, message=message, now=True)

    # B. On Approval -> Send to Everyone
    elif method == "on_submit" and doc.status == "Approved":
        recipients = list(set([get_employee_email(doc.employee), doc.leave_approver] + get_hr_manager_emails()))
        subject = _("Leave Approved: {0}").format(doc.employee_name)
        message = f"""
            <div style="font-family: sans-serif;">
                <p>Dear Team,</p>
                <p>The leave application for <b>{doc.employee_name}</b> has been <b>Approved</b>.</p>
                <p><b>Period:</b> {get_dt_fmt(doc.from_date)} to {get_dt_fmt(doc.to_date)}</p>
            </div>
        """
        frappe.sendmail(recipients=recipients, subject=subject, message=message, now=True)

# --- 2. ON-DUTY (ARQ) TRIGGERS ---

def handle_arq_email_triggers(doc, method=None):
    if method == "after_insert" and doc.custom_attendance_request_approver:
        approver_name = get_user_full_name(doc.custom_attendance_request_approver)
        subject = _("On-Duty Request: {0}").format(doc.employee_name)
        message = f"""
            <div style="font-family: sans-serif;">
                <p>Dear <b>{approver_name}</b>,</p>
                <p><b>{doc.employee_name}</b> has submitted an On-Duty/Regularization request.</p>
                <p><b>Date:</b> {get_dt_fmt(doc.from_date)}</p>
                <p><b>Reason:</b> {doc.reason}</p>
                <p><a href="{frappe.utils.get_url_to_form(doc.doctype, doc.name)}" style="background-color: #3498DB; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">View Request</a></p>
            </div>
        """
        frappe.sendmail(recipients=[doc.custom_attendance_request_approver], subject=subject, message=message, now=True)

# --- 3. OT TRIGGERS (FIXED) ---

def handle_ot_email_triggers(doc, method=None):
    # Requirement: Only trigger on Application (after_insert)
    if method == "after_insert":
        # FIX: Changed 'doc.approver' to 'doc.overtime_request_approver' 
        # to match your system's actual field name.
        approver = getattr(doc, "overtime_request_approver", None) or \
                   frappe.db.get_value("Employee", doc.employee, "leave_approver")
        
        if approver:
            approver_name = get_user_full_name(approver)
            subject = _("New OT Request: {0}").format(doc.employee_name)
            
            message = f"""
                <div style="font-family: sans-serif; color: #333;">
                    <p>Dear <b>{approver_name}</b>,</p>
                    <p>An Overtime request has been submitted by <b>{doc.employee_name}</b> and is awaiting your approval.</p>
                    <hr style="border: none; border-top: 1px solid #eee;">
                    <p><b>Date:</b> {get_dt_fmt(doc.date)}</p>
                    <p><b>Requested Hours:</b> {getattr(doc, 'overtime_hours', 'N/A')}</p>
                    <hr style="border: none; border-top: 1px solid #eee;">
                    <p><a href="{frappe.utils.get_url_to_form(doc.doctype, doc.name)}" 
                          style="background-color: #3498DB; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;">
                          Review OT Request
                       </a></p>
                </div>
            """
            
            frappe.sendmail(
                recipients=[approver], 
                subject=subject, 
                message=message, 
                now=True
            )

# --- 4. SALARY SLIP TRIGGERS (VERIFIED) ---

def send_salary_slip_with_pdf(doc, method=None):
    """
    Corrected Version:
    Derives Month and Year from start_date to avoid AttributeError.
    """
    # 1. Fetch Recipient Email
    emp_email = get_employee_email(doc.employee)
    
    if not emp_email:
        return

    try:
        # 2. Derive Month and Year from start_date (e.g., "April" and "2026")
        # doc.start_date is a date object or string like "2026-04-01"
        dt_obj = getdate(doc.start_date)
        month_name = dt_obj.strftime("%B")
        year_val = dt_obj.strftime("%Y")

        # 3. Generate PDF using your specific Print Format
        pdf_content = frappe.get_print(
            "Salary Slip", 
            doc.name, 
            print_format="Salary Slip Custom Print Format", 
            as_pdf=True
        )
        
        # 4. Format Dates for the Message
        period_start = get_dt_fmt(doc.start_date)
        period_end = get_dt_fmt(doc.end_date)
        
        subject = _("Salary Slip: {0} {1}").format(month_name, year_val)
        
        message = f"""
            <div style="font-family: sans-serif; color: #333;">
                <p>Dear <b>{doc.employee_name}</b>,</p>
                <p>Please find attached your salary slip for the period <b>{period_start}</b> to <b>{period_end}</b>.</p>
                <br>
                <p>Regards,<br>Shanthala Chits Pvt Ltd</p>
            </div>
        """
        
        # 5. Send Email with corrected Attachment Name
        frappe.sendmail(
            recipients=[emp_email], 
            subject=subject, 
            message=message, 
            attachments=[{
                "fname": f"Salary_Slip_{doc.employee_name}_{month_name}_{year_val}.pdf", 
                "fcontent": pdf_content
            }],
            now=True
        )
        
        # Optional: Log success for HR to see in Desk
        frappe.msgprint(_("Salary Slip for {0} has been emailed to {1}").format(doc.employee_name, emp_email))

    except Exception:
        # Log the error in the 'Error Log' list if it fails
        frappe.log_error(title="Salary Slip Email System Failure", message=frappe.get_traceback())



@frappe.whitelist()
def get_upcoming_holidays_filtered():
    """
    Returns holidays for the next 10 days:
    - Excludes all Sundays.
    - Includes only 1st and 3rd Saturdays.
    - Includes all other non-weekend holidays (Festivals).
    """
    today_date = today()

    holiday_lists = frappe.db.get_value("Holiday List", {"from_date": ["<=", today_date], "to_date": [">=", today_date]}, "name")
    holiday_list_name = holiday_lists
    # print("HHHHHHHHHHHHHHHHHHHHHHHoliday List Name:", holiday_list_name)  # Debugging line
    start_date = today()
    end_date = add_days(start_date, 10)
    # print("Start Date:", start_date, "End Date:", end_date)  # Debugging line
    
    raw_holidays = frappe.get_all(
        "Holiday",
        filters={
            "parent": holiday_list_name,
            "holiday_date": ["between", [start_date, end_date]]
        },
        fields=["holiday_date", "description"],
        order_by="holiday_date asc"
    )

    filtered_list = []

    for h in raw_holidays:
        dt = getdate(h.holiday_date)
        day_of_month = dt.day
        weekday = dt.weekday() # 0=Monday, 5=Saturday, 6=Sunday

        # 1. Strictly Exclude Sunday
        if weekday == 6:
            continue

        # 2. Logic for Saturdays
        if weekday == 5:
            # Calculate which Saturday of the month it is (1st, 2nd, 3rd, etc.)
            week_num = (day_of_month - 1) // 7 + 1
            if week_num in [1, 3]:
                filtered_list.append(h)
            continue # Skip 2nd, 4th, or 5th Saturdays

        # 3. Include all other holidays (Labour Day, Festivals, etc.)
        filtered_list.append(h)

    return filtered_list