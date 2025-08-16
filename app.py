#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HR Contracts Manager - Dark Desktop EXE
Developed by azooz  |  Email: m_azoz84@yahoo.com  |  Version: V01.2

هذا الإصدار يُنفّذ المطلوب تمامًا:
- الحــالة لون فقط (دائرة) بلا أي أرقام.
- عرض الحــالة في أقصى اليمين (عمود مستقل بالصور)، والجدول الرئيسي كما هو.
- استخدام صور الدوائر من assets/status_icons (green/yellow/red/gray). إن لم تتوفر، يسقط إلى إيموجي (🟢/🟡/🔴/⚪) بلا أرقام.
- تذييل مُرتّب: المطوّر يسار، الإصدار بالوسط، البريد في أقصى اليمين (بدون كلمة Email).
- الحفاظ على بقية السلوك كما كان.
"""

import os, sys, sqlite3, csv, traceback
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import tkinter.font as tkfont

# Optional features
try:
    from tkcalendar import DateEntry
    HAS_DATEENTRY = True
except Exception:
    HAS_DATEENTRY = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except Exception:
    HAS_FPDF = False

# === إعدادات عامة ===
ADMIN_PASSWORD = "Admin@123$"
APP_NAME = "HR Contracts Manager"
APP_VERSION = "V01.2"
REMINDER_DAYS_DEFAULT = 30

# إن True يستعمل الإيموجي كنص احتياطي فقط إن لم تتوفر الصور (بدون أرقام).
USE_EMOJI_STATUS = True

def resource_path(*parts):
    """يدعم التشغيل من exe أو من السورس."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        exe_dir = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))
        exe_dir = base_path
    if parts and parts[0] == 'writable':
        return os.path.join(exe_dir, *parts[1:])
    return os.path.join(base_path, *parts)

DB_PATH = resource_path('writable', 'hr.db')
ICON_PATH = resource_path('assets', 'app.ico')
LOGO_PATH = resource_path('assets', 'logo.png')
STATUS_DIR = resource_path('assets', 'status_icons')

def _ensure_dirs():
    try:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        os.makedirs(STATUS_DIR, exist_ok=True)
    except Exception:
        pass

