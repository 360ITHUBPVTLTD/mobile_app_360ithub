import io
import frappe
from frappe.utils import today, getdate, get_datetime, get_url
from datetime import datetime, time, timedelta
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# Formatting Constants
HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
CELL_FONT = Font(name="Calibri", size=11)
BORDER_SIDE = Side(border_style="thin", color="D9D9D9")
THIN_BORDER = Border(left=BORDER_SIDE, right=BORDER_SIDE, top=BORDER_SIDE, bottom=BORDER_SIDE)
CENTER_ALIGN = Alignment(horizontal="center", vertical="center")
LEFT_ALIGN = Alignment(horizontal="left", vertical="center")

def make_form_url(doctype: str, name: str) -> str:
    """Generate a direct browser hyperlink to a Frappe document form."""
    site_url = get_url()
    slug = doctype.lower().replace(" ", "-")
    return f"{site_url}/app/{slug}/{name}"

def format_date_dmy(date_val) -> str:
    """Convert any date input to dd-mm-yyyy format."""
    if not date_val:
        return "-"
    try:
        return getdate(date_val).strftime('%d-%m-%Y')
    except Exception:
        return str(date_val)

def is_working_day(check_date) -> bool:
    """
    Returns True if check_date is a working day based on the company's Holiday List.
    Only skips days that are explicitly listed as holidays — weekends are NOT
    skipped unless they appear in the Holiday List.
    """
    check_date = getdate(check_date)

    # Try to find the default Holiday List from the default company
    holiday_list_name = None
    try:
        default_company = frappe.db.get_single_value("Global Defaults", "default_company")
        if default_company:
            holiday_list_name = frappe.db.get_value("Company", default_company, "default_holiday_list")
    except Exception:
        pass

    if not holiday_list_name:
        frappe.logger().info("Daily Attendance Report: No Holiday List configured, treating all days as working days.")
        return True

    # Check if the date is explicitly listed as a holiday
    is_holiday = frappe.db.exists("Holiday", {
        "parent": holiday_list_name,
        "holiday_date": check_date
    })
    if is_holiday:
        frappe.logger().info(
            f"Daily Attendance Report skipped: {check_date.strftime('%d-%m-%Y')} is a holiday in '{holiday_list_name}'."
        )
        return False

    return True

