import frappe
import json
import requests
from frappe.utils import now_datetime, today, getdate




def checkin_before_insert(doc, method):
    try:
        emp_checkin_method = frappe.db.get_value("Employee", doc.employee, "checkin_method")
        if doc.system_generated == 1:
            pass
        elif emp_checkin_method == "Mobile App":
            if doc.device_id:
                frappe.throw(("You are allowed to checkin using Mobile App only."))
            elif not doc.custom_custom_lat_long:
                frappe.throw(("Latitude and Longitude is required for login via Mobile App."))
        elif emp_checkin_method == "Biometric":
            if doc.custom_hrms_360ithub:
                frappe.throw(("You are allowed to checkin using Biometric only."))
            elif not doc.device_id:
                frappe.throw(("Device ID is required."))
            
    except Exception as e:
        frappe.log_error(message=str(e), title="Error in checkin_before_insert")
        frappe.throw(("Failed to get method {0} with {1}").format(method, e))



@frappe.whitelist(allow_guest=True)
def biometric_login(**kwargs):
    """
    Biometric Device Endpoint.
    Maintains strict response format for hardware compatibility.
    Logs activity to 'Integration Request'.
    """
    
    # 1. Capture Raw Data
    # We prioritize capturing the data before logic runs.
    raw_data = frappe.form_dict
    frappe.log_error(title="Raw Data", message=raw_data)


    # 2. Create Audit Log (Status: Queued)
    log = create_integration_log(raw_data)
    
    try:
        # ---------------------------------------
        # VALIDATION: Missing Code
        # ---------------------------------------
        
        employee_code = raw_data.get("employee_code")
        if not employee_code:
            msg = "Employee code missing"
            update_log(log, "Failed", output={"message": msg})
            return {"status": False, "message": msg}

        # ---------------------------------------
        # LOGIC: Find Employee
        # ---------------------------------------
        employee, status = frappe.db.get_value(
            "Employee", 
            {"attendance_device_id": employee_code}, 
            ["name", "status"]
        ) or (None, None)

        if not employee:
            msg = "Employee not found"
            update_log(log, "Failed", output={"message": msg})
            return {"status": False, "message": msg}

        if status != "Active":
            msg = "Employee is not active"
            update_log(log, "Failed", output={"message": msg})
            return {"status": False, "message": msg}

        # ---------------------------------------
        # LOGIC: Determine IN/OUT & Time
        # ---------------------------------------
        # Use provided time or current server time
        log_dt = raw_data.get("log_datetime") or now_datetime()

        if frappe.db.exists("Employee Checkin", {
            "employee": employee,
            "time": log_dt,
            "system_generated": 0
        }):
            msg = f"Duplicate skipped for {employee} at {log_dt}"
            update_log(log, "Completed", output={"message": msg, "duplicate": True})
            return {"status": True, "message": msg} # Return True so hardware stops retrying
        
        # Smart toggle logic (Safe against yesterday's missed punches)
        new_log_type = calculate_log_type(employee, log_dt)

        # ---------------------------------------
        # ACTION: Create Check-in
        # ---------------------------------------
        checkin = frappe.get_doc({
            "doctype": "Employee Checkin",
            "employee": employee,
            "log_type": new_log_type,
            "time": log_dt,
            "device_id": raw_data.get("device_id","ID Not Provided"),
            "device_name": raw_data.get("device_name","Name Not Provided"),
            "skip_auto_attendance": 0
        })
        checkin.insert(ignore_permissions=True)
        update_shift_last_sync(employee)
        # ---------------------------------------
        # SUCCESS RESPONSE (Strict Format)
        # ---------------------------------------
        # Link Log to the Document
        log.reference_doctype = "Employee Checkin"
        log.reference_docname = checkin.name
        
        response_payload = {
            "status": True,
            "message": f"Check-in created ({new_log_type})",
            "employee": employee,
            "log_type": new_log_type,
            "time": log_dt
        }
        
        update_log(log, "Completed", output=response_payload)

        return response_payload

    except Exception as e:
        # ---------------------------------------
        # ERROR RESPONSE
        # ---------------------------------------
        traceback = frappe.get_traceback()
        update_log(log, "Failed", error=traceback)
        
        # Return generic error to device, detailed error is in Integration Request
        return {"status": False, "message": "Failed to create check-in"}


def update_shift_last_sync(employee_name):
    # Fetch the employee record
    employee = frappe.db.get_value("Employee", employee_name, "default_shift")

    if employee:  # Check if the employee has a default shift
        frappe.db.set_value(
            "Shift Type",
            employee,
            "last_sync_of_checkin",
            now_datetime(),
        )

