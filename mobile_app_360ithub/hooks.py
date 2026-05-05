app_name = "mobile_app_360ithub"
app_title = "Mobile App 360Ithub"
app_publisher = "pankaj@360ithub.com"
app_description = "Mobile App 360ithub"
app_email = "pankaj@360ithub.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mobile_app_360ithub",
# 		"logo": "/assets/mobile_app_360ithub/logo.png",
# 		"title": "Mobile App 360Ithub",
# 		"route": "/mobile_app_360ithub",
# 		"has_permission": "mobile_app_360ithub.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mobile_app_360ithub/css/mobile_app_360ithub.css"
# app_include_js = "/assets/mobile_app_360ithub/js/mobile_app_360ithub.js"

# include js, css files in header of web template
# web_include_css = "/assets/mobile_app_360ithub/css/mobile_app_360ithub.css"
# web_include_js = "/assets/mobile_app_360ithub/js/mobile_app_360ithub.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mobile_app_360ithub/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mobile_app_360ithub/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mobile_app_360ithub.utils.jinja_methods",
# 	"filters": "mobile_app_360ithub.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mobile_app_360ithub.install.before_install"
# after_install = "mobile_app_360ithub.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mobile_app_360ithub.uninstall.before_uninstall"
# after_uninstall = "mobile_app_360ithub.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mobile_app_360ithub.utils.before_app_install"
# after_app_install = "mobile_app_360ithub.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mobile_app_360ithub.utils.before_app_uninstall"
# after_app_uninstall = "mobile_app_360ithub.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mobile_app_360ithub.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Employee Checkin": {
        "before_insert": "mobile_app_360ithub.custom_employee_checkin.checkin_before_insert",
    },
    "Attendance": {
        "before_submit": "mobile_app_360ithub.custom_attendance.auto_present_logic"
    },
    "Employee": {
        "before_save": "mobile_app_360ithub.custom_employee.before_save_employee",
    },
   
 	"Comment": {
 		"after_insert": "mobile_app_360ithub.task_comments.publish_task_comment_event",
		"on_trash": "mobile_app_360ithub.task_comments.delete_task_comment_event"
 	},
    "Task": {
        "after_insert": "mobile_app_360ithub.task_hooks.task_after_insert",
        "before_save": "mobile_app_360ithub.task_hooks.task_before_save",
        "on_update": "mobile_app_360ithub.fcm_notification.send_task_notification"
    },
    "Leave Application": {
        "after_insert": "mobile_app_360ithub.fcm_notification.send_leave_notification",
        "on_submit": "mobile_app_360ithub.fcm_notification.notify_employee_on_finish",
        "before_submit": "mobile_app_360ithub.custom_employee.validate_leave_approver_on_submit",
        # "on_update": "mobile_app_360ithub.fcm_notification.notify_employee_on_finish" 
    },
    "Expense Claim": {
        "after_insert": "mobile_app_360ithub.fcm_notification.send_expense_notification",
        "on_submit": "mobile_app_360ithub.fcm_notification.notify_employee_on_expense_finish",
        "before_insert": "mobile_app_360ithub.custom_expense_claim.before_insert_expense_claim",
        # "on_update": "mobile_app_360ithub.fcm_notification.notify_employee_on_expense_finish"
    },
    "Event Activity": {
        "after_insert": "mobile_app_360ithub.fcm_notification.send_activity_creation_notification"
    },
     "Attendance Request": {
        # "on_submit": "mobile_app_360ithub.custom_hr.fix_checkin_skip_logic",
        # "before_validate": "mobile_app_360ithub.custom_hr.clear_attendance_request_conflict",
        "validate": "mobile_app_360ithub.custom_attendance_request.validate",
        "before_submit": "mobile_app_360ithub.custom_attendance_request.before_submit",
        "on_submit": "mobile_app_360ithub.custom_attendance_request.on_submit",
        "on_cancel": "mobile_app_360ithub.custom_attendance_request.on_cancel",
        "on_update": "mobile_app_360ithub.custom_hr.auto_submit_on_approval",
        "validate": [
            "mobile_app_360ithub.custom_hr.validate_approver_authority"
        ],
        # "after_insert": "mobile_app_360ithub.custom_hr.handle_arq_email_triggers"
    },
  
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"mobile_app_360ithub.tasks.all"
# 	],
# 	"daily": [
# 		"mobile_app_360ithub.tasks.daily"
# 	],
# 	"hourly": [
# 		"mobile_app_360ithub.tasks.hourly"
# 	],
# 	"weekly": [
# 		"mobile_app_360ithub.tasks.weekly"
# 	],
# 	"monthly": [
# 		"mobile_app_360ithub.tasks.monthly"
# 	],
# }
scheduler_events = {
    "cron": {
        "0 9 * * *": [
            "mobile_app_360ithub.fcm_notification.send_daily_task_summary"
        ],
        "15 9 * * *": [
            "mobile_app_360ithub.fcm_notification.send_daily_activity_summary"
        ],
        "00 23 * * *":
            [
            "mobile_app_360ithub.custom_attendance.checkin_out_for_missed_logs"
            ],
        "30 23 * * *": [
            "mobile_app_360ithub.custom_attendance.run_daily_auto_attendance"
        ]
    },
    "daily": [
		"mobile_app_360ithub.custom_task.daily_overdue_status_update",
        # "clarity_360ithub.custom_hr.mark_management_attendance"
	],
}



# Testing
# -------

# before_tests = "mobile_app_360ithub.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mobile_app_360ithub.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mobile_app_360ithub.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mobile_app_360ithub.utils.before_request"]
# after_request = ["mobile_app_360ithub.utils.after_request"]

# Job Events
# ----------
# before_job = ["mobile_app_360ithub.utils.before_job"]
# after_job = ["mobile_app_360ithub.utils.after_job"]

custom_html_blocks_dashboard = [
    "Month Brithday",
    "HTML for checkin",
    "Today Team Presence",
    "Approved Leaves HR",
    "Pending Leave Applications HR",
    "Absent Table HR",
    "Absent Table Employee",
    "Pending Leave Applications Employee",
    "Approved Leaves Employee",
    "Absent Table Employee 13mar",
    "Pending Leave Applications Employee 13 mar",
    "Approved Leaves Employee 13mar",
    "Absent Table HR 13mar",
    "Pending / To-Approve On-Duty",
    "Pending Employee OT"
        

]


fixtures = [
    {
        "dt": "Custom HTML Block", 
        "filters": [["name", "in", custom_html_blocks_dashboard]]
    },
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "fieldname", "in", [
                    # Task
                    "task_owner",
                    # Lead
                    "custom_address",
                    # Branch
                    "custom_latitude", "custom_longitude", "custom_radius",
                    # Employee Checkin
                    "custom_custom_lat_long", "custom_hrms_360ithub",
                    # Event
                    "custom_actual_visit_date_time", "custom_location",
                    "custom_actual_checked_out_at", "custom_checkout_notes",
                    "custom_visit_address", "custom_allocated_to"
                    # Customer
                    "custom_address"
                ]
            ]
        ]
    }
]




# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mobile_app_360ithub.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