@frappe.whitelist()
def send_daily_attendance_report():
    """Triggered daily to check settings, build the Excel report, and email it."""
    # 1. Fetch & Validate Settings
    settings = frappe.get_single("Mobile App Admin Settings")
    
    if not settings.get("custom_enable_daily_attendance_report"):
        frappe.logger().info("Daily Attendance Report is disabled in settings.")
        return

    emails_str = settings.get("custom_daily_attendance_report_emails")
    if not emails_str:
        frappe.log_error("Daily Attendance Report skipped: No recipient emails configured.", "Attendance Report Error")
        return

    recipients = [e.strip() for e in emails_str.split(",") if e.strip()]
    if not recipients:
        frappe.log_error("Daily Attendance Report skipped: No valid emails parsed.", "Attendance Report Error")
        return

    # 2. Get today's date and check if it's a working day per the Holiday List
    today_date = getdate(today())
    if not is_working_day(today_date):
        return

    try:
        # 3. Generate Excel fully in-memory (no temp file, no File doctype record)
        excel_buffer = io.BytesIO()
        counts = build_excel_report(excel_buffer, today_date)

        # 4. Email Report with a beautiful HTML summary
        subject = f"Daily Attendance & Leave Report - {format_date_dmy(today_date)}"
        
        report_date_str = today_date.strftime('%A, %d-%b-%Y')
        
        html_message = f"""
        <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #fcfcfc;">
            <div style="background-color: #1f4e78; color: #ffffff; padding: 20px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px;">
                <h2 style="margin: 0; font-size: 22px; font-weight: 600; letter-spacing: 0.5px;">Daily Attendance & Leave Report</h2>
                <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">Date: {report_date_str}</p>
            </div>
            
            <div style="padding: 24px; color: #333333; line-height: 1.6;">
                <p style="margin-top: 0; font-size: 16px;">Dear Sir/HR Team,</p>
                <p style="font-size: 15px; color: #555555;">Please find below today's daily attendance summary. The detailed report has been attached to this email as an Excel spreadsheet.</p>
                
                <!-- Summary Cards -->
                <table style="width: 100%; border-collapse: collapse; margin: 24px 0;">
                    <tr>
                        <td style="width: 50%; padding: 10px; box-sizing: border-box;">
                            <div style="background-color: #ebf3fc; border-left: 4px solid #1f4e78; padding: 15px; border-radius: 4px; text-align: center;">
                                <span style="display: block; font-size: 13px; color: #555555; font-weight: 600; margin-bottom: 5px;">Today's Presence</span>
                                <strong style="font-size: 24px; color: #1f4e78;">{counts['presence']}</strong>
                            </div>
                        </td>
                        <td style="width: 50%; padding: 10px; box-sizing: border-box;">
                            <div style="background-color: #fff8e7; border-left: 4px solid #ffb22b; padding: 15px; border-radius: 4px; text-align: center;">
                                <span style="display: block; font-size: 13px; color: #555555; font-weight: 600; margin-bottom: 5px;">Today's Late Comers </span>
                                <strong style="font-size: 24px; color: #ffb22b;">{counts['late']}</strong>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td style="width: 50%; padding: 10px; box-sizing: border-box;">
                            <div style="background-color: #edfaf1; border-left: 4px solid #2ecc71; padding: 15px; border-radius: 4px; text-align: center;">
                                <span style="display: block; font-size: 13px; color: #555555; font-weight: 600; margin-bottom: 5px;">Today's Approved Leaves</span>
                                <strong style="font-size: 24px; color: #2ecc71;">{counts['approved']}</strong>
                            </div>
                        </td>
                        <td style="width: 50%; padding: 10px; box-sizing: border-box;">
                            <div style="background-color: #fdf2f2; border-left: 4px solid #e74c3c; padding: 15px; border-radius: 4px; text-align: center;">
                                <span style="display: block; font-size: 13px; color: #555555; font-weight: 600; margin-bottom: 5px;">Today's Unapproved Leaves</span>
                                <strong style="font-size: 24px; color: #e74c3c;">{counts['unapproved']}</strong>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="2" style="padding: 10px; box-sizing: border-box;">
                            <div style="background-color: #f5eef8; border-left: 4px solid #8e44ad; padding: 15px; border-radius: 4px; text-align: center;">
                                <span style="display: block; font-size: 13px; color: #555555; font-weight: 600; margin-bottom: 5px;">No Checkin / Leave Record</span>
                                <strong style="font-size: 24px; color: #8e44ad;">{counts['no_record']}</strong>
                            </div>
                        </td>
                    </tr>
                </table>
                
            </div>
            
            <div style="background-color: #f1f1f1; color: #777777; padding: 15px; text-align: center; font-size: 12px; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; border-top: 1px solid #e0e0e0;">
                Regards,<br>
                <strong>HR Department,<br>Dac's Inc</strong>
            </div>
        </div>
        """
        
        # Attach the in-memory bytes directly — frappe.sendmail builds the MIME
        # attachment from fname/fcontent without persisting a File doctype record
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=html_message,
            attachments=[{
                "fname": f"Daily_Attendance_Report_{today_date.strftime('%Y-%m-%d')}.xlsx",
                "fcontent": excel_buffer.getvalue()
            }]
        )
        frappe.logger().info(f"Daily Attendance Report emailed successfully to {', '.join(recipients)}.")

    except Exception as e:
        frappe.log_error(title="Failed to build/send Daily Attendance Report", message=frappe.get_traceback())

