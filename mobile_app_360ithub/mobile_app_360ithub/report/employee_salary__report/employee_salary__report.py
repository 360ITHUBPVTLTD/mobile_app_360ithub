# Copyright (c) 2025, Vatsal and contributors
# For license information, please see license.txt

# Copyright (c) 2024, Mohan and contributors
# For license information, please see license.txt

import frappe,json,calendar
from datetime import datetime,timedelta,date
from frappe.utils import add_days, cint, flt, getdate
from datetime import datetime, timedelta, date
from hrms.hr.doctype.leave_allocation.leave_allocation import get_previous_allocation
from hrms.hr.doctype.leave_application.leave_application import (get_leave_balance_on,get_leaves_for_period,)
from frappe.utils import get_url
import datetime as dt

def execute(filters=None):
    columns, data = [], []
     
    columns=[
        
        {"label": "Emp ID", "fieldname": "eid", "fieldtype": "Link", "options": "Employee", "width": 150, },
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 175, },


        {"label": "Net Payable Salary", "fieldname": "net_payable_salary", "fieldtype": "Currency", "width": 100, },
        
        {"label": "Bank Name", "fieldname": "bank_name", "fieldtype": "Data", "width": 150, },
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 90, },
        {"label": "Acc. No.", "fieldname": "acc_no", "fieldtype": "Data", "width": 150, },
        {"label": "IFSC", "fieldname": "ifsc", "fieldtype": "Data", "width": 120, },


        {"label": "Monthly Gross Salary", "fieldname": "monthly_salary", "fieldtype": "Currency", "width": 100, },
        
        
        # {"label": "Insurance Deductions", "fieldname": "insurance_deductions", "fieldtype": "Currency", "width": 100, "default":0.00},

        # {"label": "Other Deductions", "fieldname": "other_deductions", "fieldtype": "Currency", "width": 100, "default":0.00},
        
        {"label": "Leave Without Pay", "fieldname": "lwp", "fieldtype": "Float", "width": 100, },


        {"label": "Absents", "fieldname": "absent_marked_days", "fieldtype": "Float", "width": 100, },
        {"label": "Absents Needs To Be Resolved", "fieldname": "absent_need_to_be_resolve", "fieldtype": "Data", "width": 300, },

        {"label": "Pending Leave Applications(Count)", "fieldname": "leave_applications_need_to_be_resolve_count", "fieldtype": "Int", "width": 100, },
        {"label": "Pending Leave Applications", "fieldname": "leave_applications_need_to_be_resolve", "fieldtype": "Data", "width": 300, },
        
        {"label": "Unmarked Days Count (Empty)", "fieldname": "not_marked_days", "fieldtype": "Float", "width": 100, },
        {"label": "Unmarked Days Dates (Empty)", "fieldname": "attendance_not_marked", "fieldtype": "Data", "width": 300, },
        # {"label": "Worked Days", "fieldname": "worked_days", "fieldtype": "Data", "width": 100, },
        


                # {"label": "Balance Leave Without Pay", "fieldname": "leave_without_pay", "fieldtype": "Float", "width": 100, },
        {"label": "CompOff Lv Bal", "fieldname": "compensatory_off", "fieldtype": "Float", "width": 100, },
        {"label": "Priv Lv Bal", "fieldname": "privilege_leave", "fieldtype": "Float", "width": 100, },
        {"label": "Sick Lv Bal", "fieldname": "sick_leave", "fieldtype": "Float", "width": 100, },
        {"label": "Spcl Lv Bal", "fieldname": "special_leave", "fieldtype": "Float", "width": 100, },
        {"label": "Casual Lv Bal", "fieldname": "casual_leave", "fieldtype": "Float", "width": 100, },

        {"label": "Consumed Leave Summary", "fieldname": "leave_summary", "fieldtype": "Data", "width": 300, },

    ]


     
    data,leave_emp_map, leave_data_to_view,holidays_in_month, professional_tax_applicable = employee_data(filters)

    if professional_tax_applicable:
        columns.append({"label": "PT Deduction", "fieldname": "pt_deduction", "fieldtype": "Currency", "width": 100, })
    # html_card  = f"{holidays_in_month}"
    # html_card  += " <br>   ".join(leave_data_to_view)


    html_card = """
    <div style="display: flex; justify-content: flex-end; ">
        <button id="attendance_report_btn" class="btn btn-primary">
            Open Monthly Attendance Report
        </button>
    </div>

    
    """

    return columns, data, html_card


