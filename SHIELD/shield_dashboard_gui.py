# shield_dashboard_gui.py
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import sys
from pathlib import Path

APP_TITLE = "SHIELD - Central Dashboard"
COPYRIGHT = "© 2025 SHIELD Project"

# ---- paths to your external pipeline scripts ----
FF_PARSER_DIR   = r"C:\Users\Proximus\Desktop\Obfuscate\Python\FF Parser"
CIBC_PARSER     = os.path.join(FF_PARSER_DIR, "cibc_parser_sql.py")
DATA_OBFUSCATOR = os.path.join(FF_PARSER_DIR, "data_obfuscator.py")

# ---------- helpers ----------
def try_launch(candidates: list[list[str]], error_label: str, cwd: str | None = None):
    """
    Try each command (list[str]) until one launches.
    Runs with the provided working directory (cwd) when given.
    Shows a friendly error if none exists.
    """
    for cmd in candidates:
        # if a .py is present, ensure it exists before launching
        script = next((p for p in cmd if p.lower().endswith(".py")), None)
        if script and not Path(script).exists():
            continue
        try:
            subprocess.Popen(cmd, cwd=cwd)
            return
        except FileNotFoundError:
            continue
    messagebox.showerror("Not found", f"Could not find a launcher for: {error_label}")