def build_excel_report(file_or_buffer, report_date):
    """Builds the 5-tab workbook using openpyxl. `file_or_buffer` may be a
    file path or a file-like object (e.g. io.BytesIO) — openpyxl supports both."""
    wb = openpyxl.Workbook()
    
    # Tab 1: Today's Team Presence
    ws1 = wb.active
    ws1.title = "Today's Presence"
    presence_count = build_presence_sheet(ws1, report_date)
    
    # Tab 2: Today's Approved Leaves
    ws2 = wb.create_sheet("Approved Leaves")
    approved_count = build_leaves_sheet(ws2, report_date, status="Approved")
    
    # Tab 3: Today's Unapproved Leaves
    ws3 = wb.create_sheet("Unapproved Leaves")
    unapproved_count = build_leaves_sheet(ws3, report_date, status="Open") # Open/Pending leaves
    
    # Tab 4: Today's Late Comers
    ws4 = wb.create_sheet("Late Comers")
    late_count = build_late_comers_sheet(ws4, report_date)

    # Tab 5: Active employees with no Checkin or Leave Application record today
    ws5 = wb.create_sheet("No Record")
    no_record_count = build_missing_records_sheet(ws5, report_date)

    wb.save(file_or_buffer)

    return {
        "presence": presence_count,
        "approved": approved_count,
        "unapproved": unapproved_count,
        "late": late_count,
        "no_record": no_record_count
    }

def style_sheet(ws, headers: list):
    """Applies premium headers, fonts, and column auto-adjusting to a worksheet."""
    # Write Headers
    ws.append(headers)
    
    # Format Header Row
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = CENTER_ALIGN
        cell.border = THIN_BORDER
    
    ws.row_dimensions[1].height = 25
    
    # Freeze the header row so it stays visible when scrolling down
    ws.freeze_panes = "A2"

def finalize_rows_style(ws, num_cols: int):
    """Align rows and auto-fit column widths."""
    for row in range(2, ws.max_row + 1):
        ws.row_dimensions[row].height = 20
        for col in range(1, num_cols + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = CELL_FONT
            cell.border = THIN_BORDER
            
            # Align center if date, time, status, number
            val_str = str(cell.value or "")
            if cell.hyperlink or "@" in val_str:
                cell.font = Font(name="Calibri", size=11, color="0563C1", underline="single")
            
            # Formatting for dates, statuses or IDs
            if col in [1, 2, 5, 6, 7]:  # Align center for IDs, date/time fields
                cell.alignment = CENTER_ALIGN
            else:
                cell.alignment = LEFT_ALIGN
                
    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val = str(cell.value or "")
            # Don't size columns based on huge URLs
            if cell.hyperlink:
                val = "View Document"
            max_len = max(max_len, len(val))
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

def build_presence_sheet(ws, report_date):
    """Fetches and builds the team presence sheet using Employee Checkin records (Present & Half Day)."""
    headers = ["Employee ID", "Employee Name", "Department", "Status", "Check-in Time", "Check-out Time", "Working Hours"]
    style_sheet(ws, headers)
    
    # Get all check-ins for the report date
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "time": ["between", [f"{report_date} 00:00:00", f"{report_date} 23:59:59"]]
        },
        fields=["employee", "log_type", "time"],
        order_by="time asc"
    )
    
    # Group check-ins by employee to determine first IN and last OUT
    emp_data = {}
    for c in checkins:
        emp = c.employee
        if emp not in emp_data:
            try:
                emp_doc = frappe.get_cached_doc("Employee", emp)
                emp_name = emp_doc.employee_name
                emp_dept = emp_doc.department or "-"
            except Exception:
                emp_name = emp
                emp_dept = "-"
                
            emp_data[emp] = {
                "name": emp_name,
                "dept": emp_dept,
                "first_in": None,
                "last_out": None
            }
        
        c_time = get_datetime(c.time)
        if c.log_type == "IN":
            if not emp_data[emp]["first_in"]:
                emp_data[emp]["first_in"] = c_time
        elif c.log_type == "OUT":
            emp_data[emp]["last_out"] = c_time

    count = 0
    for emp, data in sorted(emp_data.items()):
        in_time_str = data["first_in"].strftime("%I:%M %p") if data["first_in"] else "-"
        out_time_str = data["last_out"].strftime("%I:%M %p") if data["last_out"] else "-"
        
        # Calculate working hours if both IN and OUT exist
        working_hours = "-"
        if data["first_in"] and data["last_out"]:
            diff = data["last_out"] - data["first_in"]
            hours = diff.total_seconds() / 3600.0
            working_hours = f"{hours:.2f}"
            
        row_data = [
            emp,
            data["name"],
            data["dept"],
            "Present",
            in_time_str,
            out_time_str,
            working_hours
        ]
        ws.append(row_data)
        count += 1
        
        # Link Employee ID to standard DocType view
        cell = ws.cell(row=ws.max_row, column=1)
        cell.hyperlink = make_form_url("Employee", emp)

    finalize_rows_style(ws, len(headers))
    return count

