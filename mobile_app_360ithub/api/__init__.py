import frappe
from frappe import _
from frappe.utils import flt, cint, getdate, get_first_day, get_last_day, now, nowdate
from .utils import get_employee_by_user, get_last_log_details
import math
from typing import Dict, List, Optional, Any
from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period
from hrms.hr.report.employee_leave_balance.employee_leave_balance import (
    get_allocated_and_expired_leaves,
    get_opening_balance,
)
from frappe.utils.password import update_password
from datetime import datetime, timedelta

@frappe.whitelist()
def get_current_user_details() -> Dict[str, Any]:
	"""Get current user details with proper error handling.

	Returns:
		Dict[str, Any]: User details dictionary
	"""
	try:
		current_user = frappe.session.user
		if not current_user:
			frappe.throw(_("No active user session found"))

		user = frappe.db.get_value("User", current_user, "*", as_dict=True)
		if not user:
			frappe.throw(_("User details not found for {0}").format(current_user))

		return user
	except Exception as e:
		frappe.log_error(f"Error fetching user details: {str(e)}")
		frappe.throw(_("Failed to fetch user details"))

@frappe.whitelist()
def change_password(old_password: str, new_password: str) -> None:
	"""Change the password of the current user.

	Args:
		old_password (str): Current password
		new_password (str): New password
	"""
	try:
		current_user = frappe.session.user
		if not current_user:
			frappe.throw(_("No active user session found"))

		# Fetch the actual User document, not just values
		user = frappe.get_doc("User", current_user)
		if not user:
			frappe.throw(_("User details not found for {0}").format(current_user))

		try:
			frappe.auth.check_password(user.name, old_password)
		except frappe.AuthenticationError:
			frappe.throw(_("Incorrect current password"))

		update_password(user=user.name, pwd=new_password)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Error changing password: {str(e)}")
		frappe.throw(_(str(e)))

@frappe.whitelist()
def get_home_page() -> Dict[str, Any]:
	"""Get home page data including employee and log details.

	Returns:
		Dict[str, Any]: Dictionary containing employee data and log details
	"""
	try:
		current_user = frappe.session.user
		if not current_user:
			frappe.throw(_("No active user session found"))

		emp_data = get_employee_by_user(current_user)
		if not emp_data:
			frappe.throw(_("Employee data not found for current user"))

		log_details = get_last_log_details(emp_data.get("name"))

		return {
			"emp_data": emp_data,
			"log_details": log_details
		}
	except Exception as e:
		frappe.log_error(f"Error fetching home page data: {str(e)}")
		frappe.throw(_("Failed to fetch home page data {0}").format(str(e)))

@frappe.whitelist()
def get_leave_data(year: Optional[int] = None) -> List[Dict[str, Any]]:
	"""Get leave data for the current employee for a specific year.

	Args:
		year (Optional[int]): Year to fetch leave data for. Defaults to current year.

	Returns:
		List[Dict[str, Any]]: List of leave data dictionaries
	"""
	try:
		current_user = frappe.session.user
		if not current_user:
			frappe.throw(_("No active user session found"))

		# Get current year if not provided
		if not year:
			year = getdate(nowdate()).year

		# Validate year
		if not isinstance(year, int) or year < 1900 or year > 2100:
			frappe.throw(_("Invalid year provided: {0}").format(year))

		# Calculate date range for the year
		from_date = get_first_day(f"{year}-01-01")
		to_date = get_last_day(f"{year}-12-31")

		# Get employee data
		employee_data = get_employee_by_user(current_user)
		if not employee_data:
			frappe.throw(_("Employee data not found for current user"))

		return get_employee_leave_data([employee_data], to_date, from_date)

	except Exception as e:
		frappe.log_error(f"Error fetching leave data: {str(e)}")
		frappe.throw(_("Failed to fetch leave data {0}").format(str(e)))


def get_employee_leave_data(employees: List[Dict], to_date: str, from_date: str) -> List[Dict[str, Any]]:
	"""Get comprehensive leave data for employees.

	Args:
		employees (List[Dict]): List of employee dictionaries
		to_date (str): End date for leave data
		from_date (str): Start date for leave data

	Returns:
		List[Dict[str, Any]]: List of leave data for each employee and leave type
	"""
	try:
		if not employees:
			return []

		if not from_date or not to_date:
			frappe.throw(_("From date and to date are required"))

		# Get system precision for float calculations
		precision = cint(frappe.db.get_single_value("System Settings", "float_precision")) or 2

		# Get all leave types
		leave_types = frappe.get_all(
			"Leave Type",
			pluck="name",
			order_by="name"
		)

		if not leave_types:
			frappe.throw(_("No leave types found"))

		data = []

		for employee in employees:
			if not employee or not employee.get("name"):
				continue

			employee_name = employee.get("name")
			employee_display_name = employee.get("employee_name", employee_name)

			for leave_type in leave_types:
				try:
					leave_data = _calculate_leave_balance(
						employee_name=employee_name,
						employee_display_name=employee_display_name,
						leave_type=leave_type,
						from_date=from_date,
						to_date=to_date,
						precision=precision
					)

					if leave_data:
						data.append(leave_data)

				except Exception as e:
					frappe.log_error(
						f"Error calculating leave data for {employee_name}, {leave_type}: {str(e)}"
					)
					continue

		return data

	except Exception as e:
		frappe.log_error(f"Error in get_employee_leave_data: {str(e)}")
		raise