def employee_data(filters):
    fy = filters.get("fy")
    mon = filters.get("month")
    absent_data = None
    first_date, last_date = get_first_and_last_date_of_month(fy, mon)
    mon_num = first_date.month
    year_num = first_date.year
    from_leave_date = datetime(year_num, 1, 1)

    # 1. Fetch Absents (Status = Absent)
    absent_list = frappe.get_all("Attendance",
                                 filters={"status": "Absent", "docstatus": 1,
                                          "attendance_date": ("between", [first_date, last_date])},
                                 fields=["name", "employee_name", "employee"])

    holidays_in_month = get_holidays_in_month(first_date, last_date)
    
    ab_emp = {}
    if absent_list:
        for ab in absent_list:
            if ab.employee not in ab_emp:
                ab_emp[ab.employee] = []
            # Create a clickable link for the absent record
            ab_emp[ab.employee].append(f"<a href='{get_url()}/app/attendance/{ab.name}'>{ab.name} (Absent)</a>")

    holiday_dicts = frappe.get_all("Holiday", filters={"holiday_date": ("between", [first_date, last_date])},
                                   fields=("holiday_date",))
    holiday_dates = [str(holiday["holiday_date"])[-2:] for holiday in holiday_dicts]

    working_dates = set()
    current_date = first_date
    while current_date <= last_date:
        current_day = str(current_date)[-2:]
        if current_day not in holiday_dates:
            working_dates.add(current_day)
        current_date += timedelta(days=1)

    # 2. Fetch All Attendance (Added 'status' to fields to detect Half Days)
    attendance_list = frappe.get_all("Attendance",
                                     filters={"docstatus": 1,
                                              "attendance_date": ("between", [first_date, last_date])},
                                     fields=["name", "attendance_date", "employee_name", "employee", "status"])
    
    attendance_map = {}
    half_day_attendance_map = {} # NEW: Track Half Day Attendance Dates

    for attendance in attendance_list:
        # Standard Attendance Map (Tracks if ANY attendance exists)
        day_str = str(attendance["attendance_date"])[-2:]
        if attendance["employee"] not in attendance_map:
            attendance_map[attendance["employee"]] = {day_str}
        else:
            attendance_map[attendance["employee"]].add(day_str)
        
        # NEW: Half Day Specific Map
        if attendance["status"] == "Half Day":
            if attendance["employee"] not in half_day_attendance_map:
                half_day_attendance_map[attendance["employee"]] = {day_str}
            else:
                half_day_attendance_map[attendance["employee"]].add(day_str)

    emp_filter = {"status": "Active"}
    if filters.get("employee"):
        emp_filter["name"] = filters.get("employee")

    emp_list = frappe.get_all("Employee",
                              filters=emp_filter,
                              fields=["name", "employee_name", "ctc", "bank_name", "bank_ac_no", "ifsc_code",
                                      "company", "designation", "department", "date_of_joining"])

    # 3. Fetch Approved Leaves
    leave_application_list = frappe.get_all("Leave Application",
                                            filters={
                                                "status": "Approved",
                                                "docstatus": 1,
                                                "from_date": ("<=", last_date),
                                                "to_date": (">=", first_date)
                                            },
                                            fields=["name", "leave_type", "employee", "total_leave_days", "from_date",
                                                    "to_date", "half_day", "half_day_date"])

    leave_emp_map = {}
    emp_leave_summary = {}
    leave_data_to_view = []
    
    # NEW: Track dates that have an APPROVED Half Day Leave
    approved_half_day_leave_map = {} 

    for leave in leave_application_list:
        # Standard LWP Calculation
        if leave.leave_type == "Leave Without Pay":
            total_leave_days_for_current_month = get_leave_days_of_current_month(leave, first_date, last_date,
                                                                                 holidays_in_month)
            leave_data_to_view.append(str(leave) + str(total_leave_days_for_current_month) + "\n")
            if leave.employee not in leave_emp_map:
                leave_emp_map[leave.employee] = total_leave_days_for_current_month
            else:
                leave_emp_map[leave.employee] += total_leave_days_for_current_month

        # Leave Summary String Construction
        leave_date_range = [" to ".join(set([str(leave.from_date.strftime("%d-%m-%Y")), str(leave.to_date.strftime("%d-%m-%Y"))]))]
        if leave.employee not in emp_leave_summary:
            emp_leave_summary[leave.employee] = {leave.leave_type: [leave.total_leave_days, leave_date_range]}
        else:
            if leave.leave_type not in emp_leave_summary[leave.employee]:
                emp_leave_summary[leave.employee][leave.leave_type] = [leave.total_leave_days, leave_date_range]
            else:
                emp_leave_summary[leave.employee][leave.leave_type][0] += leave.total_leave_days
                emp_leave_summary[leave.employee][leave.leave_type][1] += leave_date_range

        # NEW: Map Approved Half Day Dates
        if leave.half_day and leave.half_day_date:
            # Check if half_day_date is string or date object
            hd_date = leave.half_day_date
            if isinstance(hd_date, str):
                hd_date = datetime.strptime(hd_date, "%Y-%m-%d").date()
            
            # Ensure the half day falls in this month
            if first_date <= hd_date <= last_date:
                hd_day_str = str(hd_date)[-2:] # Extract Day Number (e.g. '05')
                if leave.employee not in approved_half_day_leave_map:
                    approved_half_day_leave_map[leave.employee] = {hd_day_str}
                else:
                    approved_half_day_leave_map[leave.employee].add(hd_day_str)

    # 4. Fetch Pending Leaves
    pending_leave_application_list = frappe.get_all("Leave Application",
                                                    filters={
                                                        "docstatus": 0,
                                                        "status": ("not in", ["Cancelled", "Rejected"]),
                                                        "from_date": ("<=", last_date),
                                                        "to_date": (">=", first_date)
                                                    },
                                                    fields=["name", "employee"])
    pending_leave_application_dict = {}
    for pe_la in pending_leave_application_list:
        if pe_la.employee not in pending_leave_application_dict:
            pending_leave_application_dict[pe_la.employee] = []
        # Create link for pending application
        pending_leave_application_dict[pe_la.employee].append(f"<a href='{get_url()}/app/leave-application/{pe_la.name}'>{pe_la.name}</a>")

    data = []
    leave_data = get_employee_leave_data(emp_list, last_date, from_leave_date)
    emp_leave_bal = {}
    for i in leave_data:
        if i.employee not in emp_leave_bal:
            emp_leave_bal[i.employee] = {i.leave_type: (i.leaves_allocated, i.leaves_taken)}
        else:
            emp_leave_bal[i.employee][i.leave_type] = (i.leaves_allocated, i.leaves_taken)

    professional_tax_applicable = frappe.get_single_value("Mobile App Setting", "professional_tax_applicable")

    for emp in emp_list:
        data_row = {
            "eid": emp.name,
            "employee_name": emp.employee_name,
            "bank_name": emp.bank_name,
            "acc_no": emp.bank_ac_no,
            "ifsc": emp.ifsc_code,
        }

        not_marked_days = 0
        absent_marked_days = 0
        
        leave_types = frappe.get_all("Leave Type", pluck="name")
        for leave_type in leave_types:
            leavetypename = "_".join([l.lower() for l in leave_type.split(' ')])
            if emp.name in emp_leave_bal:
                if leave_type in emp_leave_bal[emp.name]:
                    data_row[leavetypename] = emp_leave_bal[emp.name][leave_type][0] - emp_leave_bal[emp.name][leave_type][1]
                else:
                    data_row[leavetypename] = 0
            else:
                data_row[leavetypename] = 0

        if emp.name in emp_leave_summary:
            summ_list = [f"{lv}({emp_leave_summary[emp.name][lv][0]})({', '.join(emp_leave_summary[emp.name][lv][1])})" for lv in emp_leave_summary[emp.name]]
            data_row["leave_summary"] = ", \n".join(summ_list)

        if emp.name not in attendance_map:
            continue

        should_skip_sal_calculation = False

        # --- CHECK 1: Pending Leave Applications (Blocks Salary) ---
        if emp.name in pending_leave_application_dict:
            data_row["monthly_salary"] = 0.00
            data_row["pt_deduction"] = 0.00
            data_row["other_deductions"] = 0.00
            data_row["insurance_deductions"] = 0.00
            data_row["lwp"] = 0
            data_row["net_payable_salary"] = 0
            data_row["leave_applications_need_to_be_resolve_count"] = len(pending_leave_application_dict[emp.name])
            data_row["leave_applications_need_to_be_resolve"] = ", \n".join(pending_leave_application_dict[emp.name])
            should_skip_sal_calculation = True

        # --- CHECK 2: Absents Marked in Attendance (Blocks Salary) ---
        # Initialize absent list if not exists, so we can append Half Day issues
        emp_absent_issues = ab_emp.get(emp.name, [])
        
        # --- NEW CHECK 3: Half Day Validation ---
        # Logic: If Half Day Attendance Exists AND NO Approved Half Day Leave Exists for that date -> Treat as Unresolved
        marked_half_days = half_day_attendance_map.get(emp.name, set())
        approved_half_days = approved_half_day_leave_map.get(emp.name, set())
        
        # Find days present in Attendance but missing in Approved Leaves
        unresolved_half_days = marked_half_days - approved_half_days
        
        if unresolved_half_days:
            for day_str in unresolved_half_days:
                # Add a specific message for Half Day Mismatch
                msg = f"Half Day Marked on {day_str}-{mon_num}-{year_num} without Approved Leave"
                emp_absent_issues.append(msg)
        
        if emp_absent_issues:
            data_row.update({
                "monthly_salary": 0.00,
                "pt_deduction": 0.00,
                "other_deductions": 0.00,
                "insurance_deductions": 0.00,
                "lwp": 0,
                "net_payable_salary": 0,
                "absent_need_to_be_resolve": ", \n".join(emp_absent_issues)
            })
            absent_marked_days = len(emp_absent_issues)
            should_skip_sal_calculation = True

        # Handle joining date logic
        joining_date = emp.date_of_joining
        if joining_date is None or joining_date <= first_date:
            adjusted_working_dates = working_dates
            unadjusted_count = 0
        else:
            adjusted_working_dates = {dt for dt in working_dates if dt >= str(joining_date.day).zfill(2)}
            total_days_count = (joining_date - first_date).days
            unadjusted_count = total_days_count

        data_row["worked_days"] = len(adjusted_working_dates)
        
        # Check if attendance is not marked for some working dates
        not_marked_dates = adjusted_working_dates - attendance_map[emp.name]
        if not_marked_dates:
            data_row["attendance_not_marked"] = ", \n".join([f"{i}-{mon_num}-{year_num}" for i in not_marked_dates])
            data_row["not_marked_days"] = len(not_marked_dates)
            should_skip_sal_calculation = True

        data_row["absent_marked_days"] = absent_marked_days

        if should_skip_sal_calculation:
            data.append(data_row)
            continue

        monthly_salary = round(emp.ctc / 12)
        pt_deduction = 0.00
        other_deductions = 0.00
        insurance_deductions = 0.00
        lwp = 0

        if monthly_salary >= 25000 and professional_tax_applicable == 1:
            pt_deduction = 200

        if emp.name in leave_emp_map:
            lwp = leave_emp_map[emp.name]

        # Standard Salary Calculation (Note: Half Day Leave deduction is already inside 'lwp' if approved)
        net_payable_salary = round((monthly_salary / 30) * (30 - lwp - unadjusted_count) - (pt_deduction + other_deductions + insurance_deductions), 0)

        data_row["monthly_salary"] = monthly_salary
        data_row["pt_deduction"] = pt_deduction
        data_row["insurance_deductions"] = insurance_deductions
        data_row["other_deductions"] = other_deductions
        data_row["lwp"] = lwp
        
        data_row["net_payable_salary"] = net_payable_salary
        data.append(data_row)

    holidays_in_month = "\n".join([f"{str(i)}<br>" for i in holidays_in_month])
    return data, leave_emp_map, leave_data_to_view, holidays_in_month, professional_tax_applicable
         
