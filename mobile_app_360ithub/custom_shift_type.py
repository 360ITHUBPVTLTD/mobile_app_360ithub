import frappe
from frappe.utils import get_time
from datetime import datetime
from hrms.hr.doctype.shift_type.shift_type import ShiftType
from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift

class CustomShiftType(ShiftType):


    def mark_absent_for_half_day_dates(self, employee):
        """
        OVERRIDE: Core Frappe forgets to apply date boundaries to Half-Day absences, 
        causing premature locking mid-shift. We inject the proper end_date boundary here.
        """
        # 1. Get the safe date boundaries that Frappe already calculated
        start_date, end_date = self.get_start_and_end_dates(employee)
        
        # If shift hasn't ended properly yet, abort locking
        if not end_date:
            return

        # 2. Add the `end_date` filter to stop premature locking!
        half_day_attendances = frappe.get_all(
            "Attendance",
            filters={
                "employee": employee, 
                "status": "Half Day", 
                "modify_half_day_status": 1,
                "attendance_date": ("<=", end_date) # THE CRITICAL FIX
            },
            fields=["name", "attendance_date"],
        )
        
        start_time = get_time(self.start_time)
        for attendance in half_day_attendances:
            timestamp = datetime.combine(attendance.attendance_date, start_time)
            shift_details = get_employee_shift(employee, timestamp, True)
            if shift_details and shift_details.shift_type.name == self.name:
                frappe.db.set_value(
                    "Attendance",
                    attendance.name,
                    {"shift": self.name, "half_day_status": "Absent", "modify_half_day_status": 0},
                )
                
                frappe.get_doc(
                    {
                        "doctype": "Comment",
                        "comment_type": "Comment",
                        "reference_doctype": "Attendance",
                        "reference_name": attendance.name,
                        "content": frappe._("Employee was marked Absent for other half due to missing Employee Checkins.")
                    }
                ).insert(ignore_permissions=True)