def _calculate_leave_balance(
	employee_name: str,
	employee_display_name: str,
	leave_type: str,
	from_date: str,
	to_date: str,
	precision: int
) -> Optional[Dict[str, Any]]:
	"""Calculate leave balance for a specific employee and leave type.

	Args:
		employee_name (str): Employee ID
		employee_display_name (str): Employee display name
		leave_type (str): Leave type name
		from_date (str): Start date
		to_date (str): End date
		precision (int): Float precision for calculations

	Returns:
		Optional[Dict[str, Any]]: Leave balance data or None if calculation fails
	"""
	try:
		# Calculate leaves taken (negative value from system)
		leaves_taken = get_leaves_for_period(
			employee_name, leave_type, from_date, to_date
		) * -1

		# Get allocation and expiry data
		new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
			from_date, to_date, employee_name, leave_type
		)

		# Calculate opening balance
		filters = frappe._dict({"from_date": from_date, "to_date": to_date})
		opening_balance = get_opening_balance(
			employee_name, leave_type, filters, carry_forwarded_leaves
		)

		# Calculate closing balance
		closing_balance = new_allocation + opening_balance - (expired_leaves + leaves_taken)

		# Special handling for Leave Without Pay
		if leave_type == "Leave Without Pay":
			closing_balance = 0

		# Prepare result dictionary
		result = frappe._dict({
			"employee": employee_name,
			"employee_name": employee_display_name,
			"leave_type": leave_type,
			"leaves_allocated": flt(new_allocation, precision),
			"leaves_expired": flt(expired_leaves, precision),
			"opening_balance": flt(opening_balance, precision),
			"leaves_taken": flt(leaves_taken, precision),
			"closing_balance": flt(closing_balance, precision),
			"indent": 1
		})

		return result

	except Exception as e:
		frappe.log_error(
			f"Error calculating leave balance for {employee_name}, {leave_type}: {str(e)}"
		)
		return None


@frappe.whitelist()
def log_employee_checkin(
	latitude: Optional[float] = None,
	longitude: Optional[float] = None,
	radius: Optional[float] = None
) -> Dict[str, Any]:
	"""Log employee check-in/out with location validation.

	Args:
		latitude (Optional[float]): Employee's current latitude
		longitude (Optional[float]): Employee's current longitude
		radius (Optional[float]): Override radius for validation

	Returns:
		Dict[str, Any]: Check-in result with details
	"""
	try:
		# Validate and parse input parameters
		latitude, longitude, radius = _validate_checkin_params(latitude, longitude, radius)

		# Get and validate employee data
		employee = _get_validated_employee()
		employee_id = employee.get("name")
		branch_name = employee.get("branch")

		geo_fencing_applicable = frappe.db.get_value("Employee", employee_id, "geo_fencing_applicable")
		if geo_fencing_applicable:
			# Validate location against branch
			_validate_employee_location(latitude, longitude, branch_name, radius)

		# Determine check-in type and create log
		log_type, action_message = _determine_log_type(employee_id)

		# Create check-in record
		checkin_doc = _create_checkin_record(employee_id, log_type, latitude, longitude)

		return {
			"success": True,
			"latitude": latitude,
			"longitude": longitude,
			"branch": branch_name,
			"log_type": log_type,
			"action_message": action_message,
			"checkin_id": checkin_doc.name,
			"timestamp": checkin_doc.time
		}

	except Exception as e:
		frappe.log_error(f"Error in employee check-in: {str(e)}")
		frappe.throw(_("Failed to log check-in {0}").format(str(e)))

