import frappe



def before_insert_expense_claim(doc, method):
    # frappe.log_error(title="before_insert_expense_claim",message=frappe.as_json(doc))
    # # frappe.db.commit()
    cost_center = frappe.get_value("Employee", doc.employee, "payroll_cost_center")
    default_payable_account = frappe.get_value("Company", doc.company, "default_payable_account")
    doc.payable_account = default_payable_account
    if not cost_center:
        frappe.throw(("Payroll Cost Center is required in Employee."))
    for expense in doc.expenses:
        expense.cost_center = cost_center
        