# --- Helper Functions ---

def create_integration_log(data):
    """Creates a new Integration Request record for audit."""
    try:
        doc = frappe.new_doc("Integration Request")
        doc.integration_request_service = "Biometric Webhook"
        doc.is_remote_request = 1
        doc.status = "Queued"
        doc.data = frappe.as_json(data)
        doc.save(ignore_permissions=True)
        frappe.db.commit() 
        return doc
    except Exception:
        return None

def update_log(doc, status, output=None, error=None):
    """Updates the log with final status."""
    if not doc: return
    
    doc.status = status
    if output:
        doc.output = frappe.as_json(output)
    if error:
        doc.error = error
        
    doc.save(ignore_permissions=True)
    frappe.db.commit()

# def calculate_log_type(employee):
#     """Smart calculation for IN/OUT based on TODAY's activity."""
#     last_log = frappe.db.get_value(
#         "Employee Checkin",
#         {
#             "employee": employee,
#             "time": [">=", f"{today()} 00:00:00"] # Reset logic every midnight
#         },
#         "log_type",
#         order_by="time DESC"
#     )
#     if not last_log:
#         return "IN" # First punch of the day is IN
#     return "OUT" if last_log == "IN" else "IN"

def calculate_log_type(employee, log_dt):
    """Smart calculation for IN/OUT based on TODAY's activity."""
    log_date = getdate(log_dt)
    last_log = frappe.db.get_value(
        "Employee Checkin",
        {
            "employee": employee,
            "time": ["between", [f"{log_date} 00:00:00", log_dt]],  # Reset logic every midnight
        },
        "log_type",
        order_by="time DESC"
    )
    if not last_log:
        return "IN" # First punch of the day is IN
    return "OUT" if last_log == "IN" else "IN"

















# @frappe.whitelist(allow_guest=True)
# def biomentric_login(employee_code=None, employee_name=None, log_datetime=None,
#                      log_date=None, log_time=None, downloaded_at=None,
#                      device_sn=None, device_name=None, device_no=None):


#     # -------------------------------
#     # 1. Parse JSON Body
#     # -------------------------------
#     try:
#         body_data = json.loads(frappe.request.data) if frappe.request.data else {}
#     except Exception as e:
#         frappe.log_error(title="Biometric Error - Invalid JSON", message=f"{frappe.request.data}\n{frappe.get_traceback()}")
#         body_data = {}

#     # -------------------------------
#     # 2. Query Params
#     # -------------------------------
#     query_data = {
#         "employee_code": employee_code,
#         "log_datetime": log_datetime,
#         "log_time": log_time,
#         "downloaded_at": downloaded_at,
#         "device_sn": device_sn,
#         "device_no": device_no,
#         "device_name": device_name,
#     }

#     # Merge body + query (body wins)
#     final_data = {**query_data, **body_data}
#     final_data = {k: v for k, v in final_data.items() if v not in [None, "", "null"]}

#     frappe.log_error("Biometric Login Received", frappe.as_json(final_data))

#     # =====================================================
#     # NEGATIVE CASE 1: employee_code missing
#     # =====================================================
#     if not final_data.get("employee_code"):
#         frappe.log_error(
#             "Biometric Error - Missing Employee Code",
#             frappe.as_json(final_data)
#         )
#         return {"status": "failed", "message": "Employee code missing"}

#     # =====================================================
#     # 3. Find Employee by attendance_device_id
#     # =====================================================
#     emp, status = frappe.db.get_value(
#         "Employee",
#         {"attendance_device_id": final_data.get("employee_code")},
#         ["name", "status"],
#         as_dict=False,
#     ) or (None, None)

#     # NEGATIVE CASE 2: No employee found
#     if not emp:
#         frappe.log_error(
#             "Biometric Error - Employee Not Found",
#             f"Employee Code: {final_data.get('employee_code')}"
#         )
#         return {"status": "failed", "message": "Employee not found"}

#     # NEGATIVE CASE 3: Employee not Active
#     if status != "Active":
#         frappe.log_error(
#             "Biometric Error - Employee Not Active",
#             f"Employee: {emp}, Status: {status}"
#         )
#         return {"status": "failed", "message": "Employee is not active"}

#     # =====================================================
#     # 4. Determine Log Datetime
#     # =====================================================
#     log_dt = final_data.get("log_datetime") or now_datetime()

