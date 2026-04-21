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
    Normalize filters into the standard Frappe filter format.
    Accepts dict | list | None. Throws on invalid formats.

    Supports both standard and linked doctype filter formats:
    - 3-element: [field, operator, value] - queries main doctype
    - 4-element: [linked_doctype, field, operator, value] - queries through linked doctype

    Examples of normalized output:
    - {"status": "Open"} -> [["status", "=", "Open"]]
    - [["status", "=", "Open"]] -> unchanged
    - ["status", "=", "Open"] -> [["status", "=", "Open"]]
    - [["Dynamic Link", "link_name", "=", "LEAD-001"]] -> unchanged (linked doctype filter)
    """
    if f is None:
        return []

    # Strings are not acceptable at this stage (JSON parsing should have converted them)
    if isinstance(f, str):
        frappe.throw(_(f"Invalid filters format: expected dict or list of conditions; got {type(f).__name__}"))

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

        # Already a list of conditions: [[field, op, val], ...] or [[linked_dt, field, op, val], ...]
        if isinstance(f[0], list):
            normalized = []
            for cond in f:
                # Accept 3-element (standard) or 4-element (linked doctype) filters
                if not (isinstance(cond, list) and len(cond) in (3, 4)):
                    frappe.throw(_(f"Invalid filters format: each condition must be a 3 or 4-element list; got {cond}"))
                normalized.append(cond)
            return normalized

        # Single condition represented as a list: [field, op, val] or [linked_dt, field, op, val]
        if len(f) in (3, 4):
            return [f]

        frappe.throw(_(f"Invalid filters format: expected list of 3 or 4-element conditions; got a list of length {len(f)}"))

    # Unsupported type
    frappe.throw(_(f"Invalid filters format: expected dict or list; got {type(f).__name__}"))


def _populate_linked_docs(doctype, data, populate_links):
    """
    Populate linked document data for specified fields.

    Args:
        doctype (str): The main doctype being queried.
        data (list[dict]): List of documents to populate.
        populate_links (list[str]): List of field names to populate (Link, Dynamic Link, or Table fields).

    Returns:
        tuple: (data, populated_fields) - Documents with linked data embedded under 
               `_linked_{fieldname}` keys, and list of field names that were populated.
    """
    if not populate_links or not data:
        return data, []

    # Get meta to identify fields and their target doctypes
    meta = frappe.get_meta(doctype)
    link_field_map = {}  # fieldname -> options (target doctype or config)
    table_field_map = {}  # fieldname -> child doctype

    # Check if wildcard is used - populate all Link, Dynamic Link, and Table fields
    populate_all = "*" in populate_links

    for field in meta.fields:
        if populate_all or field.fieldname in populate_links:
            if field.fieldtype == "Link":
                link_field_map[field.fieldname] = field.options
            elif field.fieldtype == "Dynamic Link":
                link_field_map[field.fieldname] = {"dynamic": True, "doctype_field": field.options}
            elif field.fieldtype == "Table":
                table_field_map[field.fieldname] = field.options

    # Batch fetch linked documents to minimize DB calls
    for fieldname, options in link_field_map.items():
        if isinstance(options, dict) and options.get("dynamic"):
            # Dynamic Link - doctype varies per row
            doctype_field = options["doctype_field"]
            for row in data:
                link_value = row.get(fieldname)
                link_doctype = row.get(doctype_field)
                if link_value and link_doctype:
                    try:
                        linked_doc = frappe.get_doc(link_doctype, link_value).as_dict()
                        row[f"_linked_{fieldname}"] = linked_doc
                    except frappe.DoesNotExistError:
                        row[f"_linked_{fieldname}"] = None
        else:
            # Static Link - same target doctype for all rows
            target_doctype = options
            # Collect unique link values
            link_values = list(set(row.get(fieldname) for row in data if row.get(fieldname)))

            if link_values:
                # Batch fetch all linked documents
                linked_docs = {
                    doc.name: doc
                    for doc in frappe.get_all(
                        target_doctype,
                        filters={"name": ["in", link_values]},
                        fields=["*"]
                    )
                }

                # Embed linked docs in each row
                for row in data:
                    link_value = row.get(fieldname)
                    if link_value and link_value in linked_docs:
                        row[f"_linked_{fieldname}"] = linked_docs[link_value]
                    else:
                        row[f"_linked_{fieldname}"] = None

    # Fetch child table data
    if table_field_map:
        # Collect all parent names
        parent_names = [row.get("name") for row in data if row.get("name")]

        for fieldname, child_doctype in table_field_map.items():
            if parent_names:
                # Batch fetch all child records for all parents
                child_records = frappe.get_all(
                    child_doctype,
                    filters={"parent": ["in", parent_names], "parentfield": fieldname},
                    fields=["*"],
                    order_by="idx asc"
                )

                # Group by parent
                children_by_parent = {}
                for child in child_records:
                    parent = child.get("parent")
                    if parent not in children_by_parent:
                        children_by_parent[parent] = []
                    children_by_parent[parent].append(child)

                # Embed in each row
                for row in data:
                    row_name = row.get("name")
                    row[fieldname] = children_by_parent.get(row_name, [])

    # Return list of fields that were actually populated
    populated_fields = list(link_field_map.keys()) + list(table_field_map.keys())
    return data, populated_fields


@frappe.whitelist()
def get_doc_with_filters(doctype, filters=None, or_filters=None, fields=None, limit=20, order_by=None, group_by=None, start=0, populate_links=None):
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
        populate_links (list | str, optional): List of link field names to populate with full document data.
            For each field specified, the linked document will be fetched and embedded directly in the response.
            Example: `populate_links=["customer", "lead"]` will fetch and embed the full Customer and Lead documents.
            Defaults to None.
 
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
 
    # Parse populate_links JSON string if needed
    if isinstance(populate_links, str):
        try:
            populate_links = json.loads(populate_links)
        except (ValueError, TypeError):
            populate_links = [populate_links]  # Treat as single field name

    # Validate and normalize filters and or_filters using helper
    args['filters'] = _normalize_filters(parsed_filters)
    args['or_filters'] = _normalize_filters(parsed_or_filters)
 
    # Both filters and or_filters are now properly formatted for DatabaseQuery
 
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

        frappe.response['populated_fields'] = []

        # Populate linked documents if requested
        if populate_links and data:
            data, populated_fields = _populate_linked_docs(doctype, data, populate_links)
            frappe.response['populated_fields'] = populated_fields if populated_fields else []

        return data
 
    except Exception as e:
        frappe.log_error(f"Error in get_doc_with_filters: {str(e)}")
        frappe.throw(_(f"Failed to fetch {doctype} records: {str(e)}"))