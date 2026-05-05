import frappe
import json
from frappe.utils import now_datetime, today



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
        
        # Smart toggle logic (Safe against yesterday's missed punches)
        new_log_type = calculate_log_type(employee)

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

def calculate_log_type(employee):
    """Smart calculation for IN/OUT based on TODAY's activity."""
    last_log = frappe.db.get_value(
        "Employee Checkin",
        {
            "employee": employee,
            "time": [">=", f"{today()} 00:00:00"] # Reset logic every midnight
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
