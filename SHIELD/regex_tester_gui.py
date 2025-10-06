# regex_tester_gui.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import yaml
import re
from file_loader import get_file_text

CONFIG_PATH = "config/field_patterns.yaml"

class RegexTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - Regex Pattern Tester")

        self.patterns = self.load_patterns()

        self.label_var = tk.StringVar()
        self.new_label_var = tk.StringVar()
        self.pattern_var = tk.StringVar()
        self.current_pattern_var = tk.StringVar()

        self.setup_ui()

    def load_patterns(self):
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)
        return config.get("fields", {})

    def save_patterns(self):
        with open(CONFIG_PATH, "w") as f:
            yaml.dump({"fields": self.patterns}, f, sort_keys=False)
        messagebox.showinfo("Saved", "Patterns saved to field_patterns.yaml")

    def setup_ui(self):
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_frame = tk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        # --- LEFT: CURRENT PATTERNS ---
        label_frame = tk.LabelFrame(left_frame, text="Test Current Patterns")
        label_frame.pack(fill="x")

        tk.Label(label_frame, text="Select Existing Label:").pack(anchor="w", padx=5)
        label_menu = ttk.Combobox(label_frame, textvariable=self.label_var, values=list(self.patterns.keys()))
        label_menu.pack(fill="x", padx=5, pady=2)
        label_menu.bind("<<ComboboxSelected>>", lambda e: self.update_existing_patterns())

        input_frame = tk.LabelFrame(left_frame, text="Input Text")
        input_frame.pack(fill="both", expand=True)
        self.input_textbox = scrolledtext.ScrolledText(input_frame, height=6)
        self.input_textbox.pack(fill="both", expand=True, padx=5, pady=5)

        button_frame = tk.Frame(left_frame)
        button_frame.pack(fill="x", pady=5)
        tk.Button(button_frame, text="Upload File", command=self.load_file).pack(side="left", padx=5)
        tk.Button(button_frame, text="Test Selected", command=self.test_pattern).pack(side="left", padx=5)
        tk.Button(button_frame, text="Test All", command=self.test_all_patterns).pack(side="left", padx=5)

        self.output = scrolledtext.ScrolledText(left_frame, height=12)
        self.output.pack(fill="both", expand=True, padx=5, pady=5)

        # --- RIGHT: NEW PATTERN TESTING ---
        pattern_edit_frame = tk.LabelFrame(right_frame, text="Define New Pattern")
        pattern_edit_frame.pack(fill="both", expand=True)

        tk.Label(pattern_edit_frame, text="Create New Label (optional):").pack(anchor="w", padx=5)
        tk.Entry(pattern_edit_frame, textvariable=self.new_label_var).pack(fill="x", padx=5, pady=2)

        tk.Label(pattern_edit_frame, text="Regex Pattern to Test:").pack(anchor="w", padx=5)
        tk.Entry(pattern_edit_frame, textvariable=self.pattern_var).pack(fill="x", padx=5, pady=2)

        tk.Label(pattern_edit_frame, text="Select Existing Pattern to Edit:").pack(anchor="w", padx=5)
        self.existing_patterns_box = ttk.Combobox(pattern_edit_frame, textvariable=self.current_pattern_var)
        self.existing_patterns_box.pack(fill="x", padx=5, pady=2)
        self.update_existing_patterns()

        self.regex_test_output = scrolledtext.ScrolledText(pattern_edit_frame, height=10)
        self.regex_test_output.pack(fill="both", padx=5, pady=5)

        btn_frame = tk.Frame(pattern_edit_frame)
        btn_frame.pack(fill="x", padx=5)
        tk.Button(btn_frame, text="Test New Pattern", command=self.test_new_pattern).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_frame, text="Add/Update Pattern", command=self.add_or_update_pattern).pack(side="left", expand=True, fill="x", padx=2)
        tk.Button(btn_frame, text="Save Changes", command=self.save_patterns).pack(side="left", expand=True, fill="x", padx=2)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Supported Files", "*.txt *.csv *.pdf *.rpg *.rpgrpt *.prn")
        ])
        if not path:
            return
        try:
            text = get_file_text(path)
            self.input_textbox.delete("1.0", tk.END)
            self.input_textbox.insert(tk.END, text)
        except Exception as e:
            messagebox.showerror("File Error", str(e))

    def update_existing_patterns(self):
        selected_label = self.label_var.get()
        if selected_label in self.patterns:
            self.existing_patterns_box["values"] = self.patterns[selected_label]
        else:
            self.existing_patterns_box["values"] = []

    def add_or_update_pattern(self):
        label = self.label_var.get() or self.new_label_var.get()
        pattern = self.pattern_var.get()
        if not label:
            messagebox.showwarning("Missing Label", "Select or enter a label name.")
            return
        if not pattern:
            messagebox.showwarning("Missing Pattern", "Enter a regex pattern to add.")
            return
        try:
            re.compile(pattern)
        except re.error as e:
            messagebox.showerror("Invalid Regex", str(e))
            return

        if label not in self.patterns:
            self.patterns[label] = []
        if pattern not in self.patterns[label]:
            self.patterns[label].append(pattern)
            messagebox.showinfo("Pattern Added", f"Pattern added under {label}.")
        else:
            messagebox.showinfo("Pattern Exists", f"Pattern already exists under {label}.")

        self.update_existing_patterns()

    def test_pattern(self):
        label = self.label_var.get()
        text = self.input_textbox.get("1.0", tk.END)
        self.output.delete("1.0", tk.END)

        if not label or label not in self.patterns:
            messagebox.showerror("Missing Label", "Please select a valid label.")
            return

        matches_found = False
        for pattern in self.patterns[label]:
            try:
                for match in re.finditer(pattern, text):
                    match_info = f"[{label}] Match: '{match.group()}' at ({match.start()}, {match.end()})\n"
                    self.output.insert(tk.END, match_info)
                    matches_found = True
            except re.error as e:
                self.output.insert(tk.END, f"Invalid pattern: {pattern} - {e}\n")

        if not matches_found:
            self.output.insert(tk.END, "No matches found.\n")

    def test_all_patterns(self):
        text = self.input_textbox.get("1.0", tk.END)
        self.output.delete("1.0", tk.END)
        any_matches = False

        for label, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                try:
                    for match in re.finditer(pattern, text):
                        match_info = f"[{label}] Match: '{match.group()}' at ({match.start()}, {match.end()})\n"
                        self.output.insert(tk.END, match_info)
                        any_matches = True
                except re.error as e:
                    self.output.insert(tk.END, f"Invalid pattern in {label}: {pattern} - {e}\n")

        if not any_matches:
            self.output.insert(tk.END, "No matches found.\n")

    def test_new_pattern(self):
        pattern = self.pattern_var.get()
        text = self.input_textbox.get("1.0", tk.END)
        self.regex_test_output.delete("1.0", tk.END)

        if not pattern:
            self.regex_test_output.insert(tk.END, "Enter a regex pattern to test.\n")
            return

        try:
            compiled = re.compile(pattern)
        except re.error as e:
            self.regex_test_output.insert(tk.END, f"Invalid regex: {e}\n")
            return

        matches = list(compiled.finditer(text))
        if matches:
            for match in matches:
                self.regex_test_output.insert(tk.END, f"Match: '{match.group()}' at ({match.start()}, {match.end()})\n")
        else:
            self.regex_test_output.insert(tk.END, "No matches found.\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = RegexTesterApp(root)
    root.mainloop()