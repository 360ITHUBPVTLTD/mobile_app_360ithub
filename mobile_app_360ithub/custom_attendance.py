import frappe
from frappe.utils import getdate, cint
from calendar import monthrange
import json
from datetime import date,datetime,timedelta


@frappe.whitelist()
def generate_bulk_attendance(employee_id, year, month, absent_days_list=None):
    """
    Robust API to mark monthly attendance.
    Handles string/int inputs gracefully.
    """
    try:
        # ---------------------------------------------
        # 1. Input Sanitization (Handle Client-Side Data)
        # ---------------------------------------------
        
        # Convert Year/Month to int safely
        year = cint(year)
        month = cint(month)
        
        target_absent_days = []

        if absent_days_list:
            # Case A: Passed as a Python List (rare from JS)
            if isinstance(absent_days_list, list):
                target_absent_days = absent_days_list
            
            # Case B: Passed as a String (common from JS)
            elif isinstance(absent_days_list, str):
                absent_days_list = absent_days_list.strip()
                
                # Check if it looks like JSON "[1, 2]"
                if absent_days_list.startswith("["):
                    try:
                        target_absent_days = json.loads(absent_days_list)
                    except:
                        frappe.throw("Invalid JSON format for Absent Days")
                # Assume Comma Separated "1, 5, 20"
                else:
                    target_absent_days = [int(x) for x in absent_days_list.split(",") if x.strip().isdigit()]

        # ---------------------------------------------
        # 2. Validation
        # ---------------------------------------------
        emp_details = frappe.db.get_value("Employee", employee_id, ["holiday_list", "company", "status", "employee_name"], as_dict=True)
        
        if not emp_details:
            frappe.throw(f"Employee {employee_id} not found.")

        # 3. Fetch Holidays
        holidays = []
        if emp_details.holiday_list:
            holidays = frappe.db.get_all("Holiday", 
                filters={"parent": emp_details.holiday_list}, 
                pluck="holiday_date"
            )
            # Convert dates to string format 'YYYY-MM-DD'
            holidays = [str(h) for h in holidays]

        # 4. Generate Records
        days_in_month = monthrange(year, month)[1]
        created_count = 0
        skipped_count = 0

        for day in range(1, days_in_month + 1):
            current_date_obj = getdate(f"{year}-{month:02d}-{day:02d}")
            current_date_str = str(current_date_obj)

            # Skip Holidays
            if current_date_str in holidays:
                continue

            # Skip Duplicates
            if frappe.db.exists("Attendance", {"employee": employee_id, "attendance_date": current_date_str,"docstatus": ["not in", [2]]}):
                skipped_count += 1
                continue

            # Determine Status
            status = "Absent" if day in target_absent_days else "Present"

            # Create Doc
            doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": employee_id,
                "attendance_date": current_date_str,
                "status": status,
                "company": emp_details.company,
                "docstatus": 1  # Submit immediately
            })
            doc.insert(ignore_permissions=True)
            created_count += 1

        # 5. Return Feedback
        msg = f"Generated Attendance for <b>{emp_details.employee_name}</b>.<br>Created: {created_count}<br>Skipped (Existing): {skipped_count}"
        # frappe.msgprint(msg, title="Success", indicator="green")

    except Exception as e:
        frappe.log_error("Bulk Attendance Error")
        frappe.throw(str(e))



@frappe.whitelist()
def erp_last_checkin():
    usr = frappe.session.user
    emp_list = frappe.get_all("Employee", filters={"user_id": usr})
    if not emp_list:
        return {"status": False, "msg": f"No Employee found for {usr} user"}

    checkin_list = frappe.get_all(
        "Employee Checkin",
        filters={"employee": emp_list[0].name},
        fields=["log_type", "time"],
        order_by='time desc',
        limit=1
    )
    if checkin_list:
        return {"status": True, "type": checkin_list[0].log_type, "time": checkin_list[0].time}
    else:
        return {"status": False, "msg": "No Checkin-log found"}




