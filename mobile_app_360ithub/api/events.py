import frappe
from datetime import datetime, timedelta

@frappe.whitelist()
def get_employees_with_birthday_in_current_year():
	current_date = datetime.now().date()
	one_week_before = current_date - timedelta(days=7)
	end_of_year = current_date.replace(month=12, day=31)

	# Fetch employees with birthdays and custom anniversary dates
	employees = frappe.get_all(
		"Employee",
		filters={
			"status": "Active",
		},
		fields=[
			"name",
			"employee_name",
			"date_of_birth",
			"custom_anniversary_date",
			"date_of_joining",
			"image",
		],
	)

	events = []
	for emp in employees:
		if emp.date_of_birth:
			dob_this_year = emp.date_of_birth.replace(year=current_date.year)
			if one_week_before <= dob_this_year <= end_of_year:
				events.append(
					{
						"emp_name": emp.employee_name,
						"event_type": "birthday",
						"event_date": emp.date_of_birth,
						"emp_image": emp.image,
					}
				)

		if emp.custom_anniversary_date:
			anniv_this_year = emp.custom_anniversary_date.replace(year=current_date.year)
			if one_week_before <= anniv_this_year <= end_of_year:
				events.append(
					{
						"emp_name": emp.employee_name,
						"event_type": "anniversary",
						"event_date": emp.custom_anniversary_date,
						"emp_image": emp.image,
					}
				)

		if emp.date_of_joining:
			join_this_year = emp.date_of_joining.replace(year=current_date.year)
			if one_week_before <= join_this_year <= end_of_year:
				events.append(
					{
						"emp_name": emp.employee_name,
						"event_type": "joining",
						"event_date": emp.date_of_joining,
						"emp_image": emp.image,
					}
				)

	# Sort the events by date for the current year in ascending order
	events.sort(key=lambda x: x["event_date"].replace(year=current_date.year))

	return events
