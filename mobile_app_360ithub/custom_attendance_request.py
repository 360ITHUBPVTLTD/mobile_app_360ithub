import frappe
from hrms.hr.doctype.attendance_request.attendance_request import AttendanceRequest
import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, get_url,format_date, get_time
from datetime import datetime, timedelta




class CustomAttendanceRequest(AttendanceRequest):
    
    # We override ONLY this specific method
    def has_leave_record(self, attendance_date: str) -> str | None:
        """
        Overridden to ignore Half Day leaves. 
        Standard HRMS blocks any request if ANY leave exists. 
        We only want to block if a FULL DAY leave exists.
        """
        if not self.half_day:
            return frappe.db.exists(
                "Leave Application",
                {
                    "employee": self.employee,
                    "docstatus": 1,
                    "from_date": ("<=", attendance_date),
                    "to_date": (">=", attendance_date),
                    "status": "Approved",
                    # This is the change: We only consider it a "blocker" if it is NOT a half day
                    # "half_day": 0 
                },
            )
        
        return frappe.db.exists(
                "Leave Application",
                {
                    "employee": self.employee,
                    "docstatus": 1,
                    "from_date": ("<=", attendance_date),
                    "to_date": (">=", attendance_date),
                    "status": "Approved",
                    # This is the change: We only consider it a "blocker" if it is NOT a half day
                    "half_day": 0 
                },
            )
        
    
    def status_unchanged(self, attendance_date):
        # First, run the standard Frappe check.
        is_unchanged = super().status_unchanged(attendance_date)

        # If the standard check finds the status is the same...
        if is_unchanged:
            attendance_doc = self.get_attendance_doc(attendance_date)
            # Check for our specific edge case:
            # An existing "Half Day" Attendance that has a Leave but is missing an AR.
            if attendance_doc and attendance_doc.status == "Half Day" and attendance_doc.leave_application and not attendance_doc.attendance_request:
                # Tell the system "No, the status IS changing" to force an update.
                return False
        
        # Otherwise, return the original result.
        return is_unchanged

    def create_or_update_attendance(self, date: str):
        if self.custom_status == "Rejected":
            return
        doc = self.get_attendance_doc(date)
        status = self.get_attendance_status(date)

        # If an attendance record already exists...
        if doc:
            old_status = doc.status
            
            # The CORE of the fix: We update if the status is different OR if it's our LA->AR scenario.
            if old_status != status or (old_status == "Half Day" and doc.leave_application and not doc.attendance_request):
                # Use db_set for a safe, direct update.
                

                update_values = {
                    "status": status,
                    "attendance_request": self.name
                }

                # Set half_day_status correctly based on the target status
                if status == "Half Day" :
                    if not doc.leave_application:
                        update_values["half_day_status"] = "Absent"
                        update_values["modify_half_day_status"] = 1
                    else:
                        update_values["half_day_status"] = "Present"

                    
                else:
                    # If it's a Full Day (Present), clear the half-day fields
                    update_values["half_day_status"] = None
                    update_values["modify_half_day_status"] = 0

                # Execute update
                doc.db_set(update_values)
                
                # Add a clear comment for audit trail purposes.
                # text = ("Linked this Attendance Request to the existing Half-Day Leave Application.")
                # doc.add_comment(comment_type="Info", text=text)

                frappe.msgprint(
					("Successfully regularized the remaining half-day for {0}").format(frappe.bold(frappe.utils.format_date(date))),
					title=("Attendance Updated"),
                    indicator="green"
				)
            # If it's a normal update (e.g., Absent -> Present), let the standard logic handle it.
            elif old_status != status:
                 super().create_or_update_attendance(date)

        else:
            # If no attendance record exists, let the standard Frappe method create one.
            super().create_or_update_attendance(date)


    
def validate(doc, method):
    # 1. Strictly enforce single day on the backend
    if doc.from_date:
        doc.to_date = doc.from_date
        if doc.half_day:
            doc.half_day_date = doc.from_date



def before_submit(doc, method):
    # 2. Security Validation: Check who is clicking "Submit" or hitting the API
    current_user = frappe.session.user
    user_roles = frappe.get_roles(current_user)

    # Authorized bypass roles
    privileged_roles = ["Leave Approver", "System Manager", "HR Manager"]
    
    is_approver = (current_user == doc.custom_attendance_request_approver)
    # Checks if any of the privileged roles are present in the user's roles
    is_privileged = any(role in user_roles for role in privileged_roles)

    if not (is_approver or is_privileged):
        frappe.throw(_("Only the assigned Approver, HR Manager, or HR can submit this Attendance Request."))

    # 3. Data Integrity: Ensure custom status is Approved or Rejected
    if doc.custom_status not in ["Approved", "Rejected"]:
        frappe.throw(_("Attendance Request can only be submitted if Status is 'Approved' or 'Rejected'."))

    if not doc.custom_check_in_time or not doc.custom_check_out_time:
        frappe.throw(_("Check-in and Check-out times are mandatory for submission."))