def _log_exception(e):
    """تسجيل أي خطأ في writable/error.log"""
    try:
        _ensure_dirs()
        log_path = resource_path('writable', 'error.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*70 + "\n")
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            traceback.print_exc(file=f)
    except Exception:
        pass

# ----------------------- قاعدة البيانات -----------------------
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            national_id TEXT,
            residency_no TEXT,
            job_title TEXT,
            phone TEXT,
            email TEXT,
            contract_start TEXT,
            contract_end TEXT,
            residency_expiry TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def insert_employee(data):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO employees (full_name, national_id, residency_no, job_title, phone, email,
                               contract_start, contract_end, residency_expiry, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()

def update_employee(emp_id, data):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        UPDATE employees
        SET full_name=?, national_id=?, residency_no=?, job_title=?, phone=?, email=?,
            contract_start=?, contract_end=?, residency_expiry=?, notes=?
        WHERE id=?
    """, (*data, emp_id))
    conn.commit()
    conn.close()

def delete_employee(emp_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('DELETE FROM employees WHERE id=?', (emp_id,))
    conn.commit()
    conn.close()

def fetch_employees():
    """مرتَّبة بالأقدمية حسب بداية العقد تصاعديًا (الأقدم أولاً)."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, full_name, national_id, residency_no, job_title, phone, email,
               contract_start, contract_end, residency_expiry, notes, created_at
        FROM employees
        ORDER BY
          CASE WHEN contract_start IS NULL OR contract_start='' THEN 1 ELSE 0 END,
          contract_start ASC,
          id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def export_csv(path):
    rows = fetch_employees()
    headers = ["id","full_name","national_id","residency_no","job_title","phone","email",
               "contract_start","contract_end","residency_expiry","notes","created_at"]
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def export_pdf_all(path):
    rows = fetch_employees()
    if not HAS_FPDF:
        messagebox.showwarning("مكتبة مفقودة",
                               "لتصدير PDF ركب مكتبة fpdf: pip install fpdf\nسيتم حفظ CSV بدلاً من PDF.")
        export_csv(path.replace('.pdf', '.csv'))
        return
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, txt="تقرير الموظفين", ln=True, align="C")
    pdf.ln(4)
    headers = ["الاسم","رقم الهوية","المسمى","نهاية العقد","انتهاء الإقامة"]
    colw = [60,40,40,30,30]
    for h,w in zip(headers,colw):
        pdf.cell(w, 8, h, border=1, align="C")
    pdf.ln()
    for r in rows:
        _, full_name, national_id, residency_no, job_title, phone, email, contract_start, contract_end, residency_expiry, notes, created_at = r
        pdf.cell(colw[0], 7, str(full_name or "-")[:30], border=1)
        pdf.cell(colw[1], 7, str(national_id or "-")[:15], border=1)
        pdf.cell(colw[2], 7, str(job_title or "-")[:15], border=1)
        pdf.cell(colw[3], 7, str(contract_end or "-")[:12], border=1)
        pdf.cell(colw[4], 7, str(residency_expiry or "-")[:12], border=1)
        pdf.ln()
    pdf.output(path)
    messagebox.showinfo("تم", f"تم حفظ PDF: {path}")

# ----------------------- تواريخ + الحالة -----------------------
ARABIC_TO_ENG_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def _normalize_date_string(s: str) -> str:
    if not s:
        return ""
    s = str(s).strip()
    s = s.translate(ARABIC_TO_ENG_DIGITS)
    for ch in [".", "/", "\\", "–", "—", "_", " "]:
        s = s.replace(ch, "-")
    while "--" in s:
        s = s.replace("--", "-")
    return s

def _parse(d):
    if not d:
        return None
    s = _normalize_date_string(d)
    patterns = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]
    for p in patterns:
        try:
            return datetime.strptime(s, p).date()
        except Exception:
            continue
    try:
        parts = [int(x) for x in s.split("-")]
        if len(parts) == 3:
            if len(s.split("-")[0]) == 4:
                y, m, d = parts
            else:
                d, m, y = parts
            return date(y, m, d)
    except Exception:
        pass
    return None

def _days_left(d, today=None):
    if not today:
        today = date.today()
    dt = _parse(d)
    if not dt:
        return None
    return (dt - today).days

def status_icon_key(contract_end, residency_expiry, today=None):
    """يُرجع مفتاح الأيقونة فقط (لون بدون رقم)."""
    if not today:
        today = date.today()
    d1 = _days_left(contract_end, today)
    d2 = _days_left(residency_expiry, today)
    candidates = [d for d in (d1, d2) if d is not None]
    if not candidates:
        return "gray"
    dmin = min(candidates)
    if dmin <= 15:
        return "red"
    elif dmin <= 30:
        return "yellow"
    else:
        return "green"

# ----------------------- الثيمات -----------------------
def apply_dark(root, style):
    try:
        style.theme_use("clam")
    except:
        pass
    bg = "#0F0F10"
    fg = "#EAEAEA"
    entry_bg = "#1A1A1C"
    accent = "#66B3FF"

    root.configure(bg=bg)
    style.configure(".", background=bg, foreground=fg, fieldbackground=entry_bg)
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg, font=("Arial", 14))
    style.configure("TButton", background=entry_bg, foreground=fg, borderwidth=0, padding=6, font=("Arial", 14, "bold"))
    style.map("TButton", background=[("active", "#2A2A2E")])

    style.configure("TEntry", fieldbackground=entry_bg, foreground=fg, insertcolor=fg)
    style.configure("TCombobox", fieldbackground=entry_bg, foreground=fg)

    style.configure("Treeview", relief="flat", bordercolor="#444", borderspacing=1,
                    background="#121214",
                    foreground=fg,
                    fieldbackground="#121214",
                    rowheight=28,
                    borderwidth=0,
                    font=("Segoe UI", 14))
    style.map("Treeview",
              background=[("selected", accent)],
              foreground=[("selected", "#000000")])
    style.configure("Treeview.Heading",
                    background="#1C1C1F",
                    foreground=fg,
                    relief="flat",
                    font=("Arial", 14, "bold"))
    style.configure("Info.TLabel", foreground="#A0A0A0", background=bg, font=("Arial", 11, "bold"))

