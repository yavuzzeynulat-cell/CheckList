"""Gercek DataGrid'lerin basliklariyla kucuk test dosyalari."""
import openpyxl

RIA_HEADER = ["Department Codes", "Document Number", "Revision", "Document Title", "Date and time for Inspection",
              "Action Status", "RIA Status"]
CHECK_HEADER = ["Task Number", "Task Number", "Task ID", "Status", "Checklist WF", "Task Title", "Related RIA",
                "Section"]
LAB_HEADER = ["Related RIA", "Document Number", "Document Title"]


def xlsx(path, header, rows, sheet="Sheet"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(header)
    for r in rows:
        ws.append(r)
    wb.save(path)
    return path


def ria(number, title="Concrete pouring", status="Closed"):
    return ["ST-Structures", number, "0", title, "25/04/2025 09:00", status, "APPROVED"]


def check(task, related, status="OPEN"):
    return [task, None, 1, status, "WF1-Site Supervisor", "CHECKLIST FOR WORKS", related, "4"]
