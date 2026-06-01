frappe.ui.form.on('Attendance Request', {
    refresh: function(frm) {
        fetch_and_render_logs(frm);
    },
    employee: function(frm) {
        fetch_and_render_logs(frm);
    },
    from_date: function(frm) {
        fetch_and_render_logs(frm);
    },
    before_save: function(frm) {
        if (frm.doc.from_date){
            frm.doc.to_date = frm.doc.from_date;
            if(frm.doc.half_day){
                frm.doc.half_day_date = frm.doc.from_date;
            }
        }
        if (frm.doc.docstatus === 0 && frm.doc.custom_status === "Approved") {
            
            if (frm.confirmed_approval) {
                delete frm.confirmed_approval;
                return;
            }
            
            frappe.validated = false; // Halt save process
            
            // Fetch authorized roles from the server
            frappe.call({
                method: 'mobile_app_360ithub.custom_attendance_request.get_hr_admin_roles', // <--- Update this to your python path
                callback: function(r) {
                    const admin_roles = r.message || [];
                    const user_roles = frappe.user_roles;
                    
                    const is_admin = user_roles.some(role => admin_roles.includes(role));
                    const is_approver = (frappe.session.user === frm.doc.custom_attendance_request_approver);
                    
                    if (is_admin || is_approver) {
                        // User is authorized, request confirmation
                        frappe.confirm(
                            __('Approving this Attendance Request will automatically submit the document and finalize the records. This action cannot be undone. Do you wish to proceed?'),
                            function() {
                                frm.confirmed_approval = true;
                                frm.save();
                            }
                        );
                    } else {
                        // User is not authorized, abort save and show alert
                        const approver_name = frm.doc.custom_attendance_request_approver_name || frm.doc.custom_attendance_request_approver;
                        frappe.msgprint({
                            title: __('Authorization Required'),
                            indicator: 'red',
                            message: __('Only the designated approver ({0}) or an authorized HR Admin is permitted to approve this request.', [approver_name])
                        });
                    }
                }
            });
        }
    }
});

function fetch_and_render_logs(frm) {
    let fieldname = null;
    if (frm.fields_dict.custom_existing_checkins) {
        fieldname = "custom_existing_checkins";
    } else if (frm.fields_dict.existing_checkins) {
        fieldname = "existing_checkins";
    }

    if (!fieldname) return;

    if (frm.doc.employee && frm.doc.from_date) {
        let wrapper = frm.get_field(fieldname).$wrapper;
        wrapper.html('<div style="color:#666; padding:10px;"><i class="fa fa-spinner fa-spin"></i> Loading Log History...</div>');

        frappe.call({
            method: 'mobile_app_360ithub.custom_employee.get_existing_logs', 
            args: {
                employee: frm.doc.employee,
                attendance_date: frm.doc.from_date
            },
            callback: function(r) {
                if (r.message) {
                    let final_html = `
                        <div style="margin-bottom: 10px; font-weight: bold; color: #2c3e50; font-size: 14px; padding: 5px; background: #ecf0f1; border-left: 5px solid #3498db;">
                            Total Day Hours: <span style="color: #27ae60;">${r.message.office_hours} hrs</span>
                        </div>
                        ${r.message.html}
                        <div style="font-size: 11px; color: #7f8c8d; margin-top: 5px; font-style: italic;">
                            * Struck-through entries are biometric punches being overridden by this request.
                        </div>
                    `;
                    wrapper.html(final_html);
                }
            }
        });
    } else {
        frm.get_field(fieldname).$wrapper.html('<div style="color:#999; padding:10px; font-style:italic;">Select Employee and Date to see history.</div>');
    }
}


frappe.ui.form.on('Attendance Request', {
    refresh: function(frm) {
        if (frm.doc.custom_attendance_request_approver) {
            update_approver_label_only(frm);
        }
    },
 
    employee: function(frm) {
        if (frm.doc.employee) {
            // Auto-fetch approver from Employee Master
            frappe.db.get_value("Employee", frm.doc.employee, "leave_approver", (r) => {
                if (r && r.leave_approver) {
                    frm.set_value("custom_attendance_request_approver", r.leave_approver);
                    update_approver_label_only(frm);
                }
            });
        }
    },
 
    custom_attendance_request_approver: function(frm) {
        update_approver_label_only(frm);
    }
});
 
function update_approver_label_only(frm) {
    if (!frm.doc.custom_attendance_request_approver) {
        frm.set_df_property('custom_attendance_request_approver', 'description', "");
        return;
    }
 
    // Call the Python service to get the name safely (bypass permissions)
    frappe.call({
        method: 'mobile_app_360ithub.custom_employee.get_approver_name_service',
        args: {
            user_id: frm.doc.custom_attendance_request_approver
        },
        callback: function(r) {
            if (r.message) {
                // Show the name in bold green text right below the email field
                let name_html = `<b style="color: #27ae60;">Approver: ${r.message}</b>`;
                frm.set_df_property('custom_attendance_request_approver', 'description', name_html);
            } else {
                frm.set_df_property('custom_attendance_request_approver', 'description', "");
            }
        }
    });
}