def apply_light(root, style):
    try:
        style.theme_use("clam")
    except:
        pass
    bg = "#FAFAF0"
    fg = "#0B2E6F"
    accent = "#66B3FF"

    root.configure(bg=bg)
    style.configure(".", background=bg, foreground=fg, fieldbackground="#FFFFFF")
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=fg, font=("Arial", 14))
    style.configure("TButton", background="#F0F0F0", foreground=fg, borderwidth=0, padding=6, font=("Arial", 14, "bold"))
    style.map("TButton", background=[("active", "#E0E0E0")])

    style.configure("TEntry", fieldbackground="#FFFFFF", foreground=fg, insertcolor=fg)
    style.configure("TCombobox", fieldbackground="#FFFFFF", foreground=fg)

    style.configure("Treeview", relief="flat", bordercolor="#444", borderspacing=1,
                    background="#FFFFFF",
                    foreground=fg,
                    fieldbackground="#FFFFFF",
                    rowheight=28,
                    borderwidth=0,
                    font=("Segoe UI", 14))
    style.map("Treeview",
              background=[("selected", accent)],
              foreground=[("selected", "#000000")])
    style.configure("Treeview.Heading",
                    background="#E7E7E7",
                    foreground=fg,
                    relief="flat",
                    font=("Arial", 14, "bold"))
    style.configure("Info.TLabel", foreground="#666666", background=bg, font=("Arial", 11, "bold"))

