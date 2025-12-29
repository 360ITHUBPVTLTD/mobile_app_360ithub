import frappe
from frappe import _
from typing import Any, Dict
from frappe.utils.password import update_password

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