# def employee_data(filters):
#     fy = filters.get("fy")
#     mon = filters.get("month")
#     absent_data=None
#     first_date, last_date = get_first_and_last_date_of_month(fy, mon)
#     # print(first_date, last_date)
#     mon_num=first_date.month
#     year_num=first_date.year
#     from_leave_date = datetime(year_num, 1, 1)
#     absent_list = frappe.get_all("Attendance",
#                                  filters={"status": "Absent","docstatus":1, "attendance_date": ("between", [first_date, last_date])},
#                                  fields=["name", "employee_name","employee"])

#     holidays_in_month  = get_holidays_in_month(first_date, last_date)
#     # print("absent_listttttttttttttttttttt",absent_list)
#     ab_emp = {}
#     if absent_list:
#         absent_msg = f"First resolve the Absent mark for {mon} of {fy}"
        
#         for ab in absent_list:
#             #absent_msg += f"<br><a href='https://online.lsaoffice.com/app/attendance/{ab.name}'>{ab.name}</a> for {ab.employee}"
#             absent_msg += f"<br><a href='{get_url()}/app/attendance/{ab.name}'>{ab.name}</a> for {ab.employee}"

#             if ab.employee not in ab_emp:
#                 ab_emp[ab.employee] = []
#             ab_emp[ab.employee].append(ab.name)

#         # frappe.msgprint(absent_msg)
#         # return []
#     print("AAAAAAAAAAAAAAAAAAAAAAAAAab_emp",ab_emp)
#     # print("ab_emp",ab_emp)
    
#     holiday_dicts = frappe.get_all("Holiday",filters={"holiday_date":("between",[first_date, last_date])},fields=("holiday_date",))
#     holiday_dates = [str(holiday["holiday_date"])[-2:] for holiday in holiday_dicts]
#     # print("holiday_dates",holiday_dates)

#     working_dates = set()
#     current_date = first_date
#     while current_date <= last_date:
#         current_day=str(current_date)[-2:]
#         if current_day not in holiday_dates:
#             working_dates.add(current_day)
#         current_date += timedelta(days=1)
#     # print("working_dates",working_dates)
#     # absent_data=[working_dates]
#     attendance_list = frappe.get_all("Attendance",
#                                  filters={"docstatus":1, "attendance_date": ("between", [first_date, last_date])},
#                                  fields=["name","attendance_date", "employee_name","employee","status"])
#     attendance_map = {}
#     for attendance in attendance_list:
#         if attendance["employee"] not in attendance_map:
#             attendance_map[attendance["employee"]]={str(attendance["attendance_date"])[-2:]}
#         else:
#             attendance_map[attendance["employee"]].add(str(attendance["attendance_date"])[-2:])
    
#     # print("attendance_map",attendance_map)
#     # absent_data+=[attendance_map]
#     emp_filter = {"status":"Active"}
#     if filters.get("employee"):
#         # print('filterrrrrrrrrrrrr',filters.get("employee"))
#         emp_filter["name"] = filters.get("employee")
    
#     emp_list = frappe.get_all("Employee",
#                               filters=emp_filter,
#                               fields=["name", "employee_name", "ctc", "bank_name", "bank_ac_no", "ifsc_code",
#                                         "company","designation","department","date_of_joining"])

#     leave_application_list = frappe.get_all("Leave Application",
#                                             filters={
#                                                 # "leave_type": "Leave Without Pay",
#                                                 "status": "Approved",
#                                                 "docstatus": 1,
#                                                 "from_date": ("<=", last_date),
#                                                 "to_date": (">=", first_date)
#                                             },
#                                             fields=["name","leave_type", "employee", "total_leave_days", "from_date", "to_date","half_day","half_day_date"])
    
   
#     leave_emp_map = {}
#     emp_leave_summary={}
#     leave_data_to_view = []
#     for leave in leave_application_list:
#         if leave.leave_type =="Leave Without Pay":
            
#             total_leave_days_for_current_month = get_leave_days_of_current_month(leave,first_date,last_date,holidays_in_month)
#             leave_data_to_view.append(str(leave)+str(total_leave_days_for_current_month)+"\n")
#             if leave.employee not in leave_emp_map:
#                 # leave_for_month=leave_days_for_current_month(leave,first_date,last_date)
#                 # leave_emp_map[leave.employee] = leave_for_month
#                 leave_emp_map[leave.employee] = total_leave_days_for_current_month
#             else:
#                 # leave_for_month=leave_days_for_current_month(leave,first_date,last_date)
#                 # leave_emp_map[leave.employee] += leave_for_month
#                 leave_emp_map[leave.employee] += total_leave_days_for_current_month

#         leave_date_range=[" to ".join(set([str(leave.from_date.strftime("%d-%m-%Y")),str(leave.to_date.strftime("%d-%m-%Y"))]))]
#         if leave.employee not in emp_leave_summary:
#             emp_leave_summary[leave.employee] = {leave.leave_type :[leave.total_leave_days,leave_date_range]}
#         else:
#             if leave.leave_type not in emp_leave_summary[leave.employee]:
#                 emp_leave_summary[leave.employee][leave.leave_type] = [leave.total_leave_days,leave_date_range]
#             else:
#                 emp_leave_summary[leave.employee][leave.leave_type][0] += leave.total_leave_days
#                 emp_leave_summary[leave.employee][leave.leave_type][1] +=leave_date_range
#     absent_data=leave_emp_map
#     pending_leave_application_list = frappe.get_all("Leave Application",
#                                             filters={
#                                                 "docstatus": 0,
#                                                 "status": ("not in", ["Cancelled", "Rejected"]),
#                                                 "from_date": ("<=", last_date),
#                                                 "to_date": (">=", first_date)
#                                             },
#                                             fields=["name","employee",])
#     pending_leave_application_dict={}
#     for pe_la in pending_leave_application_list:
#         if pe_la.employee not in pending_leave_application_dict:
#             pending_leave_application_dict[pe_la.employee] = []
#         pending_leave_application_dict[pe_la.employee] += [pe_la.name]


#     # print(emp_leave_summary)
#     data = []
#     leave_data=get_employee_leave_data(emp_list,last_date,from_leave_date)
#     emp_leave_bal={}
#     for i in leave_data:
#         if i.employee not in emp_leave_bal:
#             emp_leave_bal[i.employee] = {i.leave_type:(i.leaves_allocated,i.leaves_taken)}
#         else:
#             emp_leave_bal[i.employee][i.leave_type]=(i.leaves_allocated,i.leaves_taken)
#     # print("leave_emp_map",emp_leave_bal)
#     professional_tax_applicable = frappe.get_single_value("Clarity App Setting", "professional_tax_applicable")

#     for emp in emp_list:

#         data_row = {
#             "eid": emp.name,
#             "employee_name": emp.employee_name,
#             "bank_name": emp.bank_name,
#             "acc_no": emp.bank_ac_no,
#             "ifsc": emp.ifsc_code,
#         }
#         # print("data_row",data_row)
#         not_marked_days=0
#         absent_marked_days=0
#         # leave_types = ['Leave Without Pay', 'Compensatory Off',  'Privilege Leave', 'Sick Leave', 'Special Leave','Casual Leave']
#         leave_types = frappe.get_all("Leave Type",pluck="name")
#         for leave_type in leave_types:
#             leavetypename="_".join([l.lower() for l in leave_type.split(' ')])
#             # print(leavetypename)
#             if emp.name in emp_leave_bal:
#                 if leave_type in emp_leave_bal[emp.name]:
#                     data_row[leavetypename]=emp_leave_bal[emp.name][leave_type][0]-emp_leave_bal[emp.name][leave_type][1]
#                 else:
#                     data_row[leavetypename]=0

#             else:
#                 data_row[leavetypename]=0