def _validate_checkin_params(
	latitude: Optional[float],
	longitude: Optional[float],
	radius: Optional[float]
) -> tuple:
	"""Validate and parse check-in parameters.

	Args:
		latitude: Raw latitude parameter
		longitude: Raw longitude parameter
		radius: Raw radius parameter

	Returns:
		tuple: (latitude, longitude, radius) as floats

	Raises:
		frappe.ValidationError: If validation fails
	"""
	if latitude is None or longitude is None:
		frappe.throw(_("Latitude and longitude are required"))

	try:
		latitude = float(latitude)
		longitude = float(longitude)
		if radius is not None:
			radius = float(radius)
	except (ValueError, TypeError):
		frappe.throw(_("Latitude and longitude must be valid numbers"))

	# Validate coordinate ranges
	if not (-90 <= latitude <= 90):
		frappe.throw(_("Latitude must be between -90 and 90 degrees"))
	if not (-180 <= longitude <= 180):
		frappe.throw(_("Longitude must be between -180 and 180 degrees"))

	return latitude, longitude, radius


def _get_validated_employee() -> Dict[str, Any]:
	"""Get and validate employee data for current user.

	Returns:
		Dict[str, Any]: Employee data

	Raises:
		frappe.ValidationError: If employee not found or invalid
	"""
	current_user = frappe.session.user
	if not current_user:
		frappe.throw(_("No active user session found"))

	employee = get_employee_by_user(current_user)
	if not employee:
		frappe.throw(_("Employee record not found for current user"))

	if not employee.get("branch"):
		frappe.throw(_("No branch assigned to employee"))

	return employee


# def _validate_employee_location(
# 	latitude: float,
# 	longitude: float,
# 	branch_name: str,
# 	override_radius: Optional[float] = None
# ) -> None:
# 	"""Validate employee location against branch coordinates.

# 	Args:
# 		latitude: Employee latitude
# 		longitude: Employee longitude
# 		branch_name: Branch name
# 		override_radius: Override radius for validation

# 	Raises:
# 		frappe.ValidationError: If location validation fails
# 	"""
# 	try:
# 		# Get branch location data
# 		branch_data = frappe.db.get_value(
# 			"Branch",
# 			branch_name,
# 			["latitude", "longitude", "radius"],
# 			as_dict=True
# 		)

# 		if not branch_data:
# 			frappe.throw(_("Branch details not found for: {0}").format(branch_name))

# 		# Validate branch has location data
# 		if not branch_data.latitude or not branch_data.longitude:
# 			frappe.throw(
# 				_("Branch {0} does not have location coordinates configured").format(branch_name)
# 			)

# 		# Calculate distance
# 		branch_lat = float(branch_data.latitude)
# 		branch_lon = float(branch_data.longitude)
# 		distance = _haversine(branch_lat, branch_lon, latitude, longitude)

# 		# Determine radius to use
# 		validation_radius = override_radius
# 		if validation_radius is None:
# 			validation_radius = float(branch_data.radius) if branch_data.radius else 100.0

# 		# Validate distance
# 		if distance > validation_radius:
# 			frappe.throw(
# 				_("You are {0:.0f} meters away from the branch. Maximum allowed distance is {1:.0f} meters")
# 				.format(distance, validation_radius)
# 			)

# 	except Exception as e:
# 		if "You are" in str(e) or "Branch" in str(e):
# 			raise
# 		frappe.log_error(f"Error validating employee location: {str(e)}")
# 		frappe.throw(_("Failed to validate location. Please try again"))


def _validate_employee_location(
    latitude: float,
    longitude: float,
    branch_name: str,
    override_radius: Optional[float] = None
) -> None:
    """Validate employee location against branch coordinates.

    Args:
        latitude: Employee latitude
        longitude: Employee longitude
        branch_name: Branch name
        override_radius: Override radius for validation

    Raises:
        frappe.ValidationError: If location validation fails
    """
    try:
        # Get branch location data
        branch_data = frappe.db.get_value(
            "Branch",
            branch_name,
            ["custom_latitude", "custom_longitude", "custom_radius"],
            as_dict=True
        )

        if not branch_data:
            frappe.throw(_("Branch details not found for: {0}").format(branch_name))

        # If radius is 0 or empty, allow the location to pass without validation
        if not branch_data.custom_radius or float(branch_data.custom_radius) == 0:
            return

        # Calculate distance
        branch_lat = float(branch_data.custom_latitude)
        branch_lon = float(branch_data.custom_longitude)
        distance = _haversine(branch_lat, branch_lon, latitude, longitude)

        # Determine radius to use
        validation_radius = override_radius
        if validation_radius is None:
            validation_radius = float(branch_data.radius) if branch_data.radius else 100.0

        # Validate distance
        if distance > validation_radius:
            frappe.throw(
                _("You are {0:.0f} meters away from the branch. Maximum allowed distance is {1:.0f} meters")
                .format(distance, validation_radius)
            )

    except Exception as e:
        if "You are" in str(e) or "Branch" in str(e):
            raise
        frappe.log_error(f"Error validating employee location: {str(e)}")
        frappe.throw(_("Failed to validate location. Please try again"))