#     # =====================================================
#     # 5. Get Last Checkin → Determine IN/OUT
#     # =====================================================
#     last_log_type = frappe.db.get_value(
#         "Employee Checkin",
#         {"employee": emp},
#         "log_type",
#         order_by="time DESC"
#     )

#     new_log_type = "OUT" if last_log_type == "IN" else "IN"

#     # =====================================================
#     # 6. Create Employee Checkin
#     # =====================================================
#     try:
#         checkin = frappe.get_doc({
#             "doctype": "Employee Checkin",
#             "employee": emp,
#             "log_type": new_log_type,
#             "time": log_dt,
#             "device_id": final_data.get("device_no")
#         })
#         checkin.insert(ignore_permissions=True)
#         frappe.db.commit()

        # return {
        #     "status": "success",
        #     "message": f"Check-in created ({new_log_type})",
        #     "employee": emp,
        #     "log_type": new_log_type,
        #     "time": log_dt
        # }

#     except Exception as e:
#         frappe.log_error(
#             "Biometric Checkin Error - Insert Failed",
#             frappe.get_traceback()
#         )
#         return {"status": "error", "message": "Failed to create check-in"}


def checkin_after_insert(doc, method=None):
    """
    Triggers after a new Employee Checkin is inserted.
    Passes employee, log_type and time directly to the background job
    to avoid DoesNotExistError from uncommitted DB transactions.
    """
    try:
        frappe.enqueue(
            "mobile_app_360ithub.custom_employee_checkin.run_late_coming_whatsapp_notification",
            employee=doc.employee,
            log_type=doc.log_type,
            checkin_time=str(doc.time),
            queue="short",
            timeout=300
        )
    except Exception as e:
        frappe.log_error(title="Late Checkin WhatsApp Enqueue Error", message=frappe.get_traceback())


def run_late_coming_whatsapp_notification(employee, log_type, checkin_time):
    """
    Runs in background worker with data passed directly (no DB fetch needed).
    """
    try:
        from frappe.model.document import Document
        # Build a minimal mock doc with required fields
        doc = frappe._dict({
            "employee": employee,
            "log_type": log_type,
            "time": checkin_time,
        })
        send_late_coming_whatsapp_notification(doc)
    except Exception as e:
        frappe.log_error(title="Late Checkin WhatsApp Error", message=frappe.get_traceback())


