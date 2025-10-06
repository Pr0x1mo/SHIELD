# reporting_gui.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import os
import hashlib
from collections import Counter
from datetime import datetime

FEEDBACK_FILE = "data/feedback.json"
BACKUP_DIR = "data/backups"


def _compute_line_pos(text, start, end):
    """Return (line_number, left, right) for char span [start:end) within text."""
    lines = text.splitlines()
    offset = 0
    for i, line in enumerate(lines):
        line_len = len(line) + 1  # +1 for '\n'
        if offset + line_len > start:
            left = start - offset
            right = end - offset
            return i, left, right
        offset += line_len
    return -1, -1, -1


def _iter_entities(entities):
    """
    Yield normalized dicts:
      {"start": int, "end": int, "label": str, "line_number": int|-1, "left": int|-1, "right": int|-1, "_raw": original}
    Accepts both dict and (start,end,label) tuples.
    """
    for e in entities or []:
        if isinstance(e, dict):
            yield {
                "start": int(e.get("start", -1)),
                "end": int(e.get("end", -1)),
                "label": str(e.get("label", "")),
                "line_number": int(e.get("line_number", -1)) if e.get("line_number") is not None else -1,
                "left": int(e.get("left", -1)) if e.get("left") is not None else -1,
                "right": int(e.get("right", -1)) if e.get("right") is not None else -1,
                "_raw": e,
            }
        elif isinstance(e, (list, tuple)) and len(e) >= 3:
            yield {
                "start": int(e[0]),
                "end": int(e[1]),
                "label": str(e[2]),
                "line_number": -1,
                "left": -1,
                "right": -1,
                "_raw": e,
            }


class ReportingUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - Reporting UI")
        self.data = []
        self.doc_map = {}          # doc_id -> snippet
        self.tree_data = []        # rows currently shown
        self.sort_state = {"column": None, "reverse": False}

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)

        self.label_var = tk.StringVar()
        self.doc_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.min_len_var = tk.StringVar()
        self.max_len_var = tk.StringVar()

        ttk.Label(top_frame, text="Label:").pack(side="left")
        self.label_menu = ttk.Combobox(top_frame, textvariable=self.label_var, state="readonly", width=18)
        self.label_menu.pack(side="left", padx=5)

        ttk.Label(top_frame, text="Document:").pack(side="left")
        self.doc_menu = ttk.Combobox(top_frame, textvariable=self.doc_var, state="readonly", width=26)
        self.doc_menu.pack(side="left", padx=5)

        ttk.Label(top_frame, text="Search:").pack(side="left")
        tk.Entry(top_frame, textvariable=self.search_var, width=16).pack(side="left", padx=5)

        ttk.Label(top_frame, text="Min Len:").pack(side="left")
        tk.Entry(top_frame, textvariable=self.min_len_var, width=6).pack(side="left")

        ttk.Label(top_frame, text="Max Len:").pack(side="left")
        tk.Entry(top_frame, textvariable=self.max_len_var, width=6).pack(side="left")

        tk.Button(top_frame, text="Apply Filters", command=self.apply_filter).pack(side="left", padx=10)
        tk.Button(top_frame, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(top_frame, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(top_frame, text="Export JSON", command=self.export_json).pack(side="right", padx=5)
        tk.Button(top_frame, text="Export CSV", command=self.export_csv).pack(side="right")

        columns = ("value", "label", "span", "doc")
        self.tree = ttk.Treeview(self.root, columns=columns, show='headings', selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col.title(), command=lambda c=col: self.sort_by_column(c))
            self.tree.column(col, width=120 if col != "value" else 320, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=5)

        self.summary_label = tk.Label(self.root, text="", anchor="w", justify="left", font=("Courier", 10))
        self.summary_label.pack(fill="x", padx=10, pady=5)

    def load_data(self):
        if not os.path.exists(FEEDBACK_FILE):
            messagebox.showinfo("No Data", "No feedback.json found.")
            return

        try:
            with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            if not isinstance(self.data, list):
                raise ValueError("feedback.json should be a list.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read feedback: {e}")
            self.data = []
            return

        # Build doc map and label set
        all_labels = set()
        all_docs = {}
        for item in self.data:
            text = item.get("text", "")
            text_id = self.get_doc_id(text)
            all_docs[text_id] = (text[:30] + "...").replace("\n", " ").strip()
            for ent in _iter_entities(item.get("entities", [])):
                if ent["label"]:
                    all_labels.add(ent["label"])

        self.label_menu["values"] = ["(All Labels)"] + sorted(all_labels)
        self.label_var.set("(All Labels)")
        self.doc_map = all_docs
        self.doc_menu["values"] = ["(All Documents)"] + list(all_docs.values())
        self.doc_var.set("(All Documents)")

        self.refresh_table(self.data)

    def get_doc_id(self, text):
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def apply_filter(self):
        label = self.label_var.get()
        doc_label = self.doc_var.get()
        search = self.search_var.get().lower()
        min_len = int(self.min_len_var.get()) if self.min_len_var.get().isdigit() else None
        max_len = int(self.max_len_var.get()) if self.max_len_var.get().isdigit() else None

        # Resolve selected document's id
        doc_id = None
        if doc_label != "(All Documents)":
            for k, v in self.doc_map.items():
                if v == doc_label:
                    doc_id = k
                    break

        filtered = []
        for item in self.data:
            text = item.get("text", "")
            item_id = self.get_doc_id(text)
            if doc_id and item_id != doc_id:
                continue

            filtered_entities = []
            for ent in _iter_entities(item.get("entities", [])):
                s, e, lbl = ent["start"], ent["end"], ent["label"]
                # Guard against bad spans
                value = text[s:e] if 0 <= s <= e <= len(text) else ""
                if label != "(All Labels)" and lbl != label:
                    continue
                if search and search not in value.lower():
                    continue
                if min_len is not None and len(value) < min_len:
                    continue
                if max_len is not None and len(value) > max_len:
                    continue
                filtered_entities.append({"start": s, "end": e, "label": lbl})

            if filtered_entities:
                filtered.append({"text": text, "entities": filtered_entities})

        self.refresh_table(filtered)

    def refresh_table(self, records):
        self.tree.delete(*self.tree.get_children())
        self.tree_data = []

        for item in records:
            text = item.get("text", "")
            doc_label = self.doc_map.get(self.get_doc_id(text), "(Unknown)")
            for ent in _iter_entities(item.get("entities", [])):
                s, e, lbl = ent["start"], ent["end"], ent["label"]
                value = text[s:e].replace("\n", " ").strip() if 0 <= s <= e <= len(text) else ""
                span = f"{s}-{e}"
                row = (value, lbl, span, doc_label)
                self.tree.insert("", "end", values=row)
                # store extra for edits/deletes
                self.tree_data.append((value, lbl, span, doc_label, text, s, e))

        self.update_summary()

    def update_summary(self):
        total = len(self.tree_data)
        label_counts = Counter(row[1] for row in self.tree_data)
        doc_set = set(row[3] for row in self.tree_data)

        summary = f"Total Entities: {total}    Documents: {len(doc_set)}\n"
        summary += "Entity Counts: " + ", ".join(f"{label}: {count}" for label, count in label_counts.items())
        self.summary_label.config(text=summary)

    def sort_by_column(self, col):
        reverse = self.sort_state["column"] == col and not self.sort_state["reverse"]
        idx = ("value", "label", "span", "doc").index(col)
        self.tree_data.sort(key=lambda x: x[idx], reverse=reverse)
        self.sort_state = {"column": col, "reverse": reverse}

        self.tree.delete(*self.tree.get_children())
        for row in self.tree_data:
            self.tree.insert("", "end", values=row[:4])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a record to edit.")
            return

        item_vals = self.tree.item(selected[0])["values"]
        old_value, old_label, span_str, doc_label = item_vals
        start, end = map(int, span_str.split("-"))

        new_value = simpledialog.askstring("Edit Entity Value", "Enter new entity value:", initialvalue=old_value)
        new_label = simpledialog.askstring("Edit Label", "Enter new label:", initialvalue=old_label)

        if not new_value or not new_label:
            messagebox.showinfo("Cancelled", "Edit cancelled or incomplete.")
            return

        # Backup before modify
        self.backup_feedback()

        # Locate and update the matching entity in self.data
        updated = False
        for entry in self.data:
            text = entry.get("text", "")
            if self.doc_map.get(self.get_doc_id(text)) != doc_label:
                continue

            ents = entry.get("entities", [])
            for i, ent in enumerate(list(ents)):
                for norm in _iter_entities([ent]):
                    s, e, lbl = norm["start"], norm["end"], norm["label"]
                    if s == start and e == end and lbl == old_label:
                        # Find new span in text
                        new_start = text.find(new_value)
                        if new_start == -1:
                            messagebox.showerror("Not Found", "New value not found in document.")
                            return
                        new_end = new_start + len(new_value)

                        if isinstance(ent, dict):
                            # Update dict entity & recompute fixed-width metadata
                            ln, left, right = _compute_line_pos(text, new_start, new_end)
                            ent.update({
                                "start": new_start,
                                "end": new_end,
                                "label": new_label,
                                "line_number": ln,
                                "left": left,
                                "right": right,
                            })
                            ents[i] = ent
                        else:
                            # Tuple -> create new tuple
                            ents[i] = (new_start, new_end, new_label)
                        updated = True
                        break
                if updated:
                    break
            if updated:
                entry["entities"] = ents
                break

        if not updated:
            messagebox.showwarning("Not Updated", "Could not locate the selected entity to update.")
            return

        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        self.apply_filter()
        messagebox.showinfo("Updated", "Feedback updated and versioned successfully.")

    def backup_feedback(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"feedback_{timestamp}.json")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def export_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.collect_filtered_data(), f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Exported", f"Saved to {path}")

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv")
        if path:
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Entity Value", "Label", "Span", "Document"])
                for row in self.tree_data:
                    writer.writerow(row[:4])
            messagebox.showinfo("Exported", f"Saved to {path}")

    def collect_filtered_data(self):
        return [
            {"value": row[0], "label": row[1], "span": row[2], "document": row[3]}
            for row in self.tree_data
        ]

    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select one or more records to delete.")
            return

        to_delete = []
        preview = []
        for sel in selected_items:
            value, label, span_str, doc_label = self.tree.item(sel)["values"]
            s, e = map(int, span_str.split("-"))
            to_delete.append((value, label, s, e, doc_label))
            preview.append(f"\n- {value} ({label}) in {doc_label}")

        if not messagebox.askyesno("Confirm Delete", "Delete the following entities?" + "".join(preview)):
            return

        self.backup_feedback()

        removed_count = 0
        for entry in self.data:
            text = entry.get("text", "")
            entry_doc_label = self.doc_map.get(self.get_doc_id(text), "(Unknown)")
            ents = entry.get("entities", [])
            new_ents = []
            for ent in ents:
                keep = True
                for norm in _iter_entities([ent]):
                    s, e, lbl = norm["start"], norm["end"], norm["label"]
                    for v, dl, ds, de, dd in to_delete:
                        if s == ds and e == de and lbl == dl and entry_doc_label == dd:
                            keep = False
                            break
                    if not keep:
                        break
                if keep:
                    new_ents.append(ent)
                else:
                    removed_count += 1
            entry["entities"] = new_ents

        with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        self.apply_filter()
        messagebox.showinfo("Deleted", f"{removed_count} record(s) deleted successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReportingUI(root)
    root.mainloop()
