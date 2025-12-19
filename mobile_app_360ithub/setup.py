import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_migrate():
    """
    Triggered by 'bench migrate'.
    """
    create_custom_fields(get_custom_fields(), ignore_validate=True)

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