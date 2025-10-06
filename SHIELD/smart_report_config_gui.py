
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox, colorchooser
import json
import os

CONFIG_DIR = "config"

class SmartReportGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - Smart Report Config")
        self.fields = []
        self.preview_lines = []
        self.text_data = ""
        self.selected_file = None

        self.setup_ui()
        self.refresh_config_list()

    def setup_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=5)

        tk.Label(top, text="Report Name:").grid(row=0, column=0)
        self.report_name = tk.Entry(top)
        self.report_name.grid(row=0, column=1)

        tk.Label(top, text="Load Config:").grid(row=0, column=2)
        self.config_picker = ttk.Combobox(top, state="readonly")
        self.config_picker.grid(row=0, column=3)
        self.config_picker.bind("<<ComboboxSelected>>", self.load_selected_config)

        tk.Label(top, text="Header Skip:").grid(row=1, column=0)
        self.header_skip = tk.Spinbox(top, from_=0, to=50, width=5)
        self.header_skip.grid(row=1, column=1, sticky="w")

        tk.Label(top, text="Footer Skip:").grid(row=2, column=0)
        self.footer_skip = tk.Spinbox(top, from_=0, to=50, width=5)
        self.footer_skip.grid(row=2, column=1, sticky="w")

        self.use_date_var = tk.BooleanVar()
        tk.Checkbutton(top, text="Use Content Date", variable=self.use_date_var).grid(row=1, column=2)
        self.show_header_var = tk.BooleanVar()
        tk.Checkbutton(top, text="Show CSV Header", variable=self.show_header_var).grid(row=2, column=2)

        mid = tk.Frame(self.root)
        mid.pack(fill="both", padx=10, pady=5, expand=True)

        self.field_table = ttk.Treeview(mid, columns=("label", "group", "line", "left", "right", "color"), show="headings")
        for col in self.field_table["columns"]:
            self.field_table.heading(col, text=col.capitalize())
        self.field_table.pack(side="left", fill="y", padx=(0, 5))
        self.field_table.bind("<Double-1>", self.edit_cell)

        btn_frame = tk.Frame(mid)
        btn_frame.pack(side="left", fill="y")

        tk.Button(btn_frame, text="Add Field", command=self.add_field).pack(fill="x")
        tk.Button(btn_frame, text="Delete Selected", command=self.delete_field).pack(fill="x")
        tk.Button(btn_frame, text="Save Config", command=self.save_config).pack(fill="x", pady=(20, 0))

        bottom = tk.Frame(self.root)
        bottom.pack(fill="both", expand=True, padx=10, pady=5)

        # Row with "Load Report File" + highlight controls
        load_row = tk.Frame(bottom)
        load_row.pack(fill="x", pady=(0, 4))

        tk.Button(load_row, text="Load Report File", command=self.load_file).pack(side="left")

        tk.Label(load_row, text="  Highlight Group:").pack(side="left", padx=(12, 2))
        self.group_highlight_var = tk.StringVar(value="All")
        self.group_highlight_menu = ttk.Combobox(
            load_row, textvariable=self.group_highlight_var, state="readonly", width=10
        )
        self.group_highlight_menu["values"] = ["All"] + [str(i) for i in range(1, 11)]
        self.group_highlight_menu.pack(side="left", padx=5)

        tk.Button(load_row, text="Apply Group Highlighting",
                  command=self.render_preview).pack(side="left", padx=6)

        # Preview area
        self.preview = scrolledtext.ScrolledText(bottom, height=20, font=("Courier New", 10))
        self.preview.pack(fill="both", expand=True)

        # Optional: add a horizontal scrollbar
        hscroll = tk.Scrollbar(bottom, orient="horizontal", command=self.preview.xview)
        self.preview.configure(xscrollcommand=hscroll.set)
        hscroll.pack(fill="x", side="bottom")


    def refresh_config_list(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        files = [f[:-5] for f in os.listdir(CONFIG_DIR) if f.endswith(".json")]
        self.config_picker["values"] = files

    def load_selected_config(self, event=None):
        name = self.config_picker.get()
        path = os.path.join(CONFIG_DIR, f"{name}.json")
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.report_name.delete(0, "end")
        self.report_name.insert(0, name)
        self.header_skip.delete(0, "end")
        self.header_skip.insert(0, config.get("header_skip", 0))
        self.footer_skip.delete(0, "end")
        self.footer_skip.insert(0, config.get("footer_skip", 0))
        self.use_date_var.set(config.get("use_content_date", False))
        self.show_header_var.set(config.get("show_csv_header", False))

        self.field_table.delete(*self.field_table.get_children())
        for f in config.get("fields", []):
            row = (
                f.get("label", ""),
                f.get("group", 1),
                f.get("line", 0),
                f.get("left", 0),
                f.get("right", 0),
                f.get("color", "#FFFFCC"),
            )
            self.field_table.insert("", "end", values=row)

        self.render_preview()

    def add_field(self):
        self.field_table.insert("", "end", values=("FIELD_NAME", "1", "0", "0", "10", "#FFCCCC"))
        self.render_preview()

    def delete_field(self):
        for item in self.field_table.selection():
            self.field_table.delete(item)
        self.render_preview()

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt *.rpt")])
        if not path:
            return
        self.selected_file = path
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            self.text_data = f.read()
        self.preview_lines = self.text_data.splitlines()
        self.render_preview()

    def render_preview(self):
        self.preview.delete("1.0", "end")
        header_skip = int(self.header_skip.get())
        footer_skip = int(self.footer_skip.get())
        lines = self.preview_lines[header_skip:len(self.preview_lines) - footer_skip]

        for idx, line in enumerate(lines):
            self.preview.insert(f"{idx + 1}.0", line + "\n")

        selected_group = self.group_highlight_var.get()

        for row in self.field_table.get_children():
            vals = self.field_table.item(row)["values"]
            try:
                label, group, rel_line, left, right, color = vals
                group = int(group)
                rel_line = int(rel_line)
                left = int(left)
                right = int(right)

                if selected_group != "All" and str(group) != selected_group:
                    continue

                if rel_line == 0:
                    for idx in range(len(lines)):
                        tag = f"tag_{idx+1}_{left}_{right}"
                        self.preview.tag_add(tag, f"{idx+1}.{left}", f"{idx+1}.{right}")
                        self.preview.tag_config(tag, background=color)
                else:
                    tag_line = rel_line + 1
                    if tag_line <= len(lines):
                        tag = f"tag_{tag_line}_{left}_{right}"
                        self.preview.tag_add(tag, f"{tag_line}.{left}", f"{tag_line}.{right}")
                        self.preview.tag_config(tag, background=color)
            except Exception:
                continue

    def edit_cell(self, event):
        item = self.field_table.identify_row(event.y)
        column = self.field_table.identify_column(event.x)
        if not item or not column:
            return

        col_idx = int(column.replace("#", "")) - 1
        col_name = self.field_table["columns"][col_idx]
        x, y, width, height = self.field_table.bbox(item, column)
        value = self.field_table.set(item, col_name)

        if col_name == "color":
            new_color = colorchooser.askcolor(title="Pick Highlight Color", color=value)[1]
            if new_color:
                self.field_table.set(item, col_name, new_color)
                self.render_preview()
        else:
            entry = tk.Entry(self.field_table)
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, value)
            entry.focus()

            def on_return(e):
                self.field_table.set(item, col_name, entry.get())
                entry.destroy()
                self.render_preview()

            entry.bind("<Return>", on_return)
            entry.bind("<FocusOut>", lambda e: entry.destroy())

    def save_config(self):
        config = {
            "report_name": self.report_name.get(),
            "header_skip": int(self.header_skip.get()),
            "footer_skip": int(self.footer_skip.get()),
            "use_content_date": self.use_date_var.get(),
            "show_csv_header": self.show_header_var.get(),
            "fields": [],
        }
        for row in self.field_table.get_children():
            vals = self.field_table.item(row)["values"]
            config["fields"].append({
                "label": vals[0],
                "group": int(vals[1]),
                "line": vals[2],
                "left": int(vals[3]),
                "right": int(vals[4]),
                "color": vals[5]
            })

        report_name = self.report_name.get().strip()
        
        if not report_name:
            messagebox.showerror("Missing Name", "Please enter a Report Name.")
            return
        filename = f"{CONFIG_DIR}/{report_name}.json"
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        messagebox.showinfo("Saved", f"Saved as {filename}")
        self.refresh_config_list()


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartReportGUI(root)
    root.mainloop()
