# training_monitor_gui.py
import tkinter as tk
from tkinter import scrolledtext, ttk, filedialog, messagebox
import json
import os

FEEDBACK_FILE = "data/feedback.json"


class TrainingMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - Feedback & Training Monitor")

        self.feedback_data = []

        self.setup_ui()
        self.load_feedback()

    def setup_ui(self):
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree = ttk.Treeview(frame, columns=("text", "entity"), show="headings", height=12)
        self.tree.heading("text", text="Document Snippet")
        self.tree.heading("entity", text="Labeled Entities")
        self.tree.column("text", width=520, anchor="w")
        self.tree.column("entity", width=420, anchor="w")
        self.tree.pack(fill="both", expand=True)

        export_btn = tk.Button(frame, text="Export Feedback as JSON", command=self.export_json)
        export_btn.pack(pady=10)

    def _fmt_ent(self, e):
        """
        Accepts either:
          - dict: {"start","end","label","line_number","left","right"}
          - tuple/list: (start, end, label)
        Returns a concise string for display.
        """
        try:
            if isinstance(e, dict):
                start = int(e.get("start", -1))
                end = int(e.get("end", -1))
                label = str(e.get("label", ""))
                ln = e.get("line_number", None)
                left = e.get("left", None)
                right = e.get("right", None)
                extra = ""
                if all(isinstance(v, int) and v is not None and v >= 0 for v in (ln, left, right)):
                    extra = f", line={ln}, [{left}:{right}]"
                return f"({start}-{end}, {label}{extra})"
            elif isinstance(e, (list, tuple)) and len(e) >= 3:
                start, end, label = e[0], e[1], e[2]
                return f"({start}-{end}, {label})"
        except Exception as ex:
            return f"(invalid entity: {ex})"
        return "(invalid entity)"

    def load_feedback(self):
        # Clear current rows
        if hasattr(self, "tree"):
            for iid in self.tree.get_children():
                self.tree.delete(iid)

        if not os.path.exists(FEEDBACK_FILE):
            messagebox.showinfo("No Feedback", "No feedback.json found yet.")
            self.feedback_data = []
            return

        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("feedback.json should contain a list of records.")
            self.feedback_data = data
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read feedback: {e}")
            self.feedback_data = []
            return

        for item in self.feedback_data:
            text = item.get("text", "")
            snippet = (text[:160] + "...") if len(text) > 160 else text
            snippet = snippet.replace("\n", " ")

            ents_list = item.get("entities", [])
            ents = ", ".join(self._fmt_ent(e) for e in ents_list)
            self.tree.insert("", "end", values=(snippet, ents))

    def export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.feedback_data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Exported", f"Feedback exported to {path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = TrainingMonitor(root)
    root.mainloop()
