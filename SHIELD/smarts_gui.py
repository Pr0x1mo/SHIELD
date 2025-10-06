# -*- coding: utf-8 -*-
# smarts_gui.py (V2 - SMARTS Rule Builder for SHIELD)
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os

RULES_PATH = "config/smarts_rules.json"


class SmartsRuleBuilder:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - SMARTS Rule Builder")

        # Internal store is always a dict: {name: rule_dict}
        self.rules = {}
        # Track original on-disk shape so we can round-trip (either "dict" or "list")
        self.original_shape = "dict"

        self.current_rule = None
        self.setup_ui()
        self.load_rules()

    # ---------------------------
    # Normalization helpers
    # ---------------------------
    def _normalize_rules(self, data):
        """
        Accepts either:
          - dict: {"Rule A": {...}, "Rule B": {...}}
          - list: [{"name": "Rule A", ...}, {"name": "Rule B", ...}]
        Returns (rules_dict, original_shape)
        """
        if isinstance(data, dict):
            for k, v in data.items():
                # ensure a name field for round-trip
                if isinstance(v, dict):
                    v.setdefault("name", k)
            return data, "dict"

        if isinstance(data, list):
            rules = {}
            for i, r in enumerate(data):
                if not isinstance(r, dict):
                    # skip anything malformed
                    continue
                name = (
                    r.get("name")
                    or r.get("label")
                    or r.get("id")
                    or f"Rule {i+1}"
                )
                rules[name] = {**r, "name": name}
            return rules, "list"

        # Fallback empty
        return {}, "dict"

    def _denormalize_rules(self, rules_dict, original_shape):
        """
        Convert internal dict back to the original shape for saving.
        """
        if original_shape == "dict":
            out = {}
            for name, rule in rules_dict.items():
                r = {**rule}
                # Remove duplicate name if it mirrors the key
                if r.get("name") == name:
                    r.pop("name", None)
                out[name] = r
            return out

        # list shape
        lst = []
        for name, rule in rules_dict.items():
            r = {**rule}
            r.setdefault("name", name)
            lst.append(r)
        # keep stable order by priority, then name
        lst.sort(key=lambda r: (r.get("priority", 1), r.get("name", "")))
        return lst

    # ---------------------------
    # UI setup
    # ---------------------------
    def setup_ui(self):
        self.left_frame = tk.Frame(self.root)
        self.left_frame.pack(side="left", fill="y", padx=10, pady=10)

        tk.Label(self.left_frame, text="Rules").pack()
        self.rule_listbox = tk.Listbox(self.left_frame, width=32)
        self.rule_listbox.pack(fill="y", expand=True)
        self.rule_listbox.bind("<<ListboxSelect>>", self.load_selected_rule)

        tk.Button(self.left_frame, text="New Rule", command=self.new_rule).pack(fill="x", pady=2)
        tk.Button(self.left_frame, text="Delete Rule", command=self.delete_rule).pack(fill="x", pady=2)

        self.right_frame = tk.Frame(self.root)
        self.right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.name_var = tk.StringVar()
        self.enabled_var = tk.BooleanVar(value=True)
        self.priority_var = tk.IntVar(value=1)

        tk.Label(self.right_frame, text="Rule Name").pack(anchor="w")
        tk.Entry(self.right_frame, textvariable=self.name_var).pack(fill="x")

        toggle_frame = tk.Frame(self.right_frame)
        toggle_frame.pack(fill="x", pady=5)
        tk.Checkbutton(toggle_frame, text="Enable Rule", variable=self.enabled_var).pack(side="left")
        tk.Label(toggle_frame, text="Priority:").pack(side="left", padx=5)
        tk.Spinbox(toggle_frame, from_=1, to=99, textvariable=self.priority_var, width=5).pack(side="left")

        # Conditions JSON
        tk.Label(self.right_frame, text="Conditions (JSON)").pack(anchor="w", pady=(8, 0))
        self.condition_text = scrolledtext.ScrolledText(self.right_frame, height=8)
        self.condition_text.insert("1.0", "[]")
        self.condition_text.pack(fill="x", pady=5)

        # Actions JSON
        tk.Label(self.right_frame, text="Actions (JSON)").pack(anchor="w", pady=(8, 0))
        self.action_text = scrolledtext.ScrolledText(self.right_frame, height=6)
        self.action_text.insert("1.0", "[]")
        self.action_text.pack(fill="x", pady=5)

        # Save/Preview buttons
        tk.Button(self.right_frame, text="Save Rule", command=self.save_rule).pack(pady=3)
        tk.Button(self.right_frame, text="Save All Rules", command=self.save_all).pack(pady=3)

        # Sample Test Preview
        tk.Label(self.right_frame, text="Test Input").pack(anchor="w", pady=(8, 0))
        self.test_input = scrolledtext.ScrolledText(self.right_frame, height=8)
        self.test_input.pack(fill="both", expand=True)
        tk.Button(self.right_frame, text="Preview This Rule", command=self.preview_rule).pack()

        tk.Label(self.right_frame, text="Preview Output").pack(anchor="w", pady=(8, 0))
        self.preview_output = scrolledtext.ScrolledText(self.right_frame, height=6)
        self.preview_output.pack(fill="x", pady=5)

    # ---------------------------
    # IO
    # ---------------------------
    def load_rules(self):
        if os.path.exists(RULES_PATH):
            try:
                with open(RULES_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read rules: {e}")
                self.rules, self.original_shape = {}, "dict"
            else:
                self.rules, self.original_shape = self._normalize_rules(data)
        else:
            self.rules, self.original_shape = {}, "dict"
        self.refresh_listbox()

    def save_all(self):
        data = self._denormalize_rules(self.rules, self.original_shape)
        os.makedirs(os.path.dirname(RULES_PATH), exist_ok=True)
        try:
            with open(RULES_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Saved", "All rules saved to disk.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rules: {e}")

    # ---------------------------
    # Listbox / Selection helpers
    # ---------------------------
    def _status_prefix(self, enabled):
        # ASCII-only to avoid encoding issues
        return "[ON]" if enabled else "[OFF]"

    def _make_listbox_label(self, name, enabled):
        return f"{self._status_prefix(enabled)} {name}"

    def _parse_listbox_label(self, label):
        # Expect "[ON] name" or "[OFF] name"
        if "] " in label:
            return label.split("] ", 1)[1].strip()
        return label.strip()

    def refresh_listbox(self):
        self.rule_listbox.delete(0, "end")
        # sort by priority then name
        items = list(self.rules.items())
        items.sort(key=lambda kv: (kv[1].get("priority", 1), kv[0]))
        for name, rule in items:
            enabled = bool(rule.get("enabled", True))
            self.rule_listbox.insert("end", self._make_listbox_label(name, enabled))

    def load_selected_rule(self, event):
        sel = self.rule_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        label = self.rule_listbox.get(idx)
        name = self._parse_listbox_label(label)

        rule = self.rules.get(name)
        if not rule:
            return
        self.current_rule = name
        self.name_var.set(name)
        self.enabled_var.set(bool(rule.get("enabled", True)))
        self.priority_var.set(int(rule.get("priority", 1)))
        self.condition_text.delete("1.0", "end")
        self.condition_text.insert("1.0", json.dumps(rule.get("conditions", []), indent=2))
        self.action_text.delete("1.0", "end")
        self.action_text.insert("1.0", json.dumps(rule.get("actions", []), indent=2))

    # ---------------------------
    # CRUD
    # ---------------------------
    def new_rule(self):
        self.current_rule = None
        self.name_var.set("")
        self.enabled_var.set(True)
        self.priority_var.set(1)
        self.condition_text.delete("1.0", "end")
        self.condition_text.insert("1.0", "[]")
        self.action_text.delete("1.0", "end")
        self.action_text.insert("1.0", "[]")

    def delete_rule(self):
        sel = self.rule_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        name = self._parse_listbox_label(self.rule_listbox.get(idx))
        if name in self.rules:
            del self.rules[name]
            self.refresh_listbox()
            self.new_rule()

    def _safe_load_json_text(self, widget, default):
        raw = widget.get("1.0", "end").strip()
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception as e:
            raise ValueError(f"Invalid JSON: {e}")

    def save_rule(self):
        try:
            name = self.name_var.get().strip()
            if not name:
                raise ValueError("Missing rule name.")
            conds = self._safe_load_json_text(self.condition_text, [])
            acts = self._safe_load_json_text(self.action_text, [])

            rule = {
                "name": name,  # keep name inside for list-shape round-trip
                "enabled": bool(self.enabled_var.get()),
                "priority": int(self.priority_var.get()),
                "conditions": conds if isinstance(conds, list) else [conds],
                "actions": acts if isinstance(acts, list) else [acts],
            }
            self.rules[name] = rule
            self.refresh_listbox()
            messagebox.showinfo("Saved", f"Rule '{name}' saved.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save rule: {e}")

    # ---------------------------
    # Preview (placeholder)
    # ---------------------------
    def preview_rule(self):
        # Placeholder - future integration with smarts_v2_engine
        self.preview_output.delete("1.0", "end")
        name = self.name_var.get().strip() or "(unnamed)"
        self.preview_output.insert("1.0", f"Preview for rule '{name}':\n")
        self.preview_output.insert("end", "Preview functionality coming soon...")


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartsRuleBuilder(root)
    root.mainloop()