# ---------- main GUI ----------
class ShieldDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.minsize(520, 780)           # taller minimum
        self.geometry("520x780")         # baseline; will be overridden
        self.configure(padx=10, pady=10)

        tk.Label(self, text="SHIELD Dashboard", font=("Segoe UI", 18, "bold")).pack(pady=(0, 8), anchor="w")

        # Sections
        self._section_core()
        self._section_proximus()
        self._section_config()
        self._section_training()
        self._section_utils()

        # Footer
        ttk.Separator(self).pack(fill="x", pady=10)
        bottom = tk.Frame(self)
        bottom.pack(fill="x")
        tk.Label(bottom, text=COPYRIGHT, fg="#777").pack(side="left")
        ttk.Button(bottom, text="Exit", command=self.destroy).pack(side="right")

        # --- Auto-fit height to content (cap below screen height) ---
        self.update_idletasks()
        target_h = min(self.winfo_reqheight() + 40, self.winfo_screenheight() - 100)
        self.geometry(f"520x{target_h}")

    # -------- sections ----------
    def _section_core(self):
        frame = tk.LabelFrame(self, text="Core Pipeline", padx=10, pady=8)
        frame.pack(fill="x", pady=6)

        ttk.Button(frame, text="🎯  Detection & Obfuscation",
                   command=self.run_detection).pack(fill="x", pady=3)
        ttk.Button(frame, text="🔁  Feedback Loop Monitor",
                   command=self.launch_feedback).pack(fill="x", pady=3)
        ttk.Button(frame, text="📊  Reports / Analytics",
                   command=self.launch_reporting_ui).pack(fill="x", pady=3)

    # NEW: Proximus' Pipeline
    def _section_proximus(self):
        frame = tk.LabelFrame(self, text="Proximus' Pipeline", padx=10, pady=8)
        frame.pack(fill="x", pady=6)

        ttk.Button(frame, text="📥  Import unstructured data",
                   command=self.launch_import_unstructured).pack(fill="x", pady=3)
        ttk.Button(frame, text="🛡️  Obfuscate data",
                   command=self.launch_obfuscate_data).pack(fill="x", pady=3)

    def _section_config(self):
        frame = tk.LabelFrame(self, text="Configuration", padx=10, pady=8)
        frame.pack(fill="x", pady=6)

        ttk.Button(frame, text="📝  SMARTS Report Config",
                   command=self.launch_report_config).pack(fill="x", pady=3)
        ttk.Button(frame, text="⚙️  SMARTS Rule Builder",
                   command=self.launch_smarts_rules).pack(fill="x", pady=3)
        ttk.Button(frame, text="🧪  Regex Tester",
                   command=self.launch_regex_tester).pack(fill="x", pady=3)

    def _section_training(self):
        frame = tk.LabelFrame(self, text="Model Training", padx=10, pady=8)
        frame.pack(fill="x", pady=6)

        ttk.Button(frame, text="📂  Generate Training Data",
                   command=self.launch_generate_training).pack(fill="x", pady=3)
        ttk.Button(frame, text="⚡  Train Model",
                   command=self.launch_train_model).pack(fill="x", pady=3)
        ttk.Button(frame, text="🔍  Evaluate Model (Quick)",
                   command=self.launch_evaluate_model).pack(fill="x", pady=3)
        ttk.Button(frame, text="🧮  Compare vs SMARTS Config",
                   command=self.launch_compare_vs_config).pack(fill="x", pady=3)
        ttk.Button(frame, text="📥  Load .spacy (preview)",
                   command=self.launch_load_training).pack(fill="x", pady=3)

    def _section_utils(self):
        frame = tk.LabelFrame(self, text="Utilities", padx=10, pady=8)
        frame.pack(fill="x", pady=6)

        ttk.Button(frame, text="🗂️  Fixed-width Parser (demo)",
                   command=self.launch_parser).pack(fill="x", pady=3)

    # -------- launchers ----------
    def launch_regex_tester(self):
        try_launch([ [sys.executable, "regex_tester_gui.py"] ],
                   "Regex Tester")

    def run_detection(self):
        try_launch([ [sys.executable, "shield_gui.py"] ],
                   "Detection & Obfuscation (shield_gui.py)")

    def launch_feedback(self):
        try_launch([ [sys.executable, "training_monitor_gui.py"],
                     [sys.executable, "feedback_loop.py"] ],
                   "Feedback Loop Monitor")

    def launch_reporting_ui(self):
        try_launch([ [sys.executable, "reporting_gui.py"] ],
                   "Reporting UI")

    def launch_report_config(self):
        try_launch([ [sys.executable, "smart_report_config_gui.py"] ],
                   "SMARTS Report Config")

    def launch_smarts_rules(self):
        try_launch([ [sys.executable, "smarts_gui.py"] ],
                   "SMARTS Rule Builder")

    def launch_generate_training(self):
        try_launch([ [sys.executable, "generate_train_spacy.py"] ],
                   "Generate Training Data (train.spacy)")

    def launch_train_model(self):
        try_launch([ [sys.executable, "train_spacy_model.py"] ],
                   "Train Model (spaCy)")

    def launch_evaluate_model(self):
        try_launch([ [sys.executable, "evaluate_model.py"],
                     [sys.executable, "evaluate_single_config.py"] ],
                   "Evaluate Model")

    def launch_compare_vs_config(self):
        try_launch([ [sys.executable, "compare_predictions_to_config.py"] ],
                   "Compare Predictions vs SMARTS Config")

    def launch_load_training(self):
        try_launch([ [sys.executable, "loadTrainingData.py"] ],
                   "Load Training Data (.spacy preview)")

    def launch_parser(self):
        try_launch([ [sys.executable, "smart_parser.py"] ],
                   "Fixed-width Parser")

    # NEW: buttons’ actions
    def launch_import_unstructured(self):
        try_launch([ [sys.executable, CIBC_PARSER] ],
                   "Import unstructured data (cibc_parser_sql.py)",
                   cwd=FF_PARSER_DIR)

    def launch_obfuscate_data(self):
        try_launch([ [sys.executable, DATA_OBFUSCATOR] ],
                   "Obfuscate data (data_obfuscator.py)",
                   cwd=FF_PARSER_DIR)

if __name__ == "__main__":
    # Optional: better DPI on Windows
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ShieldDashboard()
    # Use ttk theme if available
    try:
        style = ttk.Style()
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app.mainloop()