# ----------------------- التطبيق الرئيسي -----------------------
class HRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        try:
            self.iconbitmap(ICON_PATH)
        except Exception:
            pass
        self.geometry("1200x700")

        self.style = ttk.Style(self)
        apply_dark(self, self.style)

        self.dialog_open = False
        self._status_warned_once = False
        self._syncing_select = False  # لمنع حلقة اختيار متبادل

        # تحميل أيقونات الحالة مع الاحتفاظ بالمراجع
        self.status_imgs = self._load_status_icons()

        # أعلى الشاشة
        top_bar = ttk.Frame(self, padding=8)
        top_bar.pack(fill="x")
        if os.path.exists(LOGO_PATH):
            try:
                logo_img = tk.PhotoImage(file=LOGO_PATH)
                self._logo_img_ref = logo_img
                lbl_logo = ttk.Label(top_bar, image=logo_img)
                lbl_logo.pack(side="left", padx=(6,12))
            except Exception as e:
                _log_exception(e)

        title_font = tkfont.Font(family="Arial", size=16, weight="bold")
        ttk.Label(top_bar, text=APP_NAME, font=title_font).pack(side="left")

        search_frame = ttk.Frame(top_bar)
        search_frame.pack(side="right")
        ttk.Label(search_frame, text="بحث ").pack(side="right")
        self.search_var = tk.StringVar()
        self.entry_search = ttk.Entry(search_frame, textvariable=self.search_var, width=30, font=("Arial",14))
        self.entry_search.pack(side="right", padx=6)
        self.entry_search.bind("<KeyRelease>", lambda e: self.refresh_tables())

        self.theme_var = tk.StringVar(value="dark")
        btn_theme = ttk.Button(top_bar, text="تبديل الوضع", command=self.toggle_theme)
        btn_theme.pack(side="right", padx=8)

        # أزرار التحكم
        btns = ttk.Frame(self, padding=(10,4))
        btns.pack(fill="x")
        ttk.Button(btns, text="إضافة موظف", command=self.add_employee).pack(side="left", padx=4, pady=6)
        ttk.Button(btns, text="تعديل", command=self.edit_employee).pack(side="left", padx=4, pady=6)
        ttk.Button(btns, text="حذف", command=self.delete_employee).pack(side="left", padx=4, pady=6)
        ttk.Button(btns, text="تصدير CSV", command=self.export_csv).pack(side="left", padx=4, pady=6)
        ttk.Button(btns, text="تصدير PDF", command=self.export_pdf).pack(side="left", padx=4, pady=6)
        ttk.Button(btns, text="التنبيهات", command=self.show_alerts).pack(side="left", padx=4, pady=6)

        # إطار الجداول (جدول البيانات + عمود الحالة بالصور إلى أقصى اليمين)
        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill="both", expand=True, padx=10, pady=10)

        # نستخدم grid داخل table_wrap
        table_wrap.grid_columnconfigure(0, weight=1)  # الجدول الرئيسي يتمدّد
        table_wrap.grid_rowconfigure(0, weight=1)

        # الجدول الرئيسي (بدون عمود الحالة)
        cols = ("رقم الموظف","الاسم","رقم الهوية","المسمى","الهاتف","البريد",
                "بداية العقد","نهاية العقد","انتهاء الإقامة","ملاحظات")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, anchor="center", width=120)
        self.tree.column("الاسم", width=200)
        self.tree.column("ملاحظات", width=260)
        self.tree.column("البريد", width=260)
        self.tree.grid(row=0, column=0, sticky="nsew")

        # عمود الحالة (Treeview مستقل على اليمين) لعرض الصورة فقط
        self.status_tree = ttk.Treeview(table_wrap, columns=(), show="tree headings")
        self.status_tree.heading("#0", text="الحالة")
        self.status_tree.column("#0", anchor="center", width=65, stretch=False)
        self.status_tree.grid(row=0, column=1, sticky="ns")  # على اليمين

        # أشرطة التمرير
        vbar = ttk.Scrollbar(table_wrap, orient="vertical")
        vbar.grid(row=0, column=2, sticky="ns")
        hbar = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=hbar.set)
        hbar.grid(row=1, column=0, sticky="ew")

        # ربط الشجرتين مع الشريط الرأسي (تمرير متزامن)
        def _yview(*args):
            self.tree.yview(*args)
            self.status_tree.yview(*args)
        vbar.configure(command=_yview)
        self.tree.configure(yscrollcommand=lambda *a: vbar.set(*a))
        self.status_tree.configure(yscrollcommand=lambda *a: vbar.set(*a))

        # مزامنة الاختيار بين الجدولين
        self.tree.bind("<<TreeviewSelect>>", self._sync_select_from_main)
        self.status_tree.bind("<<TreeviewSelect>>", self._sync_select_from_status)

        self.configure_status_tags()

        # تذييل: المطوّر يسار، الإصدار وسط، البريد يمين (بدون كلمة Email)
        footer = ttk.Frame(self, padding=8)
        footer.pack(fill="x")
        footer.columnconfigure(0, weight=1)
        footer.columnconfigure(1, weight=1)
        footer.columnconfigure(2, weight=1)
        lbl_dev = ttk.Label(footer, text=f"Developed by azooz", style="Info.TLabel")
        lbl_ver = ttk.Label(footer, text=f"Version: {APP_VERSION}", style="Info.TLabel")
        lbl_mail = ttk.Label(footer, text="m_azoz84@yahoo.com", style="Info.TLabel")
        lbl_dev.grid(row=0, column=0, sticky="w")
        lbl_ver.grid(row=0, column=1, sticky="n")
        lbl_mail.grid(row=0, column=2, sticky="e")

        self.refresh_tables()

    # --- تحميل الأيقونات ---
    def _load_status_icons(self):
        """يحاول تحميل (green/yellow/red/gray). يحتفظ بالمراجع ويُسقط للإيموجي عند الفشل."""
        icons = {"green": None, "yellow": None, "red": None, "gray": None}
        candidates = {
            "green": ["green.png", "circle_green.png", "status_green.png", "ok.png"],
            "yellow": ["yellow.png", "circle_yellow.png", "status_yellow.png", "warn.png"],
            "red": ["red.png", "circle_red.png", "status_red.png", "danger.png"],
            "gray": ["gray.png", "grey.png", "circle_gray.png", "status_gray.png", "unknown.png", "white.png"]
        }
        for key, names in candidates.items():
            for nm in names:
                p = os.path.join(STATUS_DIR, nm)
                if os.path.exists(p):
                    try:
                        img = tk.PhotoImage(file=p)
                        icons[key] = img
                        break
                    except Exception as e:
                        _log_exception(e)
                        continue
        return icons

    def configure_status_tags(self):
        dark = (self.theme_var.get() == "dark")
        bg_row = "#121214" if dark else "#FFFFFF"
        fg_row = "#EAEAEA" if dark else "#0B2E6F"
        for tag in ("status_ok","status_warn","status_danger","status_none"):
            self.tree.tag_configure(tag, background=bg_row, foreground=fg_row)
            self.status_tree.tag_configure(tag, background=bg_row, foreground=fg_row)

    def toggle_theme(self):
        if self.theme_var.get() == "dark":
            apply_light(self, self.style)
            self.theme_var.set("light")
        else:
            apply_dark(self, self.style)
            self.theme_var.set("dark")
        self.configure_status_tags()
        self.refresh_tables()

    def load_data(self):
        return fetch_employees()

    # --- مزامنة الاختيارات ---
    def _sync_select_from_main(self, _=None):
        if self._syncing_select: return
        try:
            self._syncing_select = True
            self.status_tree.selection_remove(self.status_tree.selection())
            for iid in self.tree.selection():
                if self.status_tree.exists(iid):
                    self.status_tree.selection_add(iid)
                    self.status_tree.see(iid)
        finally:
            self._syncing_select = False

    def _sync_select_from_status(self, _=None):
        if self._syncing_select: return
        try:
            self._syncing_select = True
            self.tree.selection_remove(self.tree.selection())
            for iid in self.status_tree.selection():
                if self.tree.exists(iid):
                    self.tree.selection_add(iid)
                    self.tree.see(iid)
        finally:
            self._syncing_select = False

    # --- تحديث الجدولين ---
    def refresh_tables(self):
        query = self.search_var.get().strip().lower()
        for r in self.tree.get_children():
            self.tree.delete(r)
        for r in self.status_tree.get_children():
            self.status_tree.delete(r)

        rows = self.load_data()
        today = date.today()

        serial = 0
        unreadable = []

        for r in rows:
            emp = {
                "id": r[0], "full_name": r[1], "national_id": r[2], "residency_no": r[3],
                "job_title": r[4], "phone": r[5], "email": r[6],
                "contract_start": r[7], "contract_end": r[8], "residency_expiry": r[9], "notes": r[10]
            }
            text = " ".join([str(v) for v in emp.values() if v])
            if query and query not in text.lower():
                continue

            serial += 1

            # تحقق من قابلية قراءة التواريخ
            if (emp["contract_end"] and not _parse(emp["contract_end"])) or \
               (emp["residency_expiry"] and not _parse(emp["residency_expiry"])):
                unreadable.append(f"{emp['full_name'] or emp['id']}")

            # مفتاح الأيقونة (لون فقط)
            key = status_icon_key(emp["contract_end"], emp["residency_expiry"], today)
            # وسم صف للمظهر (إن رغبت مستقبلاً)
            tag = {"green":"status_ok","yellow":"status_warn","red":"status_danger","gray":"status_none"}[key]

            # إدراج في الجدول الرئيسي
            self.tree.insert(
                "", "end", iid=str(emp["id"]), tags=(tag,),
                values=(
                    serial, emp["full_name"], emp["national_id"], emp["job_title"],
                    emp["phone"], emp["email"], emp["contract_start"], emp["contract_end"],
                    emp["residency_expiry"], emp["notes"] or ""
                )
            )

            # إدراج في جدول الحالة (صورة فقط – بلا أرقام)
            img = self.status_imgs.get(key)
            if img is not None:
                self.status_tree.insert("", "end", iid=str(emp["id"]), image=img, text="", tags=(tag,))
            else:
                # سقوط إلى إيموجي فقط (بدون نص/رقم)
                fallback = {"green":"🟢","yellow":"🟡","red":"🔴","gray":"⚪"} if USE_EMOJI_STATUS else {"green":"", "yellow":"", "red":"", "gray":""}
                self.status_tree.insert("", "end", iid=str(emp["id"]), text=fallback.get(key, ""), tags=(tag,))

        if unreadable and not self._status_warned_once:
            self._status_warned_once = True
            sample = "، ".join(unreadable[:6])
            more = "" if len(unreadable) <= 6 else f" ... وعدد آخر: {len(unreadable)-6}"
            messagebox.showwarning(
                "تنبيه التواريخ",
                f"بعض السجلات تحتوي تواريخ غير مقروءة، لذلك ظهرت حالة 'غير معروف':\n{sample}{more}\n\n"
                f"الرجاء استخدام صيغة مثل 2025-08-15 أو 15-08-2025 أو عبر منتقي التقويم."
            )

    def add_employee(self):
        if self.dialog_open:
            messagebox.showwarning("تنبيه", "نافذة الإدخال مفتوحة بالفعل.")
            return
        self.dialog_open = True
        def on_close_cb():
            self.dialog_open = False
        dlg = AddEditDialog(self, "إضافة موظف", on_close=on_close_cb)
        self.wait_window(dlg)
        if getattr(dlg, 'result', None):
            insert_employee(dlg.result)
            self.refresh_tables()
            messagebox.showinfo("تم", "تمت إضافة الموظف.")

    def get_selected_id(self):
        # نعطي الأولوية لاختيار الجدول الرئيسي
        sel = self.tree.selection()
        if not sel:
            sel = self.status_tree.selection()
        if not sel:
            messagebox.showwarning("تنبيه", "الرجاء اختيار موظف أولاً.")
            return None
        try:
            return int(sel[0])
        except:
            item = self.tree.item(sel[0]) if self.tree.exists(sel[0]) else self.status_tree.item(sel[0])
            # في الجدول الرئيسي القيمة الأولى هي الرقم التسلسلي؛ نعيد الـ iid بدل ذلك
            return int(sel[0])

    def edit_employee(self):
        if self.dialog_open:
            messagebox.showwarning("تنبيه", "نافذة الإدخال مفتوحة بالفعل.")
            return
        emp_id = self.get_selected_id()
        if not emp_id: return
        rows = fetch_employees()
        row = next((r for r in rows if r[0] == emp_id), None)
        if not row:
            messagebox.showerror("خطأ", "تعذر إيجاد السجل المحدد.")
            return
        current = (row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10])
        self.dialog_open = True
        def on_close_cb():
            self.dialog_open = False
        dlg = AddEditDialog(self, "تعديل بيانات", emp=current, on_close=on_close_cb)
        self.wait_window(dlg)
        if getattr(dlg, 'result', None):
            update_employee(emp_id, dlg.result)
            self.refresh_tables()
            messagebox.showinfo("تم", "تم تحديث بيانات الموظف.")

    def delete_employee(self):
        emp_id = self.get_selected_id()
        if not emp_id: return
        pwd = simpledialog.askstring("كلمة مرور حذف", "أدخل كلمة المرور للحذف:", show='*')
        if pwd is None:
            return
        if pwd != ADMIN_PASSWORD:
            messagebox.showerror("خطأ", "كلمة المرور غير صحيحة. عملية الحذف ملغاة.")
            return
        if messagebox.askyesno("تأكيد", "هل أنت متأكد من حذف هذا الموظف؟"):
            delete_employee(emp_id)
            self.refresh_tables()
            messagebox.showinfo("تم", "تم حذف الموظف.")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV","*.csv")], title="حفظ كـ CSV")
        if not path: return
        export_csv(path)
        messagebox.showinfo("تم", "تم تصدير البيانات إلى CSV.")

    def export_pdf(self):
        path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF","*.pdf")], title="حفظ كـ PDF")
        if not path: return
        export_pdf_all(path)

    def show_alerts(self):
        rows = fetch_employees()
        AlertsDialog(self, rows, days=REMINDER_DAYS_DEFAULT)