#         if emp.name in emp_leave_summary:
#             summ_list=[f"{lv}({emp_leave_summary[emp.name][lv][0]})({', '.join(emp_leave_summary[emp.name][lv][1])})"for lv in emp_leave_summary[emp.name]]
#             data_row["leave_summary"]=", \n".join(summ_list)


        

#         if emp.name not in attendance_map:
#             continue

#         should_skip_sal_calculation=False

#         if emp.name in pending_leave_application_dict :
#             data_row["monthly_salary"] = 0.00
#             data_row["pt_deduction"] = 0.00
#             data_row["other_deductions"] = 0.00
#             data_row["insurance_deductions"] = 0.00
#             data_row["lwp"] = 0
#             data_row["net_payable_salary"] = 0
#             data_row["leave_applications_need_to_be_resolve_count"]=len(pending_leave_application_dict[emp.name])
#             data_row["leave_applications_need_to_be_resolve"]=", \n".join(pending_leave_application_dict[emp.name])
#             # print("data_row_absent",data_row)
#             should_skip_sal_calculation=True


        
#         if emp.name in ab_emp:
#             data_row.update({
#                 "monthly_salary": 0.00,
#                 "pt_deduction": 0.00,
#                 "other_deductions": 0.00,
#                 "insurance_deductions": 0.00,
#                 "lwp": 0,
#                 "net_payable_salary": 0,
#                 "absent_need_to_be_resolve": ", \n".join(ab_emp[emp.name])
#             })
#             absent_marked_days = len(ab_emp[emp.name])
#             should_skip_sal_calculation = True
        
#         # Handle joining date logic
#         joining_date = emp.date_of_joining
#         # Adjusted working dates based on joining date
#         if joining_date is None or joining_date <= first_date:
#             adjusted_working_dates = working_dates
#             unadjusted_count = 0  # All working dates are adjusted
#         else:
#             # Working dates after joining date
#             adjusted_working_dates = {dt for dt in working_dates if dt >= str(joining_date.day).zfill(2)}
#             # Unadjusted working dates are those before the joining date
#             total_days_count = (joining_date - first_date).days  # This will give you all days, including weekends
#             unadjusted_count = total_days_count

#         # print('adjusted_working_datesssssssssssssssssss',len(adjusted_working_dates))
#         # unadjusted_count = len(unadjusted_count)
#         data_row["worked_days"] = len(adjusted_working_dates)
#         # adjusted_working_dates_count = len()
#         # Check if attendance is not marked for some working dates
#         not_marked_dates = adjusted_working_dates - attendance_map[emp.name]
#         if not_marked_dates:
#             data_row["attendance_not_marked"] = ", \n".join([f"{i}-{mon_num}-{year_num}" for i in not_marked_dates])
#             data_row["not_marked_days"] = len(not_marked_dates)
#             should_skip_sal_calculation = True

#         data_row["absent_marked_days"] = absent_marked_days

#         if should_skip_sal_calculation:
#             data.append(data_row)
#             continue

#         monthly_salary = round(emp.ctc / 12)
#         # net_payable_salary = round(emp.ctc / 12)
#         pt_deduction = 0.00
#         other_deductions = 0.00
#         insurance_deductions = 0.00
#         lwp = 0

#         if monthly_salary >= 25000 and professional_tax_applicable == 1:
#             pt_deduction = 200

#         if emp.name in leave_emp_map:
#             lwp = leave_emp_map[emp.name]
#         # print("lwppppppppppppp",lwp)
#         # net_payable_salary = round((monthly_salary / 30) * (30 - lwp-absent_marked_days-not_marked_days) - (pt_deduction + other_deductions),0)
#         net_payable_salary = round((monthly_salary / 30) * (30 - lwp - unadjusted_count) - (pt_deduction + other_deductions + insurance_deductions),0)


#         data_row["monthly_salary"] = monthly_salary
#         data_row["pt_deduction"] = pt_deduction
#         data_row["insurance_deductions"] = insurance_deductions
#         data_row["other_deductions"] = other_deductions
#         data_row["lwp"] = lwp
        
#         data_row["net_payable_salary"] = net_payable_salary
#         # print("data_row_complete",data_row)
#         data.append(data_row)
#     holidays_in_month = "\n".join([f"{str(i)}<br>" for i in holidays_in_month])
#     return data,leave_emp_map, leave_data_to_view,holidays_in_month, professional_tax_applicable


def get_first_and_last_date_of_month(fy, mon):
    # Split the financial year into start and end years
    start_year, end_year = map(int, fy.split('-'))

    # Map month names to month numbers
    months = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }

    # Get the month number
    month_number = months[mon]

    # Determine the actual year for the given month in the FY
    if month_number >= 4:  # April to December
        year = start_year
    else:  # January to March
        year = end_year

    # Get the first date of the month
    first_date = date(year, month_number, 1)

    # Get the last date of the month
    last_date = date(year, month_number, calendar.monthrange(year, month_number)[1])

    return first_date, last_date





def get_holidays_in_month(start_of_month, end_of_month):
    """
    Return a set of holiday date objects from the relevant Holiday List(s)
    whose from_date <= start_of_month and to_date >= end_of_month.

    :param start_of_month: A datetime.date object for the 1st day of the month
    :param end_of_month:   A datetime.date object for the last day of the month
    :return: A set of Python date objects (the holiday dates in that month range).
    """
    # Step 1: Find matching Holiday List(s)
    # We'll filter on from_date <= start_of_month AND to_date >= end_of_month
    holiday_list_records = frappe.get_all(
        "Holiday List",
        filters={
            "from_date": ("<=", start_of_month),
            "to_date": (">=", end_of_month),
        },
        fields=["name", "from_date", "to_date"]
    )

    # If no matching holiday list, return an empty set
    if not holiday_list_records:
        return set()

    # Step 2: Collect holidays from each matching Holiday List
    holiday_dates = set()

    for hl_rec in holiday_list_records:
        holiday_list_doc = frappe.get_doc("Holiday List", hl_rec["name"])

        # Step 3: Loop over child holiday rows in the doc
        for h in holiday_list_doc.holidays:
            # If it's a string like "2024-01-07", parse it, else use the date
            holiday_date = h.holiday_date
            if isinstance(holiday_date, str):
                holiday_date = datetime.strptime(holiday_date, "%Y-%m-%d").date()

            # Include only if it's within [start_of_month..end_of_month]
            if start_of_month <= holiday_date <= end_of_month:
                holiday_dates.add(holiday_date)

    return holiday_dates



def get_leave_days_of_current_month(leave_application, first_date, last_date, holidays_in_month):
    """
    Calculate how many days from 'leave_application' fall within [first_date..last_date],
    excluding any holidays in 'holidays_in_month'.

    :param leave_application: dict with keys:
        - "from_date" (str or date) in DD-MM-YYYY,
        - "to_date"   (str or date) in DD-MM-YYYY,
        - "half_day"  (bool),
        - "half_day_date" (str or date) in DD-MM-YYYY.
    :param first_date: A date object for the first day of the month.
    :param last_date:  A date object for the last day of the month.
    :param holidays_in_month: A set (or list) of date objects representing holidays in this month.
    :return: float (the number of leave days in the current month, after excluding holidays).
    """
    # 1) Parse from_date, to_date, half_day_date from strings if needed
    from_date = leave_application.get("from_date")  # e.g. "06-01-2025"
    to_date = leave_application.get("to_date")      # e.g. "10-01-2025"
    half_day_date = leave_application.get("half_day_date")  # e.g. "10-01-2025"

    if isinstance(from_date, str):
        from_date = datetime.strptime(from_date, "%d-%m-%Y").date()
    if isinstance(to_date, str):
        to_date = datetime.strptime(to_date, "%d-%m-%Y").date()

    # 2) Determine overlap window
    overlap_start = max(from_date, first_date)
    overlap_end = min(to_date, last_date)

    # If no overlap, zero days
    if overlap_start > overlap_end:
        return 0

    # 3) Create a list (or set) of all dates in the overlap
    overlap_length = (overlap_end - overlap_start).days + 1
    overlap_dates = [
        overlap_start + timedelta(days=i)
        for i in range(overlap_length)
    ]

    # 4) Exclude holidays
    #    'holidays_in_month' should be a set of date objects
    working_overlap_dates = [
        d for d in overlap_dates if d not in holidays_in_month
    ]

    leave_days_current_month = float(len(working_overlap_dates))

    # 5) If half-day is indicated, only subtract 0.5 if the half-day date is within 'working_overlap_dates'
    if leave_application.get("half_day") and leave_days_current_month > 0:
        if half_day_date:
            if isinstance(half_day_date, str):
                half_day_date = datetime.strptime(half_day_date, "%d-%m-%Y").date()
            if half_day_date in working_overlap_dates:
                leave_days_current_month -= 0.5

    # 6) Safety net
    if leave_days_current_month < 0:
        leave_days_current_month = 0

    return leave_days_current_month


