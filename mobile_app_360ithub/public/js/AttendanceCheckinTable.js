frappe.ui.form.on('Attendance', {
    refresh: function(frm) {
        // Only run if we have both an employee and an attendance date
        if (frm.doc.employee && frm.doc.attendance_date) {
            render_checkin_table(frm);
        }
    }
});

function render_checkin_table(frm) {
    let wrapper = frm.get_field("checkin_logs_html").$wrapper;
    wrapper.html('<div style="padding:10px; color:#666;">Loading check-in logs...</div>');

    let start_time = frm.doc.attendance_date + " 00:00:00";
    let end_time = frm.doc.attendance_date + " 23:59:59";

    // Fetch the logs from the server
    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Employee Checkin',
            filters: {
                employee: frm.doc.employee,
                time: ['between', [start_time, end_time]]
            },
            fields:['name', 'time', 'log_type', 'system_generated'],
            order_by: 'time asc',
            limit_page_length: 100
        },
        callback: function(r) {
            let logs = r.message ||[];
            generate_html_table(frm, logs);
        }
    });
}

function generate_html_table(frm, logs) {
    let wrapper = frm.get_field("checkin_logs_html").$wrapper;

    if (logs.length === 0) {
        wrapper.html(`
            <div style="padding: 12px; margin-top: 10px; border: 1px solid #d1d8dd; border-radius: 4px; background: #fff5f5; text-align: center; color: #e74c3c; font-weight: bold; font-size: 13px;">
                <i class="fa fa-exclamation-triangle"></i> No check-in
            </div>
        `);
        return;
    }

    let pairs =[];
    let current_in = null;

    logs.forEach(log => {
        if (log.log_type === 'IN') {
            if (current_in) pairs.push({ in: current_in, out: null });
            current_in = log;
        } else if (log.log_type === 'OUT') {
            if (!current_in) {
                pairs.push({ in: null, out: log });
            } else {
                pairs.push({ in: current_in, out: log });
                current_in = null;
            }
        }
    });
    
    if (current_in) pairs.push({ in: current_in, out: null });

    let format_time = (t) => t ? t.split(' ')[1].substring(0, 5) : '';

    // --- YOUR NEW IDEA: Smart Labels ---
    let sys_label_text = "(Auto)";
    if (frm.doc.attendance_request) {
        sys_label_text = "(Attendance Request)";
    } else if (frm.doc.leave_application) {
        sys_label_text = "(Leave Application)";
    }
    let smart_label = ` <small style="color:#d35400; font-weight:normal;">${sys_label_text}</small>`;
    // -----------------------------------

    let html = `
        <div style="margin-top: 10px; font-weight: bold; margin-bottom: 5px; color: #333;">Check-in Details</div>
        <table class="table table-bordered" style="border: 1px solid #d1d8dd; font-size: 13px; background: white;">
            <thead>
                <tr style="background-color: #f3f6f8; color: #555;">
                    <th style="width: 50%; padding: 8px;">Check-In</th>
                    <th style="width: 50%; padding: 8px;">Check-Out</th>
                </tr>
            </thead>
            <tbody>
    `;

    pairs.forEach(p => {
        let in_text = p.in 
            ? `<span style="color:#27ae60; font-weight:bold;">${format_time(p.in.time)}</span>` 
            : '<span style="color:#e74c3c; font-style:italic;">Missed check-in</span>';
            
        let out_text = p.out 
            ? `<span style="color:#2980b9; font-weight:bold;">${format_time(p.out.time)}</span>` 
            : '<span style="color:#e74c3c; font-style:italic;">Missed check-out</span>';
        
        // Apply the smart label instead of (Sys)
        if (p.in && p.in.system_generated) in_text += smart_label;
        if (p.out && p.out.system_generated) out_text += smart_label;

        html += `
            <tr>
                <td style="padding: 8px;">${in_text}</td>
                <td style="padding: 8px;">${out_text}</td>
            </tr>
        `;
    });

    html += `</tbody></table>`;
    wrapper.html(html);
}