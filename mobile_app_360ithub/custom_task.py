import frappe
from datetime import datetime
from frappe.utils import nowdate


def daily_overdue_status_update():
    """
    Optimized Bulk Update.
    Updates 10,000 records in milliseconds.
    """
    
    
    # 1. Run the update in SQL
    # We also update 'modified' so we know the system touched it.
    frappe.db.sql("""
        UPDATE `tabTask`
        SET 
            status = 'Overdue',
            modified = NOW(),
            modified_by = 'Administrator'
        WHERE 
            status IN ('Open', 'Working', 'Pending Review')
            AND exp_end_date < %s
            AND docstatus < 2
    """, (nowdate()))

    # 2. Commit the transaction (Crucial for Cron jobs)
    frappe.db.commit()



def custom_before_save(doc, method):

    end_date = doc.exp_end_date
    if type(end_date) == str:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    if end_date and end_date < datetime.now().date() and doc.status in ["Open", "Working","Pending Review"]:
        doc.status = "Overdue"
    elif end_date and end_date >= datetime.now().date() and doc.status == "Overdue":
        doc.status = "Open"



def custom_task_share_on_insert(doc,method):
    if doc.owner != doc.task_owner:
        frappe.share.add("Task",doc.name,doc.task_owner,read=1,write=1,share=1)




def custom_task_share_on_update(doc, method):


    before_doc = doc.get_doc_before_save()
    if not before_doc:
        return

    if before_doc.task_owner != doc.task_owner :
        if doc.task_owner:
            frappe.share.add(
                "Task",
                doc.name,
                doc.task_owner,
                read=1,
                write=1,
                share=1,
                notify=0
            
            )

        if before_doc.task_owner:
            # pass
            remove_task_share(doc.name, before_doc.task_owner)


def remove_task_share(task_name, user):
    docshare = frappe.db.get_value(
        "DocShare",
        {
            "share_doctype": "Task",
            "share_name": task_name,
            "user": user,
        },
        "name",
    )

    if docshare:
        frappe.get_doc("DocShare", docshare).delete(ignore_permissions=True)




            