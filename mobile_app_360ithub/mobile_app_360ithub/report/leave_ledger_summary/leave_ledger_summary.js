// Copyright (c) 2026, 360ithub and contributors
// For license information, please see license.txt

frappe.query_reports["Leave Ledger Summary"] = {
	"filters": [
		{
			"fieldname": "fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options": "Fiscal Year",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("fiscal_year")
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname": "employee",
			"label": __("Employee"),
			"fieldtype": "Link",
			"options": "Employee"
		},
		{
			"fieldname": "branch",
			"label": __("Branch"),
			"fieldtype": "Link",
			"options": "Branch"
		},
		{
			"fieldname": "department",
			"label": __("Department"),
			"fieldtype": "Link",
			"options": "Department"
		},
		{
			"fieldname": "leave_type",
			"label": __("Leave Type"),
			"fieldtype": "Link",
			"options": "Leave Type"
		},
		{
			"fieldname": "employee_status",
			"label": __("Employee Status"),
			"fieldtype": "Select",
			"options": ["", "Active", "Inactive", "Left"],
			"default": ""
		}
	],

	"formatter": function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "balance" && data && data.balance < 0) {
			value = `<span style="color: var(--text-danger)">${value}</span>`;
		}
		if (column.fieldname === "unused" && data && data.unused > 0) {
			value = `<span style="color: var(--text-on-orange)">${value}</span>`;
		}

		return value;
	}
};