@frappe.whitelist()
def checkin_out_for_missed_logs(day = None, month = None, year = None):
    today = date.today()

    if year and month and day:
        today = date(int(year), int(month), int(day)) 

    day = today.day
    month = today.month
    year = today.year

    from_datetime = datetime(year, month, day, 00, 00, 00)
    to_datetime = datetime(year, month, day, 23, 59, 59)
    
    check_logs= frappe.get_all("Employee Checkin",
                               filters={"time":("between",[from_datetime,to_datetime])},
                               fields=["employee","log_type","name"],
                               order_by="time",
                               )
    emp_checkins={}
    for log in check_logs:

        if log.employee not in emp_checkins:
            emp_checkins[log.employee]=[]
        emp_checkins[log.employee].append(log)

    for emp in emp_checkins:
        if emp_checkins[emp][-1].log_type !="OUT":
            last_in_log=frappe.get_doc("Employee Checkin",emp_checkins[emp][-1].name)
            one_minute = timedelta(minutes=1)
            out_time = last_in_log.time + one_minute

            checkin_doc = frappe.get_doc({
                                        "doctype": "Employee Checkin",
                                        "employee": last_in_log.employee,
                                        "log_type": "OUT",
                                        "time": out_time,
                                        "shift": last_in_log.shift,
                                        # "location":last_in_log.location,
                                        "device_id":"N/A",
                                        "shift_start":last_in_log.shift_start,
                                        "shift_end":last_in_log.shift_end,
                                        "shift_actual_start":last_in_log.shift_actual_start,
                                        "shift_actual_end":last_in_log.shift_actual_end,
                                        "system_generated":1,
                                    })
            checkin_doc.insert()

            frappe.db.commit()



import frappe
from frappe.utils import get_first_day, get_last_day, add_months, today, getdate, add_days

@frappe.whitelist()
def get_employee_ambiguous_attendance():
    # 1. Map session user to Employee
    user = frappe.session.user
    employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
    
    if not employee:
        return {"status": "failed", "message": "No Active Employee profile linked to your user account."}

    # 2. Define Date Range (Start of Last Month to End of Current Month)
    current_date = getdate(today())
    start_date = get_first_day(add_months(current_date, -1))
    end_date = get_last_day(current_date)

    # 3. Bulk Fetch Leaves
    leaves = frappe.get_all("Leave Application",
        filters={
            "employee": employee, 
            "docstatus": ["<", 2], # Not Cancelled/Rejected
            "from_date": ["<=", end_date], 
            "to_date":[">=", start_date]
        },
        fields=["name", "from_date", "to_date", "status", "half_day", "half_day_date"]
    )
    
    leave_map = {}
    for l in leaves:
        d = l.from_date
        while d <= l.to_date:
            leave_map[str(d)] = l
            d = add_days(d, 1)

    # 4. Bulk Fetch Attendances (Only Absent & Half Day)
    attendances = frappe.get_all("Attendance",
        filters={
            "employee": employee, 
            "docstatus": 1, 
            "attendance_date": ["between",[start_date, end_date]], 
            "status": ["in", ["Absent", "Half Day"]]
        },
        fields=["name", "attendance_date", "status", "working_hours"]
    )

    # 5. Bulk Fetch Check-ins
    attendance_names = [a.name for a in attendances]
    checkins_map = {}
    if attendance_names:
        checkins = frappe.get_all("Employee Checkin",
            filters={"attendance": ["in", attendance_names]},
            fields=["attendance", "time", "log_type", "system_generated"],
            order_by="time asc"
        )
        for c in checkins:
            checkins_map.setdefault(c.attendance,[]).append(c)

    # 6. Process Ambiguous Data (The Brains)
    ambiguous_data =[]
    
    for att in attendances:
        att_date_str = str(att.attendance_date)
        leave = leave_map.get(att_date_str)
        chk_ins = checkins_map.get(att.name,[])
        
        reason = ""
        is_ambiguous = False
        
        # PERFECTED HALF DAY & ABSENT LOGIC
        if att.status == "Absent":
            if leave and leave.status == "Approved":
                if leave.half_day and str(leave.half_day_date) == att_date_str:
                    # EDGE CASE: Marked Absent, but only applied for Half Day Leave. 
                    # They still need to regularize the other half!
                    reason = "Absent: Only Half Day Leave is approved. Missing other half."
                    is_ambiguous = True
                else:
                    continue # Full day leave approved, they are fine.
            elif leave and leave.status != "Approved":
                reason = f"Absent: Leave {leave.name} is Pending Approval"
                is_ambiguous = True
            else:
                reason = "Absent: No Leave Applied or Missing Punches"
                is_ambiguous = True

        elif att.status == "Half Day":
            if leave and leave.status == "Approved":
                if leave.half_day and str(leave.half_day_date) == att_date_str:
                    continue # Valid approved half day
                elif not leave.half_day:
                    continue # Full day leave approved, so half day is covered
            elif leave and leave.status != "Approved":
                reason = f"Half Day: Leave {leave.name} is Pending"
                is_ambiguous = True
            else:
                reason = "Half Day Marked without Approved Half Day Leave"
                is_ambiguous = True

        if is_ambiguous:
            # Format checkins for the UI nicely
            formatted_checkins =[]
            for c in chk_ins:
                sys_gen = " (Sys Gen)" if c.get("system_generated") else ""
                time_str = c.time.strftime('%H:%M') if hasattr(c.time, 'strftime') else str(c.time).split(' ')[1][:5]
                formatted_checkins.append(f"{c.log_type} at {time_str}{sys_gen}")

            ambiguous_data.append({
                "date": att_date_str,
                "status": att.status,
                "hours": att.working_hours or 0.0,
                "reason": reason,
                "checkins": formatted_checkins,
                "employee": employee
            })

    # Sort descending (newest first)
    ambiguous_data.sort(key=lambda x: x["date"], reverse=True)

    return {"status": "success", "data": ambiguous_data, "employee": employee}

