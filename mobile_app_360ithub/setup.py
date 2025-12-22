import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_migrate():
    """
    Triggered by 'bench migrate'.
    """
    create_custom_fields(get_custom_fields(), ignore_validate=True)
    setup_roles()
    setup_permissions()


def before_uninstall():
    """
    Triggered when uninstalling the app.
    """
    delete_custom_fields(get_custom_fields())

def get_custom_fields():
    """
    Exact field definitions extracted from Fixtures + Employee Config.
    """
    return {
        "Employee": [
            {
                "fieldname": "attendance_config_section",
                "label": "Attendance Configuration",
                "fieldtype": "Section Break",
                "insert_after": "approvers_section"
            },
            {
                "fieldname": "checkin_method",
                "label": "Check-in Method",
                "fieldtype": "Select",
                "options": "Mobile App\nBiometric",
                "default": "Biometric",
                "insert_after": "attendance_config_section",
                "reqd": "1" 
            },
            {
                "fieldname": "geo_fencing_applicable",
                "label": "Geo Fencing Applicable",
                "fieldtype": "Check",
                "default": "0",
                "insert_after": "checkin_method",
                "depends_on": "eval:doc.checkin_method == 'Mobile App'"
            },
            {
                "fieldname": "custom_anniversary_date",
                "label": "Anniversary Date",
                "fieldtype": "Date",
                "insert_after": "marital_status"
            }
        ],

        "Branch": [
            {
                "fieldname": "custom_latitude",
                "label": "Latitude",
                "fieldtype": "Data",
                "insert_after": "branch",
                "hidden": "0",
                "read_only": "0",
                "is_system_generated": "0"
            },
            {
                "fieldname": "custom_longitude",
                "label": "Longitude",
                "fieldtype": "Data",
                "insert_after": "custom_latitude",
                "hidden": "0",
                "read_only": "0",
                "is_system_generated": "0"
            },
            {
                "fieldname": "custom_radius",
                "label": "Radius (Meters)",
                "fieldtype": "Data",
                "insert_after": "custom_longitude",
                "hidden": "0",
                "read_only": "0",
                "is_system_generated": "0"
            }
        ],

        "Employee Checkin": [
            {
                # Exact name from your JSON
                "fieldname": "custom_custom_lat_long", 
                "label": "Custom Lat Long",
                "fieldtype": "Data",
                "insert_after": "device_id", 
                # Note: Your JSON had 'custom_section_break_wuxlu'. 
                # If that field doesn't exist, this will just appear at the bottom. 
                # I mapped it to 'device_id' to be safe, but the API relies on fieldname, so this is safe.
                "read_only": "1",
                "translatable": "1",
                "is_system_generated": "0"
            },
            {
                "fieldname": "custom_hrms_360ithub",
                "label": "HRMS 360ithub",
                "fieldtype": "Check",
                "insert_after": "custom_custom_lat_long",
                "read_only": "1",
                "is_system_generated": "0"
            }
        ],
        "Attendance": [
            {
                "fieldname": "custom_attendance_note",
                "label": "Attendance Note",
                "fieldtype": "Small Text",
                "insert_after": "status",
                "read_only": "1",
                # "is_system_generated": "0"
            }
        ]
    }

def delete_custom_fields(custom_fields):
    for doctype, fields in custom_fields.items():
        frappe.db.delete(
            "Custom Field",
            {
                "fieldname": ("in", [field["fieldname"] for field in fields]),
                "dt": doctype,
            },
        )
        frappe.clear_cache(doctype=doctype)





def setup_roles():
    roles = ["HRMS Employee", "HRMS HR"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role,
                "desk_access": 1,
                "is_custom": 1
            }).insert(ignore_permissions=True)

def setup_permissions():
    roles = {
    
        # Definition of permissions
        "HRMS Employee":  [
            # 1. Transactions (Create allowed)
            {
                "doctype": "Employee Checkin", 
                "read": 1, "create": 1, "write": 0, 
                "if_owner": 1 # Can only see checkins created by themselves
            },
            {
                "doctype": "Leave Application", 
                "read": 1, "create": 1, "write": 1, 
                "if_owner": 1 # Can only see/edit their own applications
            },
            {
                "doctype": "Comment", 
                "read": 1, "create": 1, "write": 1
            },

            # 2. Read Only Data (Masters & Reports)
            # Note: For Salary Slip & Attendance, we do NOT set if_owner=1
            # because HR creates these, not the employee. 
            # Filtering to "Only their own" is handled by User Permissions.
            {
                "doctype": "Attendance", "read": 1, "write": 0, "create": 0},
            
            {
                "doctype": "Employee", "read": 1, "write": 0, "create": 0},
            
            # 3. Configuration Data
            {
                "doctype": "Branch", "read": 1, "write": 0, "create": 0},
            {
                "doctype": "Holiday List", "read": 1, "write": 0, "create": 0},
            # {
            #     "doctype": "Task Type", "read": 1, "write": 0, "create": 0
            # },
        ],
        "HRMS HR": [
            {"doctype": "Employee", "read": 1, "write": 1, "create": 1},
        {"doctype": "Branch", "read": 1, "write": 1, "create": 1},
        {"doctype": "Department", "read": 1, "write": 1, "create": 1},
        {"doctype": "Designation", "read": 1, "write": 1, "create": 1},
        {"doctype": "Holiday List", "read": 1, "write": 1, "create": 1},
        
        # 2. Attendance & Shifts
        {"doctype": "Employee Checkin", "read": 1, "write": 1, "create": 1},
        {"doctype": "Attendance", "read": 1, "write": 1, "create": 1, "submit": 1},
        {"doctype": "Shift Type", "read": 1, "write": 1, "create": 1},
        {"doctype": "Shift Assignment", "read": 1, "write": 1, "create": 1, "submit": 1},
        
        # 3. Leave Management
        {"doctype": "Leave Application", "read": 1, "write": 1, "create": 1, "submit": 1},
        {"doctype": "Leave Allocation", "read": 1, "write": 1, "create": 1, "submit": 1},
        {"doctype": "Leave Type", "read": 1, "write": 1, "create": 1},
        {"doctype": "Leave Policy", "read": 1, "write": 1, "create": 1},
        {"doctype": "Leave Policy Assignment", "read": 1, "write": 1, "create": 1},
        {"doctype": "Leave Period", "read": 1, "write": 1, "create": 1},
        
        # 4. Payroll (Crucial)
        # {"doctype": "Salary Slip", "read": 1, "write": 1, "create": 1, "submit": 1},
        # {"doctype": "Payroll Entry", "read": 1, "write": 1, "create": 1, "submit": 1},
        # {"doctype": "Salary Structure", "read": 1, "write": 1, "create": 1},
        # {"doctype": "Salary Structure Assignment", "read": 1, "write": 1, "create": 1},
        # {"doctype": "Salary Component", "read": 1, "write": 1, "create": 1},
        
        # 5. General / Utility
        {"doctype": "Comment", "read": 1, "write": 1, "create": 1},
        ]
        }
    for role, perms in roles.items():
        for p in perms:
            add_permission(role, p)

