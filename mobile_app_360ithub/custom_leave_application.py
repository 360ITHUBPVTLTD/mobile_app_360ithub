# File: shantala_chits_360ithub/custom_leave_application.py

import frappe
from frappe import _
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication

class CustomLeaveApplication(LeaveApplication):

    def validate_attendance(self):
        # Do not block cancellation or rejection if attendance already exists
        if self.status in ["Open", "Rejected", "Cancelled"]:
            return
            
        # For all other statuses, run the standard HRMS attendance validation
        super().validate_attendance()

    def create_or_update_attendance(self, attendance_name, date):
        is_half_day_leave = self.half_day_date and frappe.utils.getdate(date) == frappe.utils.getdate(self.half_day_date)
        status = "Half Day" if is_half_day_leave else "On Leave"


        if attendance_name and is_half_day_leave:
            doc = frappe.get_doc("Attendance", attendance_name)

            if doc.status == "Half Day" and doc.leave_application:
                
                first_la_id = doc.leave_application
                first_la_type = doc.leave_type

                comment_text = _(
                    "This day is a full 'On Leave' day composed of two half-day leaves:<br>"
                    "1. First Half: {0} ({1})<br>"
                    "2. Second Half: {2} ({3})"
                ).format(
                    frappe.get_desk_link("Leave Application", first_la_id),
                    first_la_type,
                    frappe.get_desk_link("Leave Application", self.name),
                    self.leave_type
                )
                

                doc.db_set({
                    "status": "On Leave",
                    "leave_type": self.leave_type,
                    "leave_application": self.name,
                    "half_day_status": None,
                    "modify_half_day_status": 0,
                    "custom_attendance_note":comment_text
                })
                
                return # Stop execution here, the merge is complete.
            
        if status == "Half Day":
            if attendance_name:
                doc = frappe.get_doc("Attendance", attendance_name)

                half_day_status = "Absent"
                modify_half_day_status = 1
                if doc.status == "Half Day":
                    half_day_status = "Present"
                    modify_half_day_status = 0

                doc.db_set({
                    "status": status,
                    "leave_type": self.leave_type,
                    "leave_application": self.name,
                    "half_day_status": half_day_status,
                    # CRITICAL FIX: Always force this to 1 so Auto-Attendance evaluates it
                    "modify_half_day_status": modify_half_day_status
                })
            else:
                shift = frappe.db.get_value("Employee", self.employee, "default_shift")
                doc = frappe.new_doc("Attendance")
                doc.employee = self.employee
                doc.attendance_date = date
                doc.company = self.company
                doc.leave_type = self.leave_type
                doc.leave_application = self.name
                doc.status = status
                doc.half_day_status = "Absent" # Default until Auto-Attendance runs
                doc.shift = shift
                # CRITICAL FIX: Always force to 1
                doc.modify_half_day_status = 1 
                
                doc.flags.ignore_validate = True
                doc.insert(ignore_permissions=True)
                doc.submit()

                
                
                
                
        # --- SCENARIO 3: FULL DAY LEAVES ---
        else:
            # Let standard Frappe handle full day leaves
            super().create_or_update_attendance(attendance_name, date)



        # --- SCENARIO 2: A first Half-Day LA or a Full-Day LA (No changes here) ---
        # if status == "Half Day" and not doc.attendance_request:

        #     doc = frappe.new_doc("Attendance")
        #     doc.employee = self.employee
        #     doc.attendance_date = date
        #     doc.company = self.company
        #     doc.leave_type = self.leave_type
        #     doc.leave_application = self.name
        #     doc.status = status
        #     doc.half_day_status = "Absent"
        #     doc.modify_half_day_status = 1
        #     doc.flags.ignore_validate = True
        #     doc.insert(ignore_permissions=True)
        #     doc.submit()
        # else:
            # super().create_or_update_attendance(attendance_name, date)
        # super().create_or_update_attendance(attendance_name, date)