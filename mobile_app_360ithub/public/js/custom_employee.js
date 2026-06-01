frappe.ui.form.on('Employee', {
    refresh: function(frm) {
        if (frm.doc.checkin_method == "Biometric" ) {
            frm.set_df_property("attendance_device_id", "reqd", true);
        } else {
            frm.set_df_property("attendance_device_id", "reqd", false);
        }
    },
    checkin_method: function(frm) {
        if (frm.doc.checkin_method == "Biometric" ) {
            frm.set_df_property("attendance_device_id", "reqd", true);
        } else {
            frm.set_df_property("attendance_device_id", "reqd", false);
        }
    }
    
});