import frappe
from frappe import _

def auto_present_logic(doc, method):
    # 1. Fetch values
    settings = frappe.get_single("Mobile App Admin Settings")
    auto_mark = settings.auto_mark_attendance
    target_shift = settings.shift_type 

    # 2. Logic: Must be auto-mark enabled, shifts must match, and current status must be Absent
    if auto_mark and doc.shift == target_shift and doc.status == "Absent":
        
        # 3. Check for Leave Application
        leave_exists = frappe.db.exists("Leave Application", {
            "employee": doc.employee,
            "docstatus": 1,
            "status": "Approved",
            "from_date": ["<=", doc.attendance_date],
            "to_date": [">=", doc.attendance_date],
        })

        if not leave_exists:
            # Change Status
            doc.status = "Present"
            
            # 4. INSERT COMMENT MANUALLY (More reliable in before_submit)
            comment_text = _("Attendance automatically updated to <b>Present</b> as per Clarity Admin Settings.")
            
            # Using manual insert to ensure it stays in the Timeline
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Comment",
                "reference_doctype": "Attendance",
                "reference_name": doc.name,
                "content": comment_text,
                "comment_by": frappe.session.user
            }).insert(ignore_permissions=True)

            # 5. Alert the user on screen so you KNOW the code worked
            frappe.msgprint(_("Auto-Present Policy applied for {0}").format(doc.employee), alert=True)

        else:
            # If Leave is found, we can add a comment explaining why it was NOT marked present
            leave_note = _("System: Kept as Absent/Leave because an Approved Leave Application was found.")
            
            frappe.get_doc({
                "doctype": "Comment",
                "comment_type": "Comment",
                "reference_doctype": "Attendance",
                "reference_name": doc.name,
                "content": leave_note,
                "comment_by": frappe.session.user
            }).insert(ignore_permissions=True)





# import frappe
# from frappe import _
# from frappe.utils import today, getdate, add_days, get_datetime, now_datetime

# def is_date_a_holiday(employee, process_date):
#     """Checks if a date is a holiday or before joining."""
#     emp_details = frappe.db.get_value("Employee", employee, 
#         ["holiday_list", "company", "date_of_joining"], as_dict=True)
    
#     if not emp_details: return False
#     if emp_details.date_of_joining and getdate(process_date) < getdate(emp_details.date_of_joining):
#         return True # Skip
        
#     h_list = emp_details.holiday_list or frappe.db.get_value("Company", emp_details.company, "default_holiday_list")
#     if not h_list: return False

#     return frappe.db.exists("Holiday", {"parent": h_list, "holiday_date": process_date})

# def run_daily_auto_attendance():
#     settings = frappe.get_single("Clarity Admin Settings")
#     if not settings.auto_mark_attendance or not settings.shift_type:
#         return

#     shift_name = settings.shift_type
#     start_date = getattr(settings, "attendance_start_date", None) or add_days(today(), -60) 
#     curr_date = getdate(start_date)
#     end_date = getdate(today())

#     while curr_date <= end_date:
#         process_single_date(curr_date, shift_name)
#         curr_date = add_days(curr_date, 1)

# def process_single_date(process_date, shift_name):
#     # 1. Threshold Check for Today
#     if getdate(process_date) == getdate(today()):
#         process_after = frappe.db.get_value("Shift Type", shift_name, "process_attendance_after")
#         if process_after:
#             threshold_dt = get_datetime(f"{process_date} {process_after}").replace(tzinfo=None)
#             if now_datetime().replace(tzinfo=None) < threshold_dt:
#                 return 

#     # 2. Fetch Active Employees
#     employees = frappe.get_all("Employee", filters={"status": "Active", "default_shift": shift_name}, fields=["name"])

#     for emp in employees:
#         # A. Holiday Check
#         if is_date_a_holiday(emp.name, process_date):
#             continue
            
#         # B. Check for existing attendance
#         if frappe.db.exists("Attendance", {"employee": emp.name, "attendance_date": process_date, "docstatus": ["<", 2]}):
#             continue

