import frappe
from frappe.utils import getdate, cint
from calendar import monthrange
import json

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
            if frappe.db.exists("Attendance", {"employee": employee_id, "attendance_date": current_date_str}):
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
        frappe.msgprint(msg, title="Success", indicator="green")

    except Exception as e:
        frappe.log_error("Bulk Attendance Error")
        frappe.throw(str(e))