# ----------------------- نوافذ الإدخال والتنبيهات -----------------------
class AddEditDialog(tk.Toplevel):
    def __init__(self, master, title, emp=None, on_close=None):
        super().__init__(master)
        self.title(title)
        try:
            self.iconbitmap(ICON_PATH)
        except Exception:
            pass
        self.resizable(False, False)
        self.configure(bg=master['bg'])
        self.result = None
        self.on_close = on_close

        self.label_font = ("Arial", 14, "bold")
        self.entry_font = ("Arial", 14)

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)

        labels = [
            ("الاسم الكامل*", "full_name"),
            ("رقم الهوية / البطاقة*", "national_id"),
            ("المسمى الوظيفي*", "job_title"),
            ("الهاتف*", "phone"),
            ("البريد*", "email"),
            ("بداية العقد*", "contract_start"),
            ("نهاية العقد*", "contract_end"),
            ("انتهاء الإقامة*", "residency_expiry"),
            ("ملاحظات", "notes")
        ]
        self.vars = {}
        row_index_map = {}
        for i, (lbl, key) in enumerate(labels):
            row_index_map[key] = i
            l = ttk.Label(frm, text=lbl)
            l.grid(row=i, column=0, sticky="e", padx=6, pady=4)
            if key in ("contract_start","contract_end","residency_expiry") and HAS_DATEENTRY:
                ent = DateEntry(frm, width=18, date_pattern='yyyy-mm-dd', font=self.entry_font)
                ent.grid(row=i, column=1, sticky="w", padx=6, pady=4)
            else:
                ent = ttk.Entry(frm, width=44)
                ent.grid(row=i, column=1, sticky="w", padx=6, pady=4)
            try:
                ent.configure(font=self.entry_font)
                l.configure(font=self.label_font)
            except:
                pass
            self.vars[key] = ent

        start_row = row_index_map.get("contract_start", 5)
        ttk.Button(frm, text="اليوم", width=8, command=lambda: self._set_today("contract_start")).grid(row=start_row, column=2, padx=4)

        if emp:
            map_keys = ["full_name","national_id","residency_no","job_title","phone","email","contract_start","contract_end","residency_expiry","notes"]
            for i,key in enumerate(map_keys):
                if key == "residency_no":
                    continue
                if i < len(emp) and emp[i] is not None and key in self.vars:
                    try:
                        w = self.vars[key]
                        if HAS_DATEENTRY and isinstance(w, DateEntry) and key in ("contract_start","contract_end","residency_expiry"):
                            try:
                                w.set_date(_parse(emp[i]) or date.today())
                            except:
                                w.set_date(date.today())
                        else:
                            w.delete(0, tk.END)
                            w.insert(0, str(emp[i]))
                    except:
                        pass

        btns = ttk.Frame(frm)
        btns.grid(row=len(labels), column=0, columnspan=3, pady=(10,0))
        ttk.Button(btns, text="حفظ", command=self.on_save).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="إلغاء", command=self._do_close).grid(row=0, column=1, padx=6)

        self.protocol("WM_DELETE_WINDOW", self._do_close)
        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self._do_close())

    def _set_today(self, key):
        w = self.vars.get(key)
        if not w: return
        if HAS_DATEENTRY and isinstance(w, DateEntry):
            try:
                w.set_date(date.today())
            except:
                pass
        else:
            w.delete(0, tk.END)
            w.insert(0, date.today().strftime("%Y-%m-%d"))

    def on_save(self):
        mandatory = ["full_name","national_id","job_title","phone","email","contract_start","contract_end","residency_expiry"]
        for k in mandatory:
            v = self.vars.get(k).get().strip() if k in self.vars else ""
            if not v:
                messagebox.showerror("خطأ", "يرجى تعبئة كافة الحقول المطلوبة (المشار إليها بـ *).")
                return
        for key in ("contract_start","contract_end","residency_expiry"):
            raw = self.vars[key].get().strip() if not (HAS_DATEENTRY and isinstance(self.vars[key], DateEntry)) else self.vars[key].get_date().strftime("%Y-%m-%d")
            dt = _parse(raw)
            if not dt:
                messagebox.showerror("خطأ", f"التاريخ غير صحيح في الحقل: {key}. الصيغ المسموحة مثل 2025-08-15 أو 15-08-2025.")
                return
            val = dt.strftime("%Y-%m-%d")
            if HAS_DATEENTRY and isinstance(self.vars[key], DateEntry):
                self.vars[key].delete(0, tk.END)
                self.vars[key].insert(0, val)

        full_name = self.vars["full_name"].get().strip() or None
        national_id = self.vars["national_id"].get().strip() or None
        residency_no = national_id
        job_title = self.vars["job_title"].get().strip() or None
        phone = self.vars["phone"].get().strip() or None
        email = self.vars["email"].get().strip() or None
        contract_start = self.vars["contract_start"].get().strip() or None
        contract_end = self.vars["contract_end"].get().strip() or None
        residency_expiry = self.vars["residency_expiry"].get().strip() or None
        notes = self.vars["notes"].get().strip() or None
        self.result = (full_name, national_id, residency_no, job_title, phone, email, contract_start, contract_end, residency_expiry, notes)
        self._do_close()

    def _do_close(self):
        if callable(self.on_close):
            try:
                self.on_close()
            except:
                pass
        self.destroy()

