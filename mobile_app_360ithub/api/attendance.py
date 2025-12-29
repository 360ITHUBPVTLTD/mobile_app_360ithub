import frappe
import calendar

@frappe.whitelist()
def get_employee_attendance(emp_id, month, year):
	# Validate inputs
	if not emp_id or not month or not year:
		frappe.throw(("Employee ID, month, and year are required"))
	try:
		month = int(month)
		year = int(year)
	except ValueError:
		frappe.throw(("Month and year must be integers"))

	# Get the last day of the month
	last_day = calendar.monthrange(year, month)[1]

	# Format the first and last day of the month
	start_date = f"{year}-{month:02d}-01"
	end_date = f"{year}-{month:02d}-{last_day}"

	# Fetch attendance records for the specified employee and date range
	attendance_records = frappe.get_all(
		"Attendance",
		filters={
			"employee": emp_id,
			"attendance_date": ["between", [start_date, end_date]],
			"docstatus": 1,
		},
		fields=["name", "in_time", "out_time", "status", "attendance_date", "working_hours"],
	)

	# Initialize counters and store detailed records
	present_count = 0
	absent_count = 0
	leave_count = 0
	half_day_count = 0

	# Prepare detailed attendance records
	detailed_attendance_records = []

	# Bifurcate records based on status and count them
	for record in attendance_records:
		status = record.get("status")
		if status == "Present":
			present_count += 1
		elif status == "Absent":
			absent_count += 1
		elif status == "On Leave":
			leave_count += 1
		elif status == "Half Day":
			half_day_count += 0.5
		elif status == "Work From Home":
			present_count += 1

		# Fetch check-in records for the current attendance record
		checkin_records = frappe.get_all(
			"Employee Checkin",
			filters={"attendance": record.get("name")},
			fields=["log_type", "time"],
		)

		# Add record details to the list along with check-in details and working hours
		detailed_attendance_records.append(
			{
				"attendance_date": record.get("attendance_date"),
				"in_time": record.get("in_time"),
				"out_time": record.get("out_time"),
				"status": status,
				"working_hours": record.get("working_hours"),  # Include working hours
				"checkin_details": checkin_records,  # Include check-in details
			}
		)

	# Sort detailed attendance records by attendance_date in descending order
	detailed_attendance_records.sort(key=lambda x: x["attendance_date"], reverse=True)

	# Calculate total working days
	total_working_days = present_count + absent_count + leave_count + half_day_count

	# Prepare the result JSON
	result = {
		"month": month,
		"year": year,
		"total_present": present_count,
		"total_absent": absent_count,
		"total_on_leave": leave_count,
		"total_half_day": half_day_count,
		"total_working_days": total_working_days,
		"attendance_details": detailed_attendance_records,
	}

	return result