def send_late_coming_whatsapp_notification(doc):
    from datetime import timedelta, datetime, time
    from frappe.utils import get_datetime, getdate, now_datetime

    # 0. Check if WhatsApp late check-in notifications are enabled in Mobile App Admin Settings
    settings = frappe.get_single("Mobile App Admin Settings")
    if not settings.get("custom_enable_late_checkin_whatsapp"):
        return  # Feature is disabled — do nothing

    # 1. Validate that the check-in is an IN punch
    if doc.log_type != "IN":
        return

    # 2. Check if check-in time date is equal to the current server date (same-day check)
    checkin_time = get_datetime(doc.time)
    current_time = now_datetime()
    if getdate(checkin_time) != getdate(current_time):
        return

    # 3. Retrieve employee shift details
    from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift
    shift_details = get_employee_shift(doc.employee, checkin_time, consider_default_shift=True)
    if not shift_details:
        return

    shift_start = shift_details.get("start_datetime")
    if not shift_start:
        return

    # 4. If the shift type is "No Punch Needed", do not send a notification
    shift_type_name = shift_details.get("shift_type", {}).get("name")
    if shift_type_name == "No Punch Needed":
        return

    # 5. Calculate late threshold (shift start + 15 min grace)
    #    No upper bound — any first late check-in after grace period will trigger the notification
    grace_period_mins = 15
    late_threshold = shift_start + timedelta(minutes=grace_period_mins)

    # 6. Trigger only if check-in is after the late threshold
    if checkin_time > late_threshold:
        today_str = checkin_time.date().strftime("%Y-%m-%d")

        # 6a. Only fire on the FIRST IN punch of the day for this employee.
        #     Query for any IN punch with time strictly BEFORE the current check-in time.
        #     Using raw SQL avoids the doc.name=None issue in background jobs.
        earlier_checkin_count = frappe.db.sql("""
            SELECT COUNT(*) FROM `tabEmployee Checkin`
            WHERE employee = %s
              AND log_type = 'IN'
              AND DATE(time) = %s
              AND time < %s
        """, (doc.employee, today_str, checkin_time.strftime("%Y-%m-%d %H:%M:%S")))[0][0]

        if earlier_checkin_count > 0:
            return  # Not the first check-in of the day — skip notification

        # 6b. Skip if employee has an approved leave covering today AND is checking in after 12:00 PM.
        #     This handles half-day / afternoon leaves — they are legitimately coming in after lunch.
        if checkin_time.hour >= 12:
            approved_leave = frappe.db.exists(
                "Leave Application",
                {
                    "employee": doc.employee,
                    "status": "Approved",
                    "docstatus": 1,
                    "from_date": ["<=", today_str],
                    "to_date": [">=", today_str],
                }
            )
            if approved_leave:
                return  # Employee has an approved leave today and is returning after lunch — skip
        # Calculate late duration in hours and minutes
        diff = checkin_time - shift_start
        total_minutes = int(diff.total_seconds() // 60)
        hours = total_minutes // 60
        minutes = total_minutes % 60

        hour_str = "hour" if hours == 1 else "hours"
        minute_str = "minute" if minutes == 1 else "minutes"
        if hours > 0:
            late_time_str = f"{hours} {hour_str} and {minutes} {minute_str}"
        else:
            late_time_str = f"{minutes} {minute_str}"

        # 7. Get employee details
        employee_doc = frappe.get_doc("Employee", doc.employee)
        employee_name = employee_doc.employee_name or doc.employee
        mobile_number = employee_doc.cell_number

        # Clean mobile number to exactly 10 digits
        if mobile_number:
            cleaned_number = "".join(c for c in str(mobile_number) if c.isdigit())
            if len(cleaned_number) == 12 and cleaned_number.startswith("91"):
                cleaned_number = cleaned_number[-10:]
            elif len(cleaned_number) == 11 and cleaned_number.startswith("0"):
                cleaned_number = cleaned_number[-10:]
            
            if len(cleaned_number) == 10:
                mobile_number = cleaned_number
            else:
                frappe.log_error(
                    title="WhatsApp Notification Skip",
                    message=f"Invalid mobile number format for employee {doc.employee}: {mobile_number}"
                )
                return
        else:
            frappe.log_error(
                title="WhatsApp Notification Skip",
                message=f"No mobile number found for employee {doc.employee}"
            )
            return

        # 8. Fetch WhatsApp instance details directly.
        # We fetch by name 'dac' directly to avoid dependency on 'default'/'active' flags
        # which get reset by the sync_instance_data function periodically.
        # Fallback: pick any available instance if 'dac' is not found.
        wa_instances = frappe.get_all(
            'WhatsApp Instance',
            fields=['name', 'base_url', 'instance_id'],
            limit=10
        )
        if not wa_instances:
            frappe.log_error(
                title="WhatsApp Notification Error",
                message="No WhatsApp Instance configured in the system."
            )
            return

        # Prefer instance named 'dac', otherwise use first available
        instance = next((i for i in wa_instances if i['name'] == 'dac'), wa_instances[0])
        base_url = instance['base_url']
        instance_id = instance['instance_id']

        # 9. Prepare message
        message = (
            f"Dear {employee_name},\n\n"
            f"This is to inform you that you checked in late today at {checkin_time.strftime('%I:%M %p')} (Shift start: {shift_start.strftime('%I:%M %p')}). You are late by {late_time_str}.\n\n"
            f"Please maintain punctuality.\n\n"
            f"Regards,\n"
            f"HR Department,\nDac's Inc."
        )

        # 10. Send WhatsApp message directly via API with 60-second timeout.
        # We bypass send_custom_whatsapp_message() from webtoolex_whatsapp because it
        # uses a hardcoded 15-second timeout in make_api_request(). The Vision360 API
        # sometimes takes longer than 15s to respond, causing a ReadTimeout error.
        # By calling requests.post() directly here with timeout=60, we give it enough time.
        url = base_url + "sendText"
        params = {
            "token": instance_id,
            "phone": f"91{mobile_number}",
            "message": message,
        }

        try:
            response = requests.post(url, params=params, timeout=60)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('status') == 'success':
                frappe.logger().info(
                    f"Late check-in WhatsApp sent to {employee_name} ({mobile_number})"
                )
            else:
                frappe.log_error(
                    title="WhatsApp Sending Failed",
                    message=f"API returned non-success for {employee_name} ({mobile_number}): {response_data}"
                )
        except requests.exceptions.RequestException as e:
            frappe.log_error(
                title="WhatsApp Sending Failed",
                message=f"Failed to send late coming notification to {employee_name} ({mobile_number}): {e}"
            )
