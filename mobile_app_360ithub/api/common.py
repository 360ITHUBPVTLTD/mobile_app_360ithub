import frappe
from frappe import _
from frappe.model.db_query import DatabaseQuery
from frappe.model.utils import is_virtual_doctype
from frappe.model.base_document import get_controller
import json
 
 
 
@frappe.whitelist()
def get_permitted_doctypes(user=None):
    if not user:
        user = frappe.session.user
 
    user_perms = frappe.utils.user.UserPermissions(user)
    user_perms.build_permissions()
 
    return {
        "can_read": user_perms.can_read,
        "can_write": user_perms.can_write,
        "can_create": user_perms.can_create,
        "can_delete": user_perms.can_delete,
        # Add other permission types as needed
    }
 
 
 
 
 
 
def _normalize_filters(f):
    """
    Normalize filters into the standard Frappe list-of-triplets format.
    Accepts dict | list | None. Throws on invalid formats.
 
    Examples of normalized output:
    - {"status": "Open"} -> [["status", "=", "Open"]]
    - [["status", "=", "Open"]] -> unchanged
    - ["status", "=", "Open"] -> [["status", "=", "Open"]]
    """
    if f is None:
        return []
 
    # Strings are not acceptable at this stage (JSON parsing should have converted them)
    if isinstance(f, str):
        frappe.throw(_(f"Invalid filters format: expected dict or list of 3-element conditions; got {type(f).__name__}"))
 
    if isinstance(f, dict):
        out = []
        for key, value in f.items():
            if isinstance(value, list) and len(value) >= 2:
                # e.g. [">", 100] or ["in", [1,2,3]]
                operator = value[0]
                filter_value = value[1]
                out.append([key, operator, filter_value])
            else:
                out.append([key, "=", value])
        return out
 
    if isinstance(f, list):
        if not f:
            return []
 
        # Already a list of conditions: [[field, op, val], ...]
        if isinstance(f[0], list):
            normalized = []
            for cond in f:
                if not (isinstance(cond, list) and len(cond) == 3):
                    frappe.throw(_(f"Invalid filters format: each condition must be a 3-element list; got {cond}"))
                normalized.append(cond)
            return normalized
 
        # Single condition represented as a list: [field, op, val]
        if len(f) == 3:
            return [f]
 
        frappe.throw(_(f"Invalid filters format: expected list of 3-element conditions; got a list of length {len(f)}"))
 
    # Unsupported type
    frappe.throw(_(f"Invalid filters format: expected dict or list; got {type(f).__name__}"))
 
@frappe.whitelist()
def get_doc_with_filters(doctype, filters=None, or_filters=None, fields=None, limit=20, order_by=None, group_by=None, start=0):
    """Get a list of documents with filters, optimized for REST API usage.
 
    This function mirrors the powerful querying capabilities of `frappe.desk.reportview.get_list`
    but returns data in a structured, uncompressed format suitable for APIs. It supports
    various filter formats, pagination, sorting, and grouping.
 
    Args:
        doctype (str): The Doctype to query.
        filters (list | dict | str, optional): Filters to apply. Can be:
            - A list of lists (standard Frappe format): `[["status", "=", "Open"]]
            - A dictionary: `{"status": "Open", "priority": "High"}`
            - A JSON string representation of a list or dict.
            Defaults to None.
        or_filters (list | dict | str, optional): OR filters to apply. Can be:
            - A list of lists (standard Frappe format): `[["first_name", "like", "%John%"], ["mobile_no", "like", "%123%"]]`
            - A dictionary: `{"first_name": "John", "last_name": "Doe"}`
            - A JSON string representation of a list or dict.
            When both `filters` and `or_filters` are present, the query becomes: `filters AND (any of or_filters)`.
            Example: `filters={"status": "Active"}` and `or_filters=[["first_name", "like", "%John%"], ["mobile_no", "like", "%123%"]]`
            will return records where status is Active AND (first_name contains John OR mobile_no contains 123).
            Defaults to None.
        fields (list, optional): Fields to fetch. Defaults to `['*']`.
        limit (int, optional): Number of records to return. Defaults to 10.
        order_by (str, optional): Field to order by. Defaults to 'modified desc'.
        group_by (str, optional): Field to group by. Defaults to None.
        start (int, optional): Start index for pagination. Defaults to 0.
 
    Returns:
        list[dict]: A list of documents. Additionally, `total_items_count` is set in
            the response as a separate key for pagination support.
    """
    # Prepare arguments similar to reportview.get_form_params()
    args = frappe._dict({
        'doctype': doctype,
        'filters': filters or [],
        'or_filters': or_filters or [],
        'fields': fields or ['*'],
        'limit_page_length': limit,
        'limit_start': start,
        'order_by': order_by or 'modified desc',
        'group_by': group_by
    })
 
    # Parse JSON strings like reportview.parse_json() does
    if isinstance(filters, str):
        try:
            filters = json.loads(filters)
        except (ValueError, TypeError):
            pass  # If parsing fails, use as-is
 
    # Update local variable with parsed filters; normalization/validation will follow
    parsed_filters = filters
 
    # Parse or_filters JSON strings (same logic as filters)
    if isinstance(or_filters, str):
        try:
            or_filters = json.loads(or_filters)
        except (ValueError, TypeError):
            pass  # If parsing fails, use as-is
 
    # Update local variable with parsed or_filters; normalization/validation will follow
    parsed_or_filters = or_filters
 
    # Validate and normalize filters and or_filters using helper
    args['filters'] = _normalize_filters(parsed_filters)
    args['or_filters'] = _normalize_filters(parsed_or_filters)
 
    # Both filters and or_filters are now properly formatted for DatabaseQuery
 
    # Filters are now properly formatted for DatabaseQuery
 
    try:
        # Use the exact same logic as reportview.get_list()
        if is_virtual_doctype(args.doctype):
            controller = get_controller(args.doctype)
            data = controller.get_list(args)
        else:
            # Use DatabaseQuery directly like reportview does (uncompressed format)
            # Pass all args as kwargs except doctype (which is used in constructor)
            doctype = args.pop('doctype')  # Remove doctype from args
            data = DatabaseQuery(doctype).execute(**args)
 
        # Get total count with same filters but no pagination
        total_count = DatabaseQuery(doctype).execute(
            filters=args.get('filters'),
            or_filters=args.get('or_filters'),
            fields=['count(*) as total'],
            group_by=args.get('group_by')
        )
        # Set total_items_count as separate response key (outside message)
        frappe.response['total_items_count'] = total_count[0].get('total', 0) if total_count else 0
 
        return data
 
    except Exception as e:
        frappe.log_error(f"Error in get_doc_with_filters: {str(e)}")
        frappe.throw(_(f"Failed to fetch {doctype} records: {str(e)}"))
 