def get_employee_leave_data(active_employees,to_date,from_date):
    
    precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
    # consolidate_leave_types = len(active_employees) > 1 and filters.consolidate_leave_types
    leave_types = frappe.get_all("Leave Type", pluck="name")
    row = None

    data = []

    data = []
    if active_employees:
        for leave_type in leave_types:
            
            row = frappe._dict({"leave_type": leave_type})

            for employee in active_employees:
                row = frappe._dict({"leave_type": leave_type})

                row.employee = employee.name
                row.employee_name = employee.employee_name

                leaves_taken = (
                    get_leaves_for_period(employee.name, leave_type, from_date, to_date) * -1
                )

                new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
                    from_date, to_date, employee.name, leave_type
                )
                opening = get_opening_balance(employee.name, leave_type, from_date, carry_forwarded_leaves)

                row.leaves_allocated = flt(new_allocation, precision)
                row.leaves_expired = flt(expired_leaves, precision)
                row.opening_balance = flt(opening, precision)
                row.leaves_taken = flt(leaves_taken, precision)

                closing = new_allocation + opening - (row.leaves_expired + leaves_taken)
                row.closing_balance = flt(closing, precision)
                if leave_type=="Leave Without Pay":
                    row.closing_balance = 0

                row.indent = 1
                data.append(row)

    return data