def add_permission(role, p):
    doctype = p["doctype"]
    
    # Check if permission entry exists
    if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
        try:
            # Create the base permission
            frappe.permissions.add_permission(doctype, role, 0)
            
            # Update specific rights
            perm_name = frappe.db.get_value("Custom DocPerm", {"parent": doctype, "role": role})
            if perm_name:
                doc = frappe.get_doc("Custom DocPerm", perm_name)
                doc.read = p.get("read", 0)
                doc.write = p.get("write", 0)
                doc.create = p.get("create", 0)
                doc.submit = p.get("submit", 0)
                doc.cancel = p.get("cancel", 0)
                doc.if_owner = p.get("if_owner", 0)
                doc.save(ignore_permissions=True)
        except Exception:
            pass





# import frappe
# from frappe.utils import getdate
# from calendar import monthrange

# def generate_bulk_attendance(employee_id, year, month, absent_days_list=[]):
#     """
#     employee_id: string (e.g., "HR-EMP-0001")
#     year: int (e.g., 2025)
#     month: int (e.g., 11)
#     absent_days_list: list of integers (e.g., [4, 12, 18])
#     """
    
#     # 1. Get Employee's Holiday List
#     emp_details = frappe.db.get_value("Employee", employee_id, ["holiday_list", "company", "status"], as_dict=True)
    
#     if not emp_details:
#         print(f"❌ Employee {employee_id} not found.")
#         return

#     if emp_details.status != "Active":
#         print(f"⚠️ Warning: Employee {employee_id} is not Active.")

#     # Fetch Holiday Dates as strings
#     holidays = []
#     if emp_details.holiday_list:
#         holidays = frappe.db.get_all("Holiday", 
#             filters={"parent": emp_details.holiday_list}, 
#             pluck="holiday_date"
#         )
#         # Convert dates to string format 'YYYY-MM-DD' for comparison
#         holidays = [str(h) for h in holidays]
#         print(f"ℹ️ Found {len(holidays)} holidays in list: {emp_details.holiday_list}")
#     else:
#         print("⚠️ No Holiday List assigned to Employee. Assuming NO holidays.")

#     # 2. Loop through the month
#     # Get total days in the month (e.g., 28, 30, 31)
#     days_in_month = monthrange(year, month)[1]

#     print(f"\n🚀 Starting Attendance Generation for {employee_id} - {month}/{year}...")

#     created_count = 0

#     for day in range(1, days_in_month + 1):
#         # Format Date: YYYY-MM-DD
#         current_date_obj = getdate(f"{year}-{month:02d}-{day:02d}")
#         current_date_str = str(current_date_obj)

#         # A. Check if Holiday -> SKIP
#         if current_date_str in holidays:
#             print(f"   ⏩ {current_date_str}: Holiday (Skipped)")
#             continue

#         # B. Check if Duplicate -> SKIP
#         # if frappe.db.exists("Attendance", {"employee": employee_id, "attendance_date": current_date_str, "docstatus": 1}):
#         #     print(f"   ⏩ {current_date_str}: Attendance already exists (Skipped)")
#         #     continue

#         # C. Determine Status (Absent vs Present)
#         status = "Absent" if day in absent_days_list else "Present"

#         # D. Create and Submit Attendance
#         try:
#             doc = frappe.get_doc({
#                 "doctype": "Attendance",
#                 "employee": employee_id,
#                 "attendance_date": current_date_str,
#                 "status": status,
#                 "company": emp_details.company,
#                 "docstatus": 1  # 1 = Submitted directly
#             })
#             doc.insert(ignore_permissions=True)
#             print(f"   ✅ {current_date_str}: Marked {status}")
#             created_count += 1
#         except Exception as e:
#             print(f"   ❌ {current_date_str}: Failed - {str(e)}")

#     frappe.db.commit()
#     print(f"\n🎉 Done! Created {created_count} attendance records.")

