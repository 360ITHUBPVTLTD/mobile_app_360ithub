import frappe

def task_before_save(doc, method):
    """Before save — adjust sharing when task_owner changes."""
    if not doc.task_owner:
        return

    # For existing documents only
    if not doc.is_new():
        old_owner = frappe.db.get_value("Task", doc.name, "task_owner")

        # If the task owner has changed
        if old_owner and old_owner != doc.task_owner:
            # ✅ Update old owner's permission to read-only
            downgrade_old_owner_share(doc.name, old_owner)

            # ✅ Share with new owner (full rights)
            share_task_with_owner(docname=doc.name, owner=doc.task_owner)


from mobile_app_360ithub.fcm_notification import send_task_notification


def task_after_insert(doc, method):
    """After insert — share with the new owner if set."""
    if doc.task_owner:
        share_task_with_owner(docname=doc.name, owner=doc.task_owner)
    send_task_notification(doc, method="after_insert")


def downgrade_old_owner_share(docname, old_owner):
    """Downgrade old owner's share to read-only."""
    try:
        # If no share exists yet, create one with read-only
        if not frappe.db.exists("DocShare", {
            "share_doctype": "Task",
            "share_name": docname,
            "user": old_owner
        }):
            frappe.share.add("Task", docname, old_owner, read=1, write=0, share=0)
        else:
            # Update existing share
            frappe.db.set_value(
                "DocShare",
                {
                    "share_doctype": "Task",
                    "share_name": docname,
                    "user": old_owner
                },
                {
                    "read": 1,
                    "write": 0,
                    "share": 0
                }
            )
        frappe.logger().info(f"🔒 Old owner {old_owner} downgraded to read-only for Task {docname}")
    except Exception as e:
        frappe.log_error(f"Error downgrading old owner {old_owner} for Task {docname}: {e}", "Task Share Error")


def share_task_with_owner(docname, owner):
    """Share the Task with the owner (Read + Write + Share + Notify)."""
    try:
        doc = frappe.get_doc("Task", docname)

        # Avoid duplicate shares
        if not frappe.db.exists("DocShare", {
            "share_doctype": doc.doctype,
            "share_name": doc.name,
            "user": owner
        }):
            frappe.share.add(
                doc.doctype,
                doc.name,
                owner,
                read=1,
                write=1,
                share=1,
                notify=1
            )
        else:
            # Update rights if already shared but missing write/share
            frappe.db.set_value(
                "DocShare",
                {
                    "share_doctype": "Task",
                    "share_name": doc.name,
                    "user": owner
                },
                {
                    "read": 1,
                    "write": 1,
                    "share": 1
                }
            )

        frappe.logger().info(f"✅ Task {doc.name} shared with {owner} (read/write/share/notify)")
    except Exception as e:
        frappe.log_error(
            f"Error sharing Task {docname} with {owner}: {str(e)}",
            "Task Share Error"
        )