def build_leaves_sheet(ws, report_date, status="Approved"):
    """Fetches and builds the approved or unapproved leaves sheet."""
    # First column is Leave Application ID linking to Leave Application
    headers = ["Leave ID", "Employee ID", "Employee Name", "Department", "Leave Type", "From Date", "To Date", "Total Days", "Half Day", "Approver Name"]
    style_sheet(ws, headers)
    
    # Check if custom_approved_by exists on Leave Application to avoid database query errors
    fields = ["name", "employee", "employee_name", "department", "leave_type", "from_date", "to_date", "total_leave_days", "half_day", "leave_approver"]
    if frappe.get_meta("Leave Application").has_field("custom_approved_by"):
        fields.append("custom_approved_by")
    
    # Filter for leaves active today
    leaves = frappe.get_all(
        "Leave Application",
        filters={
            "status": status,
            "from_date": ["<=", report_date],
            "to_date": [">=", report_date],
            "docstatus": 1 if status == "Approved" else 0  # Approved leaves are submitted (docstatus=1)
        },
        fields=fields,
        order_by="employee asc"
    )
    
    count = 0
    for leave in leaves:
        approver_email = leave.get("custom_approved_by") or leave.leave_approver
        approver_name = "-"
        if approver_email:
            approver_name = frappe.db.get_value("User", approver_email, "full_name") or approver_email
            
        row_data = [
            leave.name,
            leave.employee,
            leave.employee_name,
            leave.department or "-",
            leave.leave_type,
            format_date_dmy(leave.from_date),
            format_date_dmy(leave.to_date),
            leave.total_leave_days,
            "Yes" if leave.half_day else "No",
            approver_name
        ]
        ws.append(row_data)
        count += 1
        
        # Link Leave ID to Leave Application DocType form view instead of Employee
        cell = ws.cell(row=ws.max_row, column=1)
        cell.hyperlink = make_form_url("Leave Application", leave.name)

    finalize_rows_style(ws, len(headers))
    return count