#         # C. Check for Approved Leave Application
#         leave_app = frappe.get_value("Leave Application", {
#             "employee": emp.name, 
#             "docstatus": 1, 
#             "status": "Approved",
#             "from_date": ["<=", process_date], 
#             "to_date": [">=", process_date]
#         }, ["name", "leave_type", "half_day"], as_dict=True)

#         # D. Determine Status and Create Record
#         try:
#             status = "Present"
#             leave_application = None
            
#             if leave_app:
#                 # If leave exists, status is "On Leave" (or "Half Day" if checked)
#                 status = "Half Day" if leave_app.half_day else "On Leave"
#                 leave_application = leave_app.name

#             doc = frappe.get_doc({
#                 "doctype": "Attendance",
#                 "employee": emp.name,
#                 "attendance_date": process_date,
#                 "status": status,
#                 "leave_application": leave_application,
#                 "shift": shift_name,
#                 "remarks": _("Auto-generated Attendance record.")
#             })
#             doc.flags.ignore_permissions = True
#             doc.insert()
#             doc.submit()
#         except Exception:
#             frappe.log_error(frappe.get_traceback(), _("Auto Attendance Error"))






import frappe
from frappe import _
from frappe.utils import today, getdate, add_days, get_datetime, now_datetime

def is_date_a_holiday(employee, process_date):
    """Checks if a date is a holiday or before joining."""
    emp_details = frappe.db.get_value("Employee", employee, 
        ["holiday_list", "company", "date_of_joining"], as_dict=True)
    
    if not emp_details: return False
    if emp_details.date_of_joining and getdate(process_date) < getdate(emp_details.date_of_joining):
        return True # Skip
        
    h_list = emp_details.holiday_list or frappe.db.get_value("Company", emp_details.company, "default_holiday_list")
    if not h_list: return False

    return frappe.db.exists("Holiday", {"parent": h_list, "holiday_date": process_date})

def run_daily_auto_attendance():
    settings = frappe.get_single("Mobile App Admin Settings")
    if not settings.auto_mark_attendance or not settings.shift_type:
        return

    shift_name = settings.shift_type
    start_date = getattr(settings, "attendance_start_date", None) or add_days(today(), -60) 
    curr_date = getdate(start_date)
    end_date = getdate(today())

    while curr_date <= end_date:
        process_single_date(curr_date, shift_name)
        curr_date = add_days(curr_date, 1)

def process_single_date(process_date, shift_name):
    # 1. Threshold Check for Today
    if getdate(process_date) == getdate(today()):
        process_after = frappe.db.get_value("Shift Type", shift_name, "process_attendance_after")
        if process_after:
            threshold_dt = get_datetime(f"{process_date} {process_after}").replace(tzinfo=None)
            if now_datetime().replace(tzinfo=None) < threshold_dt:
                return 

    # 2. Fetch Active Employees
    employees = frappe.get_all("Employee", filters={"status": "Active", "default_shift": shift_name}, fields=["name"])

    for emp in employees:
        # A. Holiday Check
        if is_date_a_holiday(emp.name, process_date):
            continue
            
        # B. Skip if Attendance already exists
        if frappe.db.exists("Attendance", {"employee": emp.name, "attendance_date": process_date, "docstatus": ["<", 2]}):
            continue

        # C. Check for Approved Leave Application
        leave_app = frappe.get_value("Leave Application", {
            "employee": emp.name, 
            "docstatus": 1, 
            "status": "Approved",
            "from_date": ["<=", process_date], 
            "to_date": [">=", process_date]
        }, ["name", "half_day"], as_dict=True)

        # D. Determine Attendance Values
        try:
            status = "Present"
            half_day = 0
            half_day_status = ""
            leave_application = None
            
            if leave_app:
                leave_application = leave_app.name
                if leave_app.half_day:
                    # Specific requirement: If half day leave, status is Half Day and other half is Present
                    status = "Half Day"
                    half_day = 1
                    half_day_status = "Present"
                else:
                    status = "On Leave"
                    half_day = 0

            # E. Create Attendance
            doc = frappe.get_doc({
                "doctype": "Attendance",
                "employee": emp.name,
                "attendance_date": process_date,
                "status": status,
                "half_day": half_day,
                "half_day_status": half_day_status,
                "leave_application": leave_application,
                "shift": shift_name,
                "remarks": _("Auto-marked via Clarity Logic")
            })
            doc.flags.ignore_permissions = True
            doc.insert()
            doc.submit()
            
        except Exception:
            frappe.log_error(frappe.get_traceback(), _("Auto Attendance Error"))