def on_submit(doc, method):
    """
    On submit of Attendance Request:
    - Fetch generated Attendance
    - Create Employee Checkin (IN/OUT)
    - Handle night shift correctly
    """

    if not doc.custom_check_in_time or not doc.custom_check_out_time:
        frappe.throw("Check-in and Check-out time is required")

    fix_checkin_skip_logic(doc)

    # 1. Fetch Attendance created by system
    attendances = frappe.get_all(
        "Attendance",
        filters={
            "attendance_request": doc.name,
            "docstatus": 1
        },
        fields=["name", "attendance_date", "employee"]
    )

    if not attendances:
        # frappe.msgprint("No Attendance records found for this request")
        return

    # 2. Validate input
    

    # 3. Loop through attendance
    for att in attendances:

        # Convert to proper datetime
        in_dt = get_datetime(f"{att.attendance_date} {doc.custom_check_in_time}")
        out_dt = get_datetime(f"{att.attendance_date} {doc.custom_check_out_time}")

        # 4. Night shift logic (FIXED)
        if out_dt <= in_dt:
            out_dt = add_days(out_dt, 1)
        
        in_datetime_str = in_dt.strftime("%Y-%m-%d %H:%M:%S")
        out_datetime_str = out_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Convert back to string
        in_datetime = in_dt.strftime("%Y-%m-%d %H:%M:%S")
        out_datetime = out_dt.strftime("%Y-%m-%d %H:%M:%S")

        # 5. Create IN log
        create_employee_checkin(
            employee=att.employee,
            log_datetime=in_datetime,
            log_type="IN",
            attendance_name=att.name,
            request_name=doc.name
        )

        # 6. Create OUT log
        create_employee_checkin(
            employee=att.employee,
            log_datetime=out_datetime,
            log_type="OUT",
            attendance_name=att.name,
            request_name=doc.name
        )

        working_hours = round((out_dt - in_dt).total_seconds() / 3600.0, 2)
        late_entry = 0
        early_exit = 0
        shift_name = None

        try:
            # Attempt to use HRMS's official shift assignment fetcher
            from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift
            shift_details = get_employee_shift(att.employee, att.attendance_date, True)
            if shift_details:
                shift_name = shift_details.shift_type.name
        except Exception:
            # Robust fallback: Use default shift on Employee master
            shift_name = frappe.db.get_value("Employee", att.employee, "default_shift")

        if shift_name:
            shift = frappe.get_doc("Shift Type", shift_name)
            if not doc.half_day:
                
                # Calculate expected shift datetimes
                expected_in_dt = get_datetime(f"{att.attendance_date} {shift.start_time}")
                expected_out_dt = get_datetime(f"{att.attendance_date} {shift.end_time}")
                
                # Handle night shifts in official shift settings
                if expected_out_dt <= expected_in_dt:
                    expected_out_dt = add_days(expected_out_dt, 1)

                # Late Entry Check
                if shift.enable_late_entry_marking:
                    grace_mins = shift.late_entry_grace_period or 0
                    allowed_in_dt = expected_in_dt + timedelta(minutes=grace_mins)
                    if in_dt > allowed_in_dt:
                        late_entry = 1

                # Early Exit Check
                if shift.enable_early_exit_marking:
                    grace_mins = shift.early_exit_grace_period or 0
                    allowed_out_dt = expected_out_dt - timedelta(minutes=grace_mins)
                    if out_dt < allowed_out_dt:
                        early_exit = 1

        frappe.db.set_value("Attendance", att.name, {
            "in_time": in_datetime_str,
            "out_time": out_datetime_str,
            "working_hours": working_hours,
            "shift": shift_name,
            "late_entry": late_entry,
            "early_exit": early_exit
        })


    

    



def create_employee_checkin(employee, log_datetime, log_type, attendance_name, request_name):
    checkin = frappe.new_doc("Employee Checkin")
    checkin.employee = employee
    checkin.time = log_datetime
    checkin.log_type = log_type
    
    # Link it to the standard Attendance document
    # checkin.attendance = attendance_name
    checkin.device_id = f"Att-Req-{request_name}"
    
    # CRUCIAL: Ensures the nightly auto-attendance cron job skips this completely
    checkin.skip_auto_attendance = 0
    checkin.system_generated = 1
    
    checkin.insert(ignore_permissions=True)

    frappe.db.set_value("Employee Checkin", checkin.name, "attendance", attendance_name)


def on_cancel(doc, method):
    # 5. Cleanup: If HR cancels the request later, delete the custom Check-ins
    linked_checkins = frappe.get_all(
        "Employee Checkin", 
        filters={"device_id": f"Att-Req-{doc.name}"}
    )
    for checkin in linked_checkins:
        frappe.delete_doc("Employee Checkin", checkin.name, ignore_permissions=True)
    att = frappe.get_all("Attendance", filters={ "attendance_request": doc.name},fields = ["name","leave_application"])
    if att and att[0].leave_application:
        leave_linked = frappe.get_all("Leave Application", filters={"docstatus": 1, "name": att[0].leave_application})

        leave_doc = frappe.get_doc("Leave Application", leave_linked[0].name)
        leave_doc.cancel()
        




def fix_checkin_skip_logic(doc):
    """
    Called on_submit of Attendance Request.
    1. Marks Biometric logs as skip_auto_attendance = 1
    2. Marks Request logs as skip_auto_attendance = 0
    """
    if doc.custom_status == "Rejected":
        return
    
    attendance_date = doc.from_date
    
    # 1. Find all biometric logs (system_generated = 0) for this day and SKIP them
    biometric_logs = frappe.get_all("Employee Checkin", filters={
        "employee": doc.employee,
        "time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
        "system_generated": 0 # Biometric
    })
    
    for log in biometric_logs:
        frappe.db.set_value("Employee Checkin", log.name, "skip_auto_attendance", 1)

    # 2. Find logs created by THIS Attendance Request and ensure they are NOT skipped
    # Frappe stores the ARQ name in the 'device_id' field for system logs
    requested_logs = frappe.get_all("Employee Checkin", filters={
        "employee": doc.employee,
        "time": ["between", [f"{attendance_date} 00:00:00", f"{attendance_date} 23:59:59"]],
        "device_id": ["like", f"%{doc.name}%"] 
    })
    
    for log in requested_logs:
        frappe.db.set_value("Employee Checkin", log.name, "skip_auto_attendance", 0)

