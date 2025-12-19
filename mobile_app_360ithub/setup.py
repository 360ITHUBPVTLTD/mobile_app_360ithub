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
    role = "HRMS Employee"
    if not frappe.db.exists("Role", role):
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role,
            "desk_access": 1,
            "is_custom": 1
        }).insert(ignore_permissions=True)

def setup_permissions():
    role = "HRMS Employee"
    
    # Definition of permissions
    perms = [
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
        {
            "doctype": "Task Type", "read": 1, "write": 0, "create": 0},
    ]

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