def build_late_comers_sheet(ws, report_date):
    """Fetches and builds the sheet for employees arriving late based on actual shifts (> 10:15 AM)."""
    headers = ["Employee ID", "Employee Name", "Department", "Shift Type", "Check-in Time", "Late Time"]
    style_sheet(ws, headers)
    
    # Get all check-ins for the report date
    checkins = frappe.get_all(
        "Employee Checkin",
        filters={
            "log_type": "IN",
            "time": ["between", [f"{report_date} 00:00:00", f"{report_date} 23:59:59"]]
        },
        fields=["employee", "time"],
        order_by="time asc"
    )
    
    # Only process the first check-in of each employee
    processed_employees = set()
    from hrms.hr.doctype.shift_assignment.shift_assignment import get_employee_shift
    
    count = 0
    for c in checkins:
        emp = c.employee
        if emp in processed_employees:
            continue
        processed_employees.add(emp)
        
        in_time_dt = get_datetime(c.time)
        
        # Get actual employee shift details
        shift_details = get_employee_shift(emp, in_time_dt, consider_default_shift=True)
        if not shift_details:
            continue
            
        shift_type_name = shift_details.get("shift_type", {}).get("name")
        if shift_type_name == "No Punch Needed":
            continue
            
        shift_start = shift_details.get("start_datetime")
        if not shift_start:
            continue
            
        # 15 minutes grace period
        late_threshold = shift_start + timedelta(minutes=15)
        
        # We classify them as late comers if they check in past the late threshold
        if in_time_dt > late_threshold:
            diff_mins = int((in_time_dt - shift_start).total_seconds() / 60)
            
            # Format diff_mins to friendly hours & minutes representation
            hours = diff_mins // 60
            minutes = diff_mins % 60
            if hours > 0:
                late_time_str = f"{hours} hr {minutes} mins"
            else:
                late_time_str = f"{minutes} mins"
                
            # Format Shift Type and Start/End Time in the same line/cell
            shift_start_time = shift_details.get("shift_type", {}).get("start_time")
            shift_end_time = shift_details.get("shift_type", {}).get("end_time")
            
            if isinstance(shift_start_time, timedelta):
                shift_start_time_str = (datetime.min + shift_start_time).strftime("%I:%M %p")
            else:
                shift_start_time_str = str(shift_start_time)
                
            if isinstance(shift_end_time, timedelta):
                shift_end_time_str = (datetime.min + shift_end_time).strftime("%I:%M %p")
            else:
                shift_end_time_str = str(shift_end_time)
                
            shift_details_str = f"{shift_type_name} ({shift_start_time_str} - {shift_end_time_str})"
            
            try:
                emp_doc = frappe.get_cached_doc("Employee", emp)
                emp_name = emp_doc.employee_name
                emp_dept = emp_doc.department or "-"
            except Exception:
                emp_name = emp
                emp_dept = "-"
            
            row_data = [
                emp,
                emp_name,
                emp_dept,
                shift_details_str,
                in_time_dt.strftime("%I:%M %p"),
                late_time_str
            ]
            ws.append(row_data)
            count += 1
            
            # Link Employee ID to form view
            cell = ws.cell(row=ws.max_row, column=1)
            cell.hyperlink = make_form_url("Employee", emp)

    finalize_rows_style(ws, len(headers))
    return count

def build_missing_records_sheet(ws, report_date):
    """Fetches and builds the sheet for active employees who have neither an
    Employee Checkin nor a Leave Application (Approved/Open) covering the report date."""
    headers = ["Employee ID", "Employee Name", "Department", "Designation", "Reporting Manager"]
    style_sheet(ws, headers)

    # Only consider employees who were already active and joined on/before the report date
    employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active",
            "date_of_joining": ["<=", report_date]
        },
        fields=["name", "employee_name", "department", "designation", "reports_to"],
        order_by="employee_name asc"
    )

    checked_in = set(frappe.get_all(
        "Employee Checkin",
        filters={
            "time": ["between", [f"{report_date} 00:00:00", f"{report_date} 23:59:59"]]
        },
        pluck="employee"
    ))

    on_leave = set(frappe.get_all(
        "Leave Application",
        filters={
            "status": ["in", ["Approved", "Open"]],
            "from_date": ["<=", report_date],
            "to_date": [">=", report_date]
        },
        pluck="employee"
    ))

    count = 0
    for emp in employees:
        if emp.name in checked_in or emp.name in on_leave:
            continue

        manager_name = "-"
        if emp.reports_to:
            manager_name = frappe.db.get_value("Employee", emp.reports_to, "employee_name") or emp.reports_to

        row_data = [
            emp.name,
            emp.employee_name,
            emp.department or "-",
            emp.designation or "-",
            manager_name
        ]
        ws.append(row_data)
        count += 1

        # Link Employee ID to form view
        cell = ws.cell(row=ws.max_row, column=1)
        cell.hyperlink = make_form_url("Employee", emp.name)

    finalize_rows_style(ws, len(headers))
    return count