def get_allocated_and_expired_leaves(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> tuple[float, float, float]:
	new_allocation = 0
	expired_leaves = 0
	carry_forwarded_leaves = 0

	records = get_leave_ledger_entries(from_date, to_date, employee, leave_type)

	for record in records:
		# new allocation records with `is_expired=1` are created when leave expires
		# these new records should not be considered, else it leads to negative leave balance
		if record.is_expired:
			continue

		if record.to_date < getdate(to_date):
			# leave allocations ending before to_date, reduce leaves taken within that period
			# since they are already used, they won't expire
			expired_leaves += record.leaves
			leaves_for_period = get_leaves_for_period(
				employee, leave_type, record.from_date, record.to_date
			)
			expired_leaves -= min(abs(leaves_for_period), record.leaves)

		if record.from_date >= getdate(from_date):
			if record.is_carry_forward:
				carry_forwarded_leaves += record.leaves
			else:
				new_allocation += record.leaves

	return new_allocation, expired_leaves, carry_forwarded_leaves


def get_opening_balance(
	employee: str, leave_type: str, from_date, carry_forwarded_leaves: float
) -> float:
	# allocation boundary condition
	# opening balance is the closing leave balance 1 day before the filter start date
	opening_balance_date = add_days(from_date, -1)
	allocation = get_previous_allocation(from_date, leave_type, employee)

	if (
		allocation
		and allocation.get("to_date")
		and opening_balance_date
		and getdate(allocation.get("to_date")) == getdate(opening_balance_date)
	):
		# if opening balance date is same as the previous allocation's expiry
		# then opening balance should only consider carry forwarded leaves
		opening_balance = carry_forwarded_leaves
	else:
		# else directly get leave balance on the previous day
		opening_balance = get_leave_balance_on(employee, leave_type, opening_balance_date)

	return opening_balance

def get_leave_ledger_entries(
	from_date: str, to_date: str, employee: str, leave_type: str
) -> list[dict]:
	ledger = frappe.qb.DocType("Leave Ledger Entry")
	return (
		frappe.qb.from_(ledger)
		.select(
			ledger.employee,
			ledger.leave_type,
			ledger.from_date,
			ledger.to_date,
			ledger.leaves,
			ledger.transaction_name,
			ledger.transaction_type,
			ledger.is_carry_forward,
			ledger.is_expired,
		)
		.where(
			(ledger.docstatus == 1)
			& (ledger.transaction_type == "Leave Allocation")
			& (ledger.employee == employee)
			& (ledger.leave_type == leave_type)
			& (
				(ledger.from_date[from_date:to_date])
				| (ledger.to_date[from_date:to_date])
				| ((ledger.from_date < from_date) & (ledger.to_date > to_date))
			)
		)
	).run(as_dict=True)






# 
# # Copyright (c) 2025, Vatsal and contributors
# # For license information, please see license.txt

# # Copyright (c) 2024, Mohan and contributors
# # For license information, please see license.txt

# import frappe,json,calendar
# from datetime import datetime,timedelta,date
# from frappe.utils import add_days, cint, flt, getdate
# from datetime import datetime, timedelta, date
# from hrms.hr.doctype.leave_allocation.leave_allocation import get_previous_allocation
# from hrms.hr.doctype.leave_application.leave_application import (get_leave_balance_on,get_leaves_for_period,)
# from frappe.utils import get_url
# import datetime as dt

# def execute(filters=None):
#     columns, data = [], []
     
#     columns=[
        
#         {"label": "Emp ID", "fieldname": "eid", "fieldtype": "Link", "options": "Employee", "width": 100, },
#         {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 175, },


#         {"label": "Net Payable Salary", "fieldname": "net_payable_salary", "fieldtype": "Currency", "width": 100, },
        
#         {"label": "Bank Name", "fieldname": "bank_name", "fieldtype": "Data", "width": 150, },
#         {"label": "Branch", "fieldname": "branch", "fieldtype": "Data", "width": 90, },
#         {"label": "Acc. No.", "fieldname": "acc_no", "fieldtype": "Data", "width": 150, },
#         {"label": "IFSC", "fieldname": "ifsc", "fieldtype": "Data", "width": 120, },


#         {"label": "Monthly Gross Salary", "fieldname": "monthly_salary", "fieldtype": "Currency", "width": 100, },
        
        
#         # {"label": "Insurance Deductions", "fieldname": "insurance_deductions", "fieldtype": "Currency", "width": 100, "default":0.00},

#         # {"label": "Other Deductions", "fieldname": "other_deductions", "fieldtype": "Currency", "width": 100, "default":0.00},
        
#         {"label": "Leave Without Pay", "fieldname": "lwp", "fieldtype": "Float", "width": 100, },


#         {"label": "Absents", "fieldname": "absent_marked_days", "fieldtype": "Float", "width": 100, },
#         {"label": "Absents Needs To Be Resolved", "fieldname": "absent_need_to_be_resolve", "fieldtype": "Data", "width": 300, },

#         {"label": "Pending Leave Applications(Count)", "fieldname": "leave_applications_need_to_be_resolve_count", "fieldtype": "Int", "width": 100, },
#         {"label": "Pending Leave Applications", "fieldname": "leave_applications_need_to_be_resolve", "fieldtype": "Data", "width": 300, },
        
#         {"label": "Unmarked Days Count (Empty)", "fieldname": "not_marked_days", "fieldtype": "Float", "width": 100, },
#         {"label": "Unmarked Days Dates (Empty)", "fieldname": "attendance_not_marked", "fieldtype": "Data", "width": 300, },
#         # {"label": "Worked Days", "fieldname": "worked_days", "fieldtype": "Data", "width": 100, },
        


#                 # {"label": "Balance Leave Without Pay", "fieldname": "leave_without_pay", "fieldtype": "Float", "width": 100, },
#         {"label": "CompOff Lv Bal", "fieldname": "compensatory_off", "fieldtype": "Float", "width": 100, },
#         {"label": "Priv Lv Bal", "fieldname": "privilege_leave", "fieldtype": "Float", "width": 100, },
#         {"label": "Sick Lv Bal", "fieldname": "sick_leave", "fieldtype": "Float", "width": 100, },
#         {"label": "Spcl Lv Bal", "fieldname": "special_leave", "fieldtype": "Float", "width": 100, },
#         {"label": "Casual Lv Bal", "fieldname": "casual_leave", "fieldtype": "Float", "width": 100, },

#         {"label": "Consumed Leave Summary", "fieldname": "leave_summary", "fieldtype": "Data", "width": 300, },


        
#     ]


     
#     data,leave_emp_map, leave_data_to_view,holidays_in_month, professional_tax_applicable = employee_data(filters)

#     if professional_tax_applicable:
#         columns.append({"label": "PT Deduction", "fieldname": "pt_deduction", "fieldtype": "Currency", "width": 100, })
#     # html_card  = f"{holidays_in_month}"
#     # html_card  += " <br>   ".join(leave_data_to_view)


#     html_card = """
#     <div style="display: flex; justify-content: flex-end; ">
#         <button id="attendance_report_btn" class="btn btn-primary">
#             Open Monthly Attendance Report
#         </button>
#     </div>

#     <script>
#         document.getElementById('attendance_report_btn').addEventListener('click', function() {
#             var baseUrl = window.location.origin; // Dynamically get the base URL
#             var attendanceReportUrl = baseUrl + '/app/query-report/Monthly%20Attendance%20Sheet';
#             window.open(attendanceReportUrl, '_blank'); // Open the report in a new tab
#         });
#     </script>
#     <script>
#         document.addEventListener('click', function(event) {
#             // Check if the clicked element is a cell
#             var clickedCell = event.target.closest('.dt-cell__content');
#             if (clickedCell) {
#                 // Remove highlight from previously highlighted cells
#                 var previouslyHighlightedCells = document.querySelectorAll('.highlighted-cell');
#                 previouslyHighlightedCells.forEach(function(cell) {
#                     cell.classList.remove('highlighted-cell');
#                     cell.style.backgroundColor = ''; // Remove background color
#                     cell.style.border = ''; // Remove border
#                     cell.style.fontWeight = '';
#                 });
                
#                 // Highlight the clicked row's cells
#                 var clickedRow = event.target.closest('.dt-row');
#                 var cellsInClickedRow = clickedRow.querySelectorAll('.dt-cell__content');
#                 cellsInClickedRow.forEach(function(cell) {
#                     cell.classList.add('highlighted-cell');
#                     cell.style.backgroundColor = '#d7eaf9'; // Light blue background color
#                     cell.style.border = '2px solid #90c9e3'; // Border color
#                     cell.style.fontWeight = 'bold';
#                 });
#             }
#         });
        
#     </script>
#     """

#     return columns, data, html_card

     
# def employee_data(filters):
#     fy = filters.get("fy")
#     mon = filters.get("month")
#     absent_data=None
#     first_date, last_date = get_first_and_last_date_of_month(fy, mon)
#     # print(first_date, last_date)
#     mon_num=first_date.month
#     year_num=first_date.year
#     from_leave_date = datetime(year_num, 1, 1)
#     absent_list = frappe.get_all("Attendance",
#                                  filters={"status": "Absent","docstatus":1, "attendance_date": ("between", [first_date, last_date])},
#                                  fields=["name", "employee_name","employee"])

#     holidays_in_month  = get_holidays_in_month(first_date, last_date)
#     # print("absent_listttttttttttttttttttt",absent_list)
#     ab_emp = {}
#     if absent_list:
#         absent_msg = f"First resolve the Absent mark for {mon} of {fy}"
        
#         for ab in absent_list:
#             #absent_msg += f"<br><a href='https://online.lsaoffice.com/app/attendance/{ab.name}'>{ab.name}</a> for {ab.employee}"
#             absent_msg += f"<br><a href='{get_url()}/app/attendance/{ab.name}'>{ab.name}</a> for {ab.employee}"

#             if ab.employee not in ab_emp:
#                 ab_emp[ab.employee] = []
#             ab_emp[ab.employee].append(ab.name)

#         # frappe.msgprint(absent_msg)
#         # return []
#     print("AAAAAAAAAAAAAAAAAAAAAAAAAab_emp",ab_emp)
#     # print("ab_emp",ab_emp)
    
#     holiday_dicts = frappe.get_all("Holiday",filters={"holiday_date":("between",[first_date, last_date])},fields=("holiday_date",))
#     holiday_dates = [str(holiday["holiday_date"])[-2:] for holiday in holiday_dicts]
#     # print("holiday_dates",holiday_dates)

#     working_dates = set()
#     current_date = first_date
#     while current_date <= last_date:
#         current_day=str(current_date)[-2:]
#         if current_day not in holiday_dates:
#             working_dates.add(current_day)
#         current_date += timedelta(days=1)
#     # print("working_dates",working_dates)
#     # absent_data=[working_dates]
#     attendance_list = frappe.get_all("Attendance",
#                                  filters={"docstatus":1, "attendance_date": ("between", [first_date, last_date])},
#                                  fields=["name","attendance_date", "employee_name","employee"])
#     attendance_map = {}
#     for attendance in attendance_list:
#         if attendance["employee"] not in attendance_map:
#             attendance_map[attendance["employee"]]={str(attendance["attendance_date"])[-2:]}
#         else:
#             attendance_map[attendance["employee"]].add(str(attendance["attendance_date"])[-2:])
    
#     # print("attendance_map",attendance_map)
#     # absent_data+=[attendance_map]
#     emp_filter = {"status":"Active"}
#     if filters.get("employee"):
#         # print('filterrrrrrrrrrrrr',filters.get("employee"))
#         emp_filter["name"] = filters.get("employee")
    
#     emp_list = frappe.get_all("Employee",
#                               filters=emp_filter,
#                               fields=["name", "employee_name", "ctc", "bank_name", "bank_ac_no", "ifsc_code",
#                                         "company","designation","department","date_of_joining"])

#     leave_application_list = frappe.get_all("Leave Application",
#                                             filters={
#                                                 # "leave_type": "Leave Without Pay",
#                                                 "status": "Approved",
#                                                 "docstatus": 1,
#                                                 "from_date": ("<=", last_date),
#                                                 "to_date": (">=", first_date)
#                                             },
#                                             fields=["name","leave_type", "employee", "total_leave_days", "from_date", "to_date","half_day","half_day_date"])
    
   
#     leave_emp_map = {}
#     emp_leave_summary={}
#     leave_data_to_view = []
#     for leave in leave_application_list:
#         if leave.leave_type =="Leave Without Pay":
            
#             total_leave_days_for_current_month = get_leave_days_of_current_month(leave,first_date,last_date,holidays_in_month)
#             leave_data_to_view.append(str(leave)+str(total_leave_days_for_current_month)+"\n")
#             if leave.employee not in leave_emp_map:
#                 # leave_for_month=leave_days_for_current_month(leave,first_date,last_date)
#                 # leave_emp_map[leave.employee] = leave_for_month
#                 leave_emp_map[leave.employee] = total_leave_days_for_current_month
#             else:
#                 # leave_for_month=leave_days_for_current_month(leave,first_date,last_date)
#                 # leave_emp_map[leave.employee] += leave_for_month
#                 leave_emp_map[leave.employee] += total_leave_days_for_current_month

#         leave_date_range=[" to ".join(set([str(leave.from_date.strftime("%d-%m-%Y")),str(leave.to_date.strftime("%d-%m-%Y"))]))]
#         if leave.employee not in emp_leave_summary:
#             emp_leave_summary[leave.employee] = {leave.leave_type :[leave.total_leave_days,leave_date_range]}
#         else:
#             if leave.leave_type not in emp_leave_summary[leave.employee]:
#                 emp_leave_summary[leave.employee][leave.leave_type] = [leave.total_leave_days,leave_date_range]
#             else:
#                 emp_leave_summary[leave.employee][leave.leave_type][0] += leave.total_leave_days
#                 emp_leave_summary[leave.employee][leave.leave_type][1] +=leave_date_range
#     absent_data=leave_emp_map
#     pending_leave_application_list = frappe.get_all("Leave Application",
#                                             filters={
#                                                 "docstatus": 0,
#                                                 "status": ("not in", ["Cancelled", "Rejected"]),
#                                                 "from_date": ("<=", last_date),
#                                                 "to_date": (">=", first_date)
#                                             },
#                                             fields=["name","employee",])
#     pending_leave_application_dict={}
#     for pe_la in pending_leave_application_list:
#         if pe_la.employee not in pending_leave_application_dict:
#             pending_leave_application_dict[pe_la.employee] = []
#         pending_leave_application_dict[pe_la.employee] += [pe_la.name]


#     # print(emp_leave_summary)
#     data = []
#     leave_data=get_employee_leave_data(emp_list,last_date,from_leave_date)
#     emp_leave_bal={}
#     for i in leave_data:
#         if i.employee not in emp_leave_bal:
#             emp_leave_bal[i.employee] = {i.leave_type:(i.leaves_allocated,i.leaves_taken)}
#         else:
#             emp_leave_bal[i.employee][i.leave_type]=(i.leaves_allocated,i.leaves_taken)
#     # print("leave_emp_map",emp_leave_bal)
#     professional_tax_applicable = frappe.get_single_value("Clarity App Setting", "professional_tax_applicable")

#     for emp in emp_list:

#         data_row = {
#             "eid": emp.name,
#             "employee_name": emp.employee_name,
#             "bank_name": emp.bank_name,
#             "acc_no": emp.bank_ac_no,
#             "ifsc": emp.ifsc_code,
#         }
#         # print("data_row",data_row)
#         not_marked_days=0
#         absent_marked_days=0
#         # leave_types = ['Leave Without Pay', 'Compensatory Off',  'Privilege Leave', 'Sick Leave', 'Special Leave','Casual Leave']
#         leave_types = frappe.get_all("Leave Type",pluck="name")
#         for leave_type in leave_types:
#             leavetypename="_".join([l.lower() for l in leave_type.split(' ')])
#             # print(leavetypename)
#             if emp.name in emp_leave_bal:
#                 if leave_type in emp_leave_bal[emp.name]:
#                     data_row[leavetypename]=emp_leave_bal[emp.name][leave_type][0]-emp_leave_bal[emp.name][leave_type][1]
#                 else:
#                     data_row[leavetypename]=0

#             else:
#                 data_row[leavetypename]=0

#         if emp.name in emp_leave_summary:
#             summ_list=[f"{lv}({emp_leave_summary[emp.name][lv][0]})({', '.join(emp_leave_summary[emp.name][lv][1])})"for lv in emp_leave_summary[emp.name]]
#             data_row["leave_summary"]=", \n".join(summ_list)


        

#         if emp.name not in attendance_map:
#             continue

#         should_skip_sal_calculation=False

#         if emp.name in pending_leave_application_dict :
#             data_row["monthly_salary"] = 0.00
#             data_row["pt_deduction"] = 0.00
#             data_row["other_deductions"] = 0.00
#             data_row["insurance_deductions"] = 0.00
#             data_row["lwp"] = 0
#             data_row["net_payable_salary"] = 0
#             data_row["leave_applications_need_to_be_resolve_count"]=len(pending_leave_application_dict[emp.name])
#             data_row["leave_applications_need_to_be_resolve"]=", \n".join(pending_leave_application_dict[emp.name])
#             # print("data_row_absent",data_row)
#             should_skip_sal_calculation=True


        
#         if emp.name in ab_emp:
#             data_row.update({
#                 "monthly_salary": 0.00,
#                 "pt_deduction": 0.00,
#                 "other_deductions": 0.00,
#                 "insurance_deductions": 0.00,
#                 "lwp": 0,
#                 "net_payable_salary": 0,
#                 "absent_need_to_be_resolve": ", \n".join(ab_emp[emp.name])
#             })
#             absent_marked_days = len(ab_emp[emp.name])
#             should_skip_sal_calculation = True
        
#         # Handle joining date logic
#         joining_date = emp.date_of_joining
#         # Adjusted working dates based on joining date
#         if joining_date is None or joining_date <= first_date:
#             adjusted_working_dates = working_dates
#             unadjusted_count = 0  # All working dates are adjusted
#         else:
#             # Working dates after joining date
#             adjusted_working_dates = {dt for dt in working_dates if dt >= str(joining_date.day).zfill(2)}
#             # Unadjusted working dates are those before the joining date
#             total_days_count = (joining_date - first_date).days  # This will give you all days, including weekends
#             unadjusted_count = total_days_count

#         # print('adjusted_working_datesssssssssssssssssss',len(adjusted_working_dates))
#         # unadjusted_count = len(unadjusted_count)
#         data_row["worked_days"] = len(adjusted_working_dates)
#         # adjusted_working_dates_count = len()
#         # Check if attendance is not marked for some working dates
#         not_marked_dates = adjusted_working_dates - attendance_map[emp.name]
#         if not_marked_dates:
#             data_row["attendance_not_marked"] = ", \n".join([f"{i}-{mon_num}-{year_num}" for i in not_marked_dates])
#             data_row["not_marked_days"] = len(not_marked_dates)
#             should_skip_sal_calculation = True

#         data_row["absent_marked_days"] = absent_marked_days

#         if should_skip_sal_calculation:
#             data.append(data_row)
#             continue

#         monthly_salary = round(emp.ctc / 12)
#         # net_payable_salary = round(emp.ctc / 12)
#         pt_deduction = 0.00
#         other_deductions = 0.00
#         insurance_deductions = 0.00
#         lwp = 0

#         if monthly_salary >= 25000 and professional_tax_applicable == 1:
#             pt_deduction = 200

#         if emp.name in leave_emp_map:
#             lwp = leave_emp_map[emp.name]
#         # print("lwppppppppppppp",lwp)
#         # net_payable_salary = round((monthly_salary / 30) * (30 - lwp-absent_marked_days-not_marked_days) - (pt_deduction + other_deductions),0)
#         net_payable_salary = round((monthly_salary / 30) * (30 - lwp - unadjusted_count) - (pt_deduction + other_deductions + insurance_deductions),0)


#         data_row["monthly_salary"] = monthly_salary
#         data_row["pt_deduction"] = pt_deduction
#         data_row["insurance_deductions"] = insurance_deductions
#         data_row["other_deductions"] = other_deductions
#         data_row["lwp"] = lwp
        
#         data_row["net_payable_salary"] = net_payable_salary
#         # print("data_row_complete",data_row)
#         data.append(data_row)
#     holidays_in_month = "\n".join([f"{str(i)}<br>" for i in holidays_in_month])
#     return data,leave_emp_map, leave_data_to_view,holidays_in_month, professional_tax_applicable


# def get_first_and_last_date_of_month(fy, mon):
#     # Split the financial year into start and end years
#     start_year, end_year = map(int, fy.split('-'))

#     # Map month names to month numbers
#     months = {
#         "January": 1, "February": 2, "March": 3, "April": 4,
#         "May": 5, "June": 6, "July": 7, "August": 8,
#         "September": 9, "October": 10, "November": 11, "December": 12
#     }

#     # Get the month number
#     month_number = months[mon]

#     # Determine the actual year for the given month in the FY
#     if month_number >= 4:  # April to December
#         year = start_year
#     else:  # January to March
#         year = end_year

#     # Get the first date of the month
#     first_date = date(year, month_number, 1)

#     # Get the last date of the month
#     last_date = date(year, month_number, calendar.monthrange(year, month_number)[1])

#     return first_date, last_date





# def get_holidays_in_month(start_of_month, end_of_month):
#     """
#     Return a set of holiday date objects from the relevant Holiday List(s)
#     whose from_date <= start_of_month and to_date >= end_of_month.

#     :param start_of_month: A datetime.date object for the 1st day of the month
#     :param end_of_month:   A datetime.date object for the last day of the month
#     :return: A set of Python date objects (the holiday dates in that month range).
#     """
#     # Step 1: Find matching Holiday List(s)
#     # We'll filter on from_date <= start_of_month AND to_date >= end_of_month
#     holiday_list_records = frappe.get_all(
#         "Holiday List",
#         filters={
#             "from_date": ("<=", start_of_month),
#             "to_date": (">=", end_of_month),
#         },
#         fields=["name", "from_date", "to_date"]
#     )

#     # If no matching holiday list, return an empty set
#     if not holiday_list_records:
#         return set()

#     # Step 2: Collect holidays from each matching Holiday List
#     holiday_dates = set()

#     for hl_rec in holiday_list_records:
#         holiday_list_doc = frappe.get_doc("Holiday List", hl_rec["name"])

#         # Step 3: Loop over child holiday rows in the doc
#         for h in holiday_list_doc.holidays:
#             # If it's a string like "2024-01-07", parse it, else use the date
#             holiday_date = h.holiday_date
#             if isinstance(holiday_date, str):
#                 holiday_date = datetime.strptime(holiday_date, "%Y-%m-%d").date()

#             # Include only if it's within [start_of_month..end_of_month]
#             if start_of_month <= holiday_date <= end_of_month:
#                 holiday_dates.add(holiday_date)

#     return holiday_dates



# def get_leave_days_of_current_month(leave_application, first_date, last_date, holidays_in_month):
#     """
#     Calculate how many days from 'leave_application' fall within [first_date..last_date],
#     excluding any holidays in 'holidays_in_month'.

#     :param leave_application: dict with keys:
#         - "from_date" (str or date) in DD-MM-YYYY,
#         - "to_date"   (str or date) in DD-MM-YYYY,
#         - "half_day"  (bool),
#         - "half_day_date" (str or date) in DD-MM-YYYY.
#     :param first_date: A date object for the first day of the month.
#     :param last_date:  A date object for the last day of the month.
#     :param holidays_in_month: A set (or list) of date objects representing holidays in this month.
#     :return: float (the number of leave days in the current month, after excluding holidays).
#     """
#     # 1) Parse from_date, to_date, half_day_date from strings if needed
#     from_date = leave_application.get("from_date")  # e.g. "06-01-2025"
#     to_date = leave_application.get("to_date")      # e.g. "10-01-2025"
#     half_day_date = leave_application.get("half_day_date")  # e.g. "10-01-2025"

#     if isinstance(from_date, str):
#         from_date = datetime.strptime(from_date, "%d-%m-%Y").date()
#     if isinstance(to_date, str):
#         to_date = datetime.strptime(to_date, "%d-%m-%Y").date()

#     # 2) Determine overlap window
#     overlap_start = max(from_date, first_date)
#     overlap_end = min(to_date, last_date)

#     # If no overlap, zero days
#     if overlap_start > overlap_end:
#         return 0

#     # 3) Create a list (or set) of all dates in the overlap
#     overlap_length = (overlap_end - overlap_start).days + 1
#     overlap_dates = [
#         overlap_start + timedelta(days=i)
#         for i in range(overlap_length)
#     ]

#     # 4) Exclude holidays
#     #    'holidays_in_month' should be a set of date objects
#     working_overlap_dates = [
#         d for d in overlap_dates if d not in holidays_in_month
#     ]

#     leave_days_current_month = float(len(working_overlap_dates))

#     # 5) If half-day is indicated, only subtract 0.5 if the half-day date is within 'working_overlap_dates'
#     if leave_application.get("half_day") and leave_days_current_month > 0:
#         if half_day_date:
#             if isinstance(half_day_date, str):
#                 half_day_date = datetime.strptime(half_day_date, "%d-%m-%Y").date()
#             if half_day_date in working_overlap_dates:
#                 leave_days_current_month -= 0.5

#     # 6) Safety net
#     if leave_days_current_month < 0:
#         leave_days_current_month = 0

#     return leave_days_current_month


# def get_employee_leave_data(active_employees,to_date,from_date):
    
#     precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
#     # consolidate_leave_types = len(active_employees) > 1 and filters.consolidate_leave_types
#     leave_types = frappe.get_all("Leave Type", pluck="name")
#     row = None

#     data = []

#     data = []
#     if active_employees:
#         for leave_type in leave_types:
            
#             row = frappe._dict({"leave_type": leave_type})

#             for employee in active_employees:
#                 row = frappe._dict({"leave_type": leave_type})

#                 row.employee = employee.name
#                 row.employee_name = employee.employee_name

#                 leaves_taken = (
#                     get_leaves_for_period(employee.name, leave_type, from_date, to_date) * -1
#                 )

#                 new_allocation, expired_leaves, carry_forwarded_leaves = get_allocated_and_expired_leaves(
#                     from_date, to_date, employee.name, leave_type
#                 )
#                 opening = get_opening_balance(employee.name, leave_type, from_date, carry_forwarded_leaves)

#                 row.leaves_allocated = flt(new_allocation, precision)
#                 row.leaves_expired = flt(expired_leaves, precision)
#                 row.opening_balance = flt(opening, precision)
#                 row.leaves_taken = flt(leaves_taken, precision)

#                 closing = new_allocation + opening - (row.leaves_expired + leaves_taken)
#                 row.closing_balance = flt(closing, precision)
#                 if leave_type=="Leave Without Pay":
#                     row.closing_balance = 0

#                 row.indent = 1
#                 data.append(row)

#     return data


# def get_allocated_and_expired_leaves(
# 	from_date: str, to_date: str, employee: str, leave_type: str
# ) -> tuple[float, float, float]:
# 	new_allocation = 0
# 	expired_leaves = 0
# 	carry_forwarded_leaves = 0

# 	records = get_leave_ledger_entries(from_date, to_date, employee, leave_type)

# 	for record in records:
# 		# new allocation records with `is_expired=1` are created when leave expires
# 		# these new records should not be considered, else it leads to negative leave balance
# 		if record.is_expired:
# 			continue

# 		if record.to_date < getdate(to_date):
# 			# leave allocations ending before to_date, reduce leaves taken within that period
# 			# since they are already used, they won't expire
# 			expired_leaves += record.leaves
# 			leaves_for_period = get_leaves_for_period(
# 				employee, leave_type, record.from_date, record.to_date
# 			)
# 			expired_leaves -= min(abs(leaves_for_period), record.leaves)

# 		if record.from_date >= getdate(from_date):
# 			if record.is_carry_forward:
# 				carry_forwarded_leaves += record.leaves
# 			else:
# 				new_allocation += record.leaves

# 	return new_allocation, expired_leaves, carry_forwarded_leaves


# def get_opening_balance(
# 	employee: str, leave_type: str, from_date, carry_forwarded_leaves: float
# ) -> float:
# 	# allocation boundary condition
# 	# opening balance is the closing leave balance 1 day before the filter start date
# 	opening_balance_date = add_days(from_date, -1)
# 	allocation = get_previous_allocation(from_date, leave_type, employee)

# 	if (
# 		allocation
# 		and allocation.get("to_date")
# 		and opening_balance_date
# 		and getdate(allocation.get("to_date")) == getdate(opening_balance_date)
# 	):
# 		# if opening balance date is same as the previous allocation's expiry
# 		# then opening balance should only consider carry forwarded leaves
# 		opening_balance = carry_forwarded_leaves
# 	else:
# 		# else directly get leave balance on the previous day
# 		opening_balance = get_leave_balance_on(employee, leave_type, opening_balance_date)

# 	return opening_balance

# def get_leave_ledger_entries(
# 	from_date: str, to_date: str, employee: str, leave_type: str
# ) -> list[dict]:
# 	ledger = frappe.qb.DocType("Leave Ledger Entry")
# 	return (
# 		frappe.qb.from_(ledger)
# 		.select(
# 			ledger.employee,
# 			ledger.leave_type,
# 			ledger.from_date,
# 			ledger.to_date,
# 			ledger.leaves,
# 			ledger.transaction_name,
# 			ledger.transaction_type,
# 			ledger.is_carry_forward,
# 			ledger.is_expired,
# 		)
# 		.where(
# 			(ledger.docstatus == 1)
# 			& (ledger.transaction_type == "Leave Allocation")
# 			& (ledger.employee == employee)
# 			& (ledger.leave_type == leave_type)
# 			& (
# 				(ledger.from_date[from_date:to_date])
# 				| (ledger.to_date[from_date:to_date])
# 				| ((ledger.from_date < from_date) & (ledger.to_date > to_date))
# 			)
# 		)
# 	).run(as_dict=True)




