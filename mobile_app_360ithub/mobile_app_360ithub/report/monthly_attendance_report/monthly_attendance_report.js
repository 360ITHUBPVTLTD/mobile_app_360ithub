// Copyright (c) 2024, Mohan and contributors
// For license information, please see license.txt

frappe.query_reports["Monthly Attendance Report"] = {
	"filters": [
		{
			"fieldname": "month",
			"label": __("Month"),
			"fieldtype": "Select",
			"reqd": 1 ,
			"options": [
				{ "value": 1, "label": __("Jan") },
				{ "value": 2, "label": __("Feb") },
				{ "value": 3, "label": __("Mar") },
				{ "value": 4, "label": __("Apr") },
				{ "value": 5, "label": __("May") },
				{ "value": 6, "label": __("June") },
				{ "value": 7, "label": __("July") },
				{ "value": 8, "label": __("Aug") },
				{ "value": 9, "label": __("Sep") },
				{ "value": 10, "label": __("Oct") },
				{ "value": 11, "label": __("Nov") },
				{ "value": 12, "label": __("Dec") },
			],
			"default": frappe.datetime.str_to_obj(frappe.datetime.get_today()).getMonth() + 1
		},
		{
			"fieldname":"year",
			"label": __("Year"),
			"fieldtype": "Select",
			"reqd": 1
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"get_query": () => {
				var company = frappe.query_report.get_filter_value('company');
				
				// 1. Check if the user is allowed to see everyone
				// Add any other roles that should see all employees (e.g., 'System Manager')
				if (frappe.user.has_role(['HR Manager', 'System Manager', 'HR User'])) {
					return {
						filters: {
							'company': company,
							'status': 'Active' // Optional: Hide left employees
						}
					};
				} 
				
				// 2. If they are a standard user, restrict to Self
				else {
					return {
						filters: {
							'company': company,
							// 'user_id' is the standard field linking Employee to User in v14/v15
							'user_id': frappe.session.user 
						}
					};
				}
			}
		},
		// {
		// 	"fieldname":"employee",
		// 	"label": __("Employee"),
		// 	"fieldtype": "Link",
		// 	"options": "Employee",
			
			
		// 	// "default":cur_emp(frappe.session.user),
		// 	// "read_only":1,
		// 	get_query: () => {
		// 		var company = frappe.query_report.get_filter_value('company');
		// 		var emp_user=frappe.session.user	

				

		// 		var filters_custom= {
		// 			'company': company,
		// 			'company_email':emp_user
		// 		}
		// 		return {
		// 			filters: filters_custom
		// 		};
		// 		// var emp_filter=true

		// 		// function getEmpFilter(emp_user) {
		// 		// 	return new Promise(function (resolve, reject) {
		// 		// 		frappe.call({
		// 		// 			method: 'lsa.lsa.report.monthly_attendance_report.monthly_attendance_report.get_emp_filter',
		// 		// 			args: {
		// 		// 				emp_user_id: emp_user
		// 		// 			},
		// 		// 			callback: function (res) {
		// 		// 				if (res && res.message !== undefined) {
		// 		// 					const emp_filter = res.message;
				
		// 		// 					if (emp_filter) {
		// 		// 						// Assuming filters_custom is declared and accessible in the outer scope
		// 		// 						filters_custom.company_email = emp_user;
		// 		// 					}
				
		// 		// 					console.log(filters_custom);
				
		// 		// 					// Resolve the promise with the modified filters
		// 		// 					resolve({ filters: filters_custom });
		// 		// 				} else {
		// 		// 					// Reject the promise with an error message
		// 		// 					reject(new Error('Error in server response'));
		// 		// 				}
		// 		// 			}
		// 		// 		});
		// 		// 	});
		// 		// }

		// 		// getEmpFilter(emp_user)
		// 		// 	.then(function (result) {
		// 		// 		// Access the modified filters here
		// 		// 		console.log(result.filters);
		// 		// 		// Continue with your logic here
		// 		// 	})
		// 		// 	.catch(function (error) {
		// 		// 		// Handle the error condition here
		// 		// 		console.error(error);
		// 		// 	});
		// 	}
		// },
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": ["","Branch","Grade","Department","Designation"]
		},
		{
			"fieldname":"summarized_view",
			"label": __("Summarized View"),
			"fieldtype": "Check",
			"Default": 0,
		}
	],
	onload: function() {
		return  frappe.call({
			method: "mobile_app_360ithub.mobile_app_360ithub.report.monthly_attendance_report.monthly_attendance_report.get_attendance_years",
			callback: function(r) {
				var year_filter = frappe.query_report.get_filter('year');
				year_filter.df.options = r.message;
				year_filter.df.default = r.message.split("\n")[0];
				year_filter.refresh();
				year_filter.set_input(year_filter.df.default);
				
			}
		});
	},
	formatter: function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		const summarized_view = frappe.query_report.get_filter_value('summarized_view');
		const group_by = frappe.query_report.get_filter_value('group_by');

		if (!summarized_view) {
			if ((group_by && column.colIndex > 3) || (!group_by && column.colIndex > 2)) {
				if (value == 'P' || value == 'WFH')
					value = "<span style='color:green'>" + value + "</span>";
				else if (value == 'A')
					value = "<span style='color:red'>" + value + "</span>";
				else if (value == 'HD')
					value = "<span style='color:orange'>" + value + "</span>";
				else if (value == 'L')
					value = "<span style='color:#318AD8'>" + value + "</span>";
			}
		}

		return value;
	}
};

function cur_emp(emp_user){
	var emp
	if (emp_user){
		frappe.call({
			method: 'mobile_app_360ithub.mobile_app_360ithub.report.monthly_attendance_report.monthly_attendance_report.get_current_employee',
			args: {
				user_id: emp_user
			},
			callback: function (r) {
				// Process the data from the server and dynamically fill the HTML field
				emp=r.message
				console.log(emp[0])
			}
		})
	}
	return emp[0]
}

