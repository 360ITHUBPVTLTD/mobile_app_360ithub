frappe.query_reports["Advance Task Report"] = {
    filters: [
        {
            fieldname: "task_owner",
            label: __("Task Owner"),
            fieldtype: "Link",
            options: "User",
            width: "120"
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\nOpen\nWorking\nOverdue\nCompleted\nCancelled",
            width: "100"
        },
        {
            fieldname: "priority",
            label: __("Priority"),
            fieldtype: "Select",
            options: "\nLow\nMedium\nHigh\nUrgent",
            width: "100"
        },
        {
            fieldname: "type",
            label: __("Type"),
            fieldtype: "Link",
            options: "Task Type",
            width: "120"
        },
        {
            fieldname: "exp_end_date",
            label: __("Expected End Date"),
            fieldtype: "DateRange",
            width: "180"
        },
        {
            fieldname: "timespan",
            label: __("Timespan"),
            fieldtype: "Select",
            options: "\nToday\nThis Week\nThis Month\nOverdue",
            width: "120"
        }
    ],

    onload: function (report) {
        // Check if user has admin-like roles
        const is_admin = frappe.user.has_role("System Manager") || frappe.user.has_role("Admin");

        // Add "Create Task" button on top-right of report
        report.page.add_inner_button(__('Create Task'), function() {
            frappe.new_doc('Task');
        });

        // If not admin, restrict Task Owner filter
        if (!is_admin) {
            const current_user = frappe.session.user;

            // Set default value
            report.set_filter_value("task_owner", current_user);

            // Make field read-only
            const field = report.page.fields_dict["task_owner"];
            if (field && field.$input) {
                field.$input.prop("disabled", true);
                field.$input.css({
                    "background-color": "#f8f9fa",
                    "pointer-events": "none",
                    "opacity": "0.7"
                });
            }
        }
    }
};
