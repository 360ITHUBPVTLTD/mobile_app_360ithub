frappe.query_reports["Monthly Attendance Matrix"] = {

	"filters": [
		{ "fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "reqd": 1, "default": frappe.defaults.get_user_default("Company") },
		{ "fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start(), "reqd": 1 },
		{ "fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end(), "reqd": 1 },
		{ "fieldname": "employee", "label": __("Employee"), "fieldtype": "Link", "options": "Employee" }
	],

	onload: function(report) {
		apply_styles();
		apply_highlight();

        // 🔥 This overrides the default Menu Export just in case someone clicks it
        report.export_report = function() {
            export_custom_excel(report);
        };
	},

	refresh: function(report) {
		apply_highlight();  

        // 🔥 ADD BUTTON OUTSIDE THE MENU (Top Right Toolbar)
        if (!report.page.inner_toolbar.find('.export-excel-btn').length) {
            
            let btn = report.page.add_inner_button("⬇ Export Excel", function() {
                export_custom_excel(report);
            });
            
            // Make the button blue and bold so it stands out completely outside
            btn.addClass("export-excel-btn btn-primary").css({
                "color": "white",
                "background-color": "#171717", // Dark button
                "font-weight": "bold",
                "border": "none"
            });
        }
	}
};


// 🔥 Custom Excel Export (Handles Bold & DD-MM-YYYY perfectly)
function export_custom_excel(report) {
    let company = report.get_filter_value('company') || "Company";
    let from_date = report.get_filter_value('from_date');
    let to_date = report.get_filter_value('to_date');
    
    // Format Date strictly to DD-MM-YYYY
    const format_to_dd_mm_yyyy = (date_str) => {
        if (!date_str) return "";
        let d_part = date_str.split(" ")[0]; 
        let parts = d_part.split("-");
        if (parts.length === 3 && parts[0].length === 4) { 
            return `${parts[2]}-${parts[1]}-${parts[0]}`;
        }
        return date_str; 
    };

    let f_date = format_to_dd_mm_yyyy(from_date);
    let t_date = format_to_dd_mm_yyyy(to_date);

    let col_count = report.columns.length;
    
    // Create HTML structure that Excel reads natively (Guarantees Bold)
    let html = `<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
    <head><meta charset="utf-8"></head>
    <body>
    <table border="1" style="border-collapse: collapse; font-family: Calibri, sans-serif;">`;
    
    // Company Name (Bold)
    html += `<tr><td colspan="${col_count}" style="text-align: left; font-size: 16px;"><b>${company}</b></td></tr>`;
    html += `<tr><td colspan="${col_count}"></td></tr>`;
    
    // Report Name (Bold)
    html += `<tr><td colspan="${col_count}" style="text-align: left; font-size: 14px;"><b>Report: Monthly Attendance Matrix</b></td></tr>`;
    
    // Formatted Filter Row (DD-MM-YYYY)
    html += `<tr><td colspan="${col_count}" style="text-align: left;"><b>Filters:</b> Date: ${f_date} to ${t_date}</td></tr>`;
    html += `<tr><td colspan="${col_count}"></td></tr>`;

    // Column Headers (Bold)
    html += `<tr>`;
    report.columns.forEach(col => {
        // Strip HTML so headers are clean text
        let clean_label = col.label.replace(/<br>/g, ' ').replace(/<[^>]+>/g, '').trim();
        html += `<td style="background-color: #f3f3f3; font-weight: bold; text-align: center;"><b>${clean_label}</b></td>`;
    });
    html += `</tr>`;

    // Data Rows
    report.data.forEach(row => {
        html += `<tr>`;
        report.columns.forEach(col => {
            let value = row[col.fieldname] || "";
            
            // Strip HTML to ensure clean data cells without tags
            let clean_val = String(value).replace(/<br>/g, ' ').replace(/<[^>]+>/g, '').trim();
            
            let align = col.fieldname === "employee" ? "left" : "center";
            // "mso-number-format" stops excel from auto-converting times into wrong formats
            html += `<td style="text-align: ${align}; mso-number-format:'\\@';">${clean_val}</td>`;
        });
        html += `</tr>`;
    });

    html += `</table></body></html>`;

    // Download File
    let blob = new Blob([html], { type: 'application/vnd.ms-excel' });
    let link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = "Monthly_Attendance_Matrix.xls";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}


// 🔥 Separate function for styles
function apply_styles() {
	const style = document.createElement('style');
	style.innerHTML = `
		.dt-row { height: auto !important; min-height: 48px; }
		.dt-header .dt-cell__content { height: 55px !important; display: flex !important; align-items: center !important; justify-content: center !important; }
		.dt-cell__content { white-space: normal !important; text-align: center !important; line-height: 1.4 !important; display: flex !important; align-items: center !important; justify-content: center !important; height: 100%; padding: 6px 2px !important; }
		.attendance-cell { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; font-size: 12px; line-height: 1.2; }
	`;
	document.head.appendChild(style);
}


// 🔥 Separate function for highlight
function apply_highlight() {
	$(document).off('click', '.dt-cell__content');
	$(document).on('click', '.dt-cell__content', function(e) {
		if ($(this).closest('.dt-header').length) return;
		let $row = $(this).closest('.dt-row');
		let expanded = $row.hasClass('is-expanded');

		$('.dt-row').removeClass('is-expanded').css({ 'background-color': '', 'box-shadow': '', 'border-top': '', 'border-bottom': '', 'z-index': '' });
		$('.dt-cell').css({ 'background-color': '', 'height': '' });

		if (expanded) return;

		$row.addClass('is-expanded').css({ 'background-color': '#e0f2fe', 'box-shadow': '0 4px 12px rgba(0,0,0,0.1)', 'border-top': '2px solid #60a5fa', 'border-bottom': '2px solid #60a5fa', 'z-index': '10' });
		$row.find('.dt-cell').css({ 'background-color': 'transparent', 'height': 'auto' });
	});
}

// frappe.query_reports["Monthly Attendance Matrix"] = {

// 	"filters": [
// 		{ "fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "reqd": 1, "default": frappe.defaults.get_user_default("Company") },
// 		{ "fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.month_start(), "reqd": 1 },
// 		{ "fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.month_end(), "reqd": 1 },
// 		{ "fieldname": "employee", "label": __("Employee"), "fieldtype": "Link", "options": "Employee" }
// 	],

// 	onload: function(report) {
// 		apply_styles();
// 		apply_highlight();
// 	},

// 	refresh: function(report) {
// 		apply_highlight();  // 🔥 THIS FIXES YOUR ISSUE
// 	}
// };


// // 🔥 Separate function for styles
// function apply_styles() {
// 	const style = document.createElement('style');
// 	style.innerHTML = `

// 		.dt-row { 
// 			height: auto !important; 
// 			min-height: 48px;
// 		}

// 		.dt-header .dt-cell__content { 
// 			height: 55px !important; 
// 			display: flex !important; 
// 			align-items: center !important; 
// 			justify-content: center !important; 
// 		}

// 		.dt-cell__content { 
// 			white-space: normal !important; 
// 			text-align: center !important; 
// 			line-height: 1.4 !important; 
// 			display: flex !important;
// 			align-items: center !important;
// 			justify-content: center !important;
// 			height: 100%;
// 			padding: 6px 2px !important;
// 		}

// 		.attendance-cell {
// 			display: flex;
// 			flex-direction: column;
// 			align-items: center;
// 			justify-content: center;
// 			gap: 2px;
// 			font-size: 12px;
// 			line-height: 1.2;
// 		}
// 	`;

// 	document.head.appendChild(style);
// }


// // 🔥 Separate function for highlight (IMPORTANT)
// function apply_highlight() {

// 	// ✅ remove old binding (prevents duplicate issue)
// 	$(document).off('click', '.dt-cell__content');

// 	$(document).on('click', '.dt-cell__content', function(e) {

// 		if ($(this).closest('.dt-header').length) return;

// 		let $row = $(this).closest('.dt-row');
// 		let expanded = $row.hasClass('is-expanded');

// 		// Reset all rows
// 		$('.dt-row').removeClass('is-expanded').css({
// 			'background-color': '',
// 			'box-shadow': '',
// 			'border-top': '',
// 			'border-bottom': '',
// 			'z-index': ''
// 		});

// 		$('.dt-cell').css({
// 			'background-color': '',
// 			'height': ''
// 		});

// 		if (expanded) return;

// 		// Apply highlight
// 		$row.addClass('is-expanded').css({
// 			'background-color': '#e0f2fe',
// 			'box-shadow': '0 4px 12px rgba(0,0,0,0.1)',
// 			'border-top': '2px solid #60a5fa',
// 			'border-bottom': '2px solid #60a5fa',
// 			'z-index': '10'
// 		});

// 		$row.find('.dt-cell').css({
// 			'background-color': 'transparent',
// 			'height': 'auto'
// 		});
// 	});
// }