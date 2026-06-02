frappe.ui.form.on('Leave Application', {
    refresh: function(frm) {
        // 1. Hide Company and Other Details
        frm.set_df_property('company', 'hidden', 1);
        // frm.set_section_display('sb_other_details', 0);
       
        // 2. Hide the standard Email field (Leave Approver)
        frm.set_df_property('leave_approver', 'hidden', 1);
 
        // 3. Fetch name if coming from Workspace (where email is already set)
        if (frm.doc.leave_approver && !frm.doc.leave_approver_name) {
            fetch_approver_real_name(frm);
        }
       
        // 4. Initial check for logs
        if (frm.doc.employee && frm.doc.from_date) {
            fetch_and_render_biometric_table(frm);
        }
    },
 
    employee: function(frm) {
        // If selecting employee manually (Direct Entry)
        if (frm.doc.employee) {
            frappe.db.get_value("Employee", frm.doc.employee, "leave_approver", (r) => {
                if (r && r.leave_approver) {
                    frm.set_value("leave_approver", r.leave_approver);
                    // This will trigger the leave_approver event below
                }
            });
            fetch_and_render_biometric_table(frm);
        }
    },
 
    leave_approver: function(frm) {
        // Triggers whenever the email ID is set or changed
        fetch_approver_real_name(frm);
    },
 
    from_date: function(frm) {
        fetch_and_render_biometric_table(frm);
    }
});
 
// Helper: Convert Email ID to Name
// function fetch_approver_real_name(frm) {
//     if (!frm.doc.leave_approver) return;
 
//     frappe.db.get_value("Employee", {"user_id": frm.doc.leave_approver}, "employee_name", (r) => {
//         if (r && r.employee_name) {
//             // FIXED: Using leave_approver_name to match your database field
//             // frm.set_value("leave_approver_name", r.employee_name);
//         }
//     });
// }
 
// Helper: Punch History
function fetch_and_render_biometric_table(frm) {
    if (!frm.doc.employee || !frm.doc.from_date) {
        frm.set_df_property('custom_checkin_logs_html', 'hidden', 1);
        return;
    }
 
    frappe.call({
        // CALL THE NEW SIMPLE FUNCTION
        method: 'mobile_app_360ithub.custom_employee.get_simple_logs_for_leave',
        args: {
            employee: frm.doc.employee,
            attendance_date: frm.doc.from_date
        },
        callback: function(r) {
            let wrapper = frm.get_field("custom_checkin_logs_html").$wrapper;
           console.log("Hello")
            if (r.message) {
                let final_html = `
                    <div style="margin-top: 5px; border: 1px solid #cce5ff; border-radius: 4px; overflow: hidden; background: white;">
                        <div style="padding: 8px; background: #e7f3ff; border-bottom: 1px solid #cce5ff; font-weight: bold; color: #004085; font-size: 11px; text-transform: uppercase;">
                            <i class="fa fa-clock-o"></i> Punch History (${frm.doc.from_date})
                        </div>
                        <div style="padding: 0px;">
                            ${r.message}
                        </div>
                    </div>
                `;
                wrapper.html(final_html);
                frm.set_df_property('custom_checkin_logs_html', 'hidden', 0);
            } else {
                // If no logs found, hide the table completely
                wrapper.html("");
                frm.set_df_property('custom_checkin_logs_html', 'hidden', 1);
            }
        }
    });
}
 
 
function fetch_approver_real_name(frm) {
    if (!frm.doc.leave_approver) {
        frm.set_value("leave_approver_name", "");
        return;
    }
 
    // We call the Python method because it has "System" power
    // to see names that the Employee Role cannot see.
    frappe.call({
        method: 'mobile_app_360ithub.custom_employee.get_approver_name_service',
        args: {
            user_id: frm.doc.leave_approver
        },
        callback: function(r) {
            if (r.message) {
                frm.set_value("leave_approver_name", r.message);
            } else {
                // Fallback: if no employee record is found, show the User ID
                frm.set_value("leave_approver_name", frm.doc.leave_approver);
            }
        }
    });
}