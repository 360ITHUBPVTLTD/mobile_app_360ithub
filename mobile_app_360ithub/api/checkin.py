import frappe
from frappe import _
from frappe.utils import now
import math
from typing import Any, Dict, Optional, Tuple
from .utils import get_employee_by_user, get_last_log_details

@frappe.whitelist()
def log_employee_checkin(
	latitude: Optional[float] = None,
	longitude: Optional[float] = None,
	radius: Optional[float] = None,
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
			"timestamp": checkin_doc.time,
		}

	except Exception as e:
		frappe.log_error(f"Error in employee check-in: {str(e)}")
		frappe.throw(_("Failed to log check-in {0}").format(str(e)))


@frappe.whitelist()
def _validate_checkin_params(
	latitude: Optional[float], longitude: Optional[float], radius: Optional[float]
) -> Tuple[float, float, Optional[float]]:
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


def _validate_employee_location(
	latitude: float,
	longitude: float,
	branch_name: str,
	override_radius: Optional[float] = None,
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
			as_dict=True,
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
				_(
					"You are {0:.0f} meters away from the branch. Maximum allowed distance is {1:.0f} meters"
				).format(distance, validation_radius)
			)

	except Exception as e:
		if "You are" in str(e) or "Branch" in str(e):
			raise
		frappe.log_error(f"Error validating employee location: {str(e)}")
		frappe.throw(_("Failed to validate location. Please try again"))


def _determine_log_type(employee_id: str):
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
	employee_id: str, log_type: str, latitude: float, longitude: float
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
		checkin_doc = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": employee_id,
				"log_type": log_type,
				"time": now(),
				"custom_custom_lat_long": f"{latitude},{longitude}",
				"custom_hrms_360ithub": 1,
			}
		)

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

	a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
	c = 2 * math.asin(math.sqrt(a))

	distance = R * c  # Distance in meters
	return distance