def _determine_log_type(employee_id: str) -> tuple:
	"""Determine the log type based on last check-in.

	Args:
		employee_id: Employee ID

	Returns:
		tuple: (log_type, action_message)
	"""
	try:
		last_checkin = get_last_log_details(employee_id)

		if not last_checkin:
			return "IN", "checked in"

		last_log_type = last_checkin.get("log_type")
		if last_log_type == "IN":
			return "OUT", "checked out"
		else:
			return "IN", "checked in"

	except Exception as e:
		frappe.log_error(f"Error determining log type: {str(e)}")
		# Default to check-in if unable to determine
		return "IN", "checked in"


def _create_checkin_record(
	employee_id: str,
	log_type: str,
	latitude: float,
	longitude: float
):
	"""Create employee check-in record.

	Args:
		employee_id: Employee ID
		log_type: Log type (IN/OUT)
		latitude: Latitude
		longitude: Longitude

	Returns:
		Document: Created check-in document

	Raises:
		frappe.ValidationError: If document creation fails
	"""
	try:
		
		checkin_doc = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": employee_id,
			"log_type": log_type,
			"time": now(),
			"custom_custom_lat_long": f"{latitude},{longitude}",
			"custom_hrms_360ithub": 1,
		})

		checkin_doc.insert(ignore_permissions=True)
		return checkin_doc

	except Exception as e:
		frappe.log_error(f"Error creating check-in record: {str(e)}")
		frappe.throw(_("Failed to log check-in: {0}").format(str(e)))


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
	"""Calculate the distance between two lat/long points using Haversine formula.

	Args:
		lat1: First point latitude in degrees
		lon1: First point longitude in degrees
		lat2: Second point latitude in degrees
		lon2: Second point longitude in degrees

	Returns:
		float: Distance in meters
	"""
	R = 6371000  # Radius of the Earth in meters

	# Convert degrees to radians
	lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

	# Haversine formula
	dlat = lat2 - lat1
	dlon = lon2 - lon1

	a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
	c = 2 * math.asin(math.sqrt(a))

	distance = R * c  # Distance in meters
	return distance


########################### Attendance ###############################

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
        'Attendance',
        filters={
            'employee': emp_id,
            'attendance_date': ['between', [start_date, end_date]],
            'docstatus': 1
        },
        fields=['name', 'in_time', 'out_time', 'status', 'attendance_date', 'working_hours']
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
            'Employee Checkin',
            filters={'attendance': record.get("name")},
            fields=['log_type', 'time']
        )

        # Add record details to the list along with check-in details and working hours
        detailed_attendance_records.append({
            "attendance_date": record.get("attendance_date"),
            "in_time": record.get("in_time"),
            "out_time": record.get("out_time"),
            "status": status,
            "working_hours": record.get("working_hours"),  # Include working hours
            "checkin_details": checkin_records  # Include check-in details
        })

    # Sort detailed attendance records by attendance_date in descending order
    detailed_attendance_records.sort(key=lambda x: x['attendance_date'], reverse=True)

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
        "attendance_details": detailed_attendance_records
    }

    return result




@frappe.whitelist()
def get_employees_with_birthday_in_current_year():
    current_date = datetime.now().date()
    one_week_before = current_date - timedelta(days=7)
    end_of_year = current_date.replace(month=12, day=31)

    # Fetch employees with birthdays and custom anniversary dates
    employees = frappe.get_all("Employee",
        filters={
            "status": "Active",
        },
        fields=["name", "employee_name", "date_of_birth", "custom_anniversary_date", "date_of_joining", "image"],
    )

    events = []
    for emp in employees:
        if emp.date_of_birth:
            dob_this_year = emp.date_of_birth.replace(year=current_date.year)
            if one_week_before <= dob_this_year <= end_of_year:
                events.append({
                    "emp_name": emp.employee_name,
                    "event_type": "birthday",
                    "event_date": emp.date_of_birth,
                    "emp_image": emp.image
                })

        if emp.custom_anniversary_date:
            anniv_this_year = emp.custom_anniversary_date.replace(year=current_date.year)
            if one_week_before <= anniv_this_year <= end_of_year:
                events.append({
                    "emp_name": emp.employee_name,
                    "event_type": "anniversary",
                    "event_date": emp.custom_anniversary_date,
                    "emp_image": emp.image
                })

        if emp.date_of_joining:
            join_this_year = emp.date_of_joining.replace(year=current_date.year)
            if one_week_before <= join_this_year <= end_of_year:
                events.append({
                    "emp_name": emp.employee_name,
                    "event_type": "joining",
                    "event_date": emp.date_of_joining,
                    "emp_image": emp.image
                })

    # Sort the events by date for the current year in ascending order
    events.sort(key=lambda x: x['event_date'].replace(year=current_date.year))

    return events

