frappe.ui.form.on('Attendance Request', {
    refresh: function(frm) {
        run_threshold_calculator(frm);
    },
    custom_check_in_time: function(frm) { run_threshold_calculator(frm); },
    custom_check_out_time: function(frm) { run_threshold_calculator(frm); },
    half_day: function(frm) { run_threshold_calculator(frm); },
    shift: function(frm) { run_threshold_calculator(frm); }
});

function run_threshold_calculator(frm) {
    if (!frm.doc.shift || !frm.doc.custom_check_in_time || !frm.doc.custom_check_out_time) {
        if (frm.fields_dict.custom_threshold_calculator) {
            frm.get_field("custom_threshold_calculator").$wrapper.html("");
        }
        return;
    }

    let start = moment(frm.doc.custom_check_in_time, "HH:mm:ss");
    let end = moment(frm.doc.custom_check_out_time, "HH:mm:ss");
    if (end.isBefore(start)) end.add(1, 'days');
    let duration = moment.duration(end.diff(start)).asHours().toFixed(2);

    frappe.db.get_value("Shift Type", frm.doc.shift, 
        ["working_hours_threshold_for_half_day", "working_hours_threshold_for_absent"], 
        (r) => {
            if (r) {
                let v1 = parseFloat(r.working_hours_threshold_for_half_day || 0);
                let v2 = parseFloat(r.working_hours_threshold_for_absent || 0);

                // Smart Logic: Higher is Full Day, Lower is Half Day
                let full_day_req = Math.max(v1, v2);
                let half_day_req = Math.min(v1, v2);

                let target_label = frm.doc.half_day ? "Half Day" : "Full Day";
                let required_val = frm.doc.half_day ? half_day_req : full_day_req;

                let is_met = parseFloat(duration) >= required_val;
                let status_text = is_met ? `${target_label} Threshold Meeting` : `${target_label} Threshold NOT Meeting`;
                let status_color = is_met ? "#28a745" : "#dc3545"; 

                let html = `
                <div style="margin-top: 10px; border: 1px solid #cce5ff; border-radius: 4px; overflow: hidden; background: white; font-family: inherit;">
                    <!-- LIGHT BLUE HEADING -->
                    <div style="padding: 10px; background: #e7f3ff; border-bottom: 1px solid #cce5ff; font-weight: bold; color: #004085; font-size: 13px;  letter-spacing: 0.5px;">
                        Work Duration Validation
                    </div>
                    <table class="table table-bordered" style="margin: 0; font-size: 13px; border: none;">
                        <tbody>
                            <tr style="border-top: none;">
                                <td style="width: 60%; color: #888; border-top: none;">Requested Duration</td>
                                <td style="font-weight: bold; color: #333; border-top: none;">${duration} hrs</td>
                            </tr>
                            <tr>
                                <td style="color: #888;">Required for ${target_label}</td>
                                <td style="font-weight: bold; color: #333;">${required_val} hrs</td>
                            </tr>
                            <tr style="background: ${is_met ? '#f8fff9' : '#fff8f8'};">
                                <td style="color: #555; font-weight: bold;">Status</td>
                                <td style="color: ${status_color}; font-weight: bold;">${status_text}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                `;
                frm.get_field("custom_threshold_calculator").$wrapper.html(html);
            }
        }
    );
}