class AlertsDialog(tk.Toplevel):
    def __init__(self, master, rows, days=REMINDER_DAYS_DEFAULT):
        super().__init__(master)
        self.title("التنبيهات")
        try:
            self.iconbitmap(ICON_PATH)
        except Exception:
            pass
        self.configure(bg=master['bg'])
        self.resizable(True, True)
        ttk.Label(self, text=f"العقود والإقامات التي ستنتهي خلال {days} يوم", style="Info.TLabel").pack(anchor="w", padx=12, pady=8)
        cols = ("id","الاسم","نهاية العقد","انتهاء الإقامة","أيام للعقد","أيام للإقامة")
        tree = ttk.Treeview(self, columns=cols, show="headings", height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor="center", width=140)
        tree.pack(fill="both", expand=True, padx=12, pady=8)
        today = date.today()
        def _fmt(x):
            return "-" if x is None else str(x)
        for r in rows:
            days_contract = _days_left(r[8], today)
            days_res = _days_left(r[9], today)
            if (days_contract is not None and 0 <= days_contract <= days) or (days_res is not None and 0 <= days_res <= days):
                tree.insert("", "end", values=(r[0], r[1], r[8] or "-", r[9] or "-", _fmt(days_contract), _fmt(days_res)))

def main():
    try:
        _ensure_dirs()
        init_db()
        app = HRApp()
        app.mainloop()
    except Exception as e:
        _log_exception(e)
        raise

if __name__ == "__main__":
    main()
