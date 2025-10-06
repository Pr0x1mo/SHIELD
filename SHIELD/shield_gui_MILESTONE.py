# upgraded_shield_gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog
import os
from file_loader import get_file_text
from regex_extractor import extract_fields, load_regex_patterns
from pii_detection import detect_entities, load_model
from feedback_loop import collect_user_feedback
from obfuscator import obfuscate_text
from trainer import train_model
from collections import Counter
import json
from utils import clean_entity_spans, hybrid_entity_extraction, extract_spans_from_smart_config
from smarts_engine import load_smarts_rules, apply_smarts_rules
import spacy
from pathlib import Path

FEEDBACK_FILE = "data/feedback.json"
OUTPUT_DIR = "data/obfuscated"

class ShieldGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - PII Detection & Obfuscation")
        self.text = ""
        self.filename = None
        self.entities = []
        self.tree_data = []
        self.setup_ui()
        self.extraction_types = {"spaCy NLP": tk.BooleanVar(value=True),"Regex": tk.BooleanVar(value=True),"SMARTS": tk.BooleanVar(value=True)}

    def setup_ui(self):
        self.root.geometry("1100x700")

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)


        tk.Button(top_frame, text="Upload File", command=self.load_file).pack(side="left", padx=5)
        tk.Button(top_frame, text="Extract Entities", command=self.extract_entities).pack(side="left", padx=5)
        tk.Button(top_frame, text="Extraction Options", command=self.show_extraction_menu).pack(side="left", padx=5)
        tk.Button(top_frame, text="Obfuscate & Save", command=self.obfuscate_and_save).pack(side="left", padx=5)
        tk.Button(top_frame, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(top_frame, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=5)

        main_frame = tk.PanedWindow(self.root, sashrelief=tk.RAISED, sashwidth=5)
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # LEFT: Text display
        self.output = scrolledtext.ScrolledText(main_frame, width=70)
        main_frame.add(self.output)

        # RIGHT: Table of entities
        right_frame = tk.Frame(main_frame)
        main_frame.add(right_frame)

        columns = ("value", "label", "span")
        self.tree = ttk.Treeview(right_frame, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=140 if col != "value" else 250)
        self.tree.pack(fill="both", expand=True)

        self.summary_label = tk.Label(right_frame, text="", anchor="w", justify="left", font=("Courier", 9))
        self.summary_label.pack(fill="x")

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[
            ("Supported Files", "*.txt *.csv *.pdf *.rpt *.rpgrpt")
        ])
        if not path:
            return

        try:
            self.text = get_file_text(path)
            self.filename = os.path.basename(path)
            self.output.delete(1.0, tk.END)
            self.output.insert(tk.END, self.text)
            self.entities = []
            self.tree_data = []
            self.refresh_table([])
        except Exception as e:
            messagebox.showerror("File Error", str(e))

    def extract_entities(self):
        if not self.text:
            messagebox.showwarning("No Input", "Please upload a file first.")
            return

        try:
            # Detect which modes are selected
            use_spacy = self.extraction_types["spaCy NLP"].get()
            use_regex = self.extraction_types["Regex"].get()
            use_smarts = self.extraction_types["SMARTS"].get()

            nlp = load_model() if use_spacy else None
            patterns = load_regex_patterns() if use_regex else []
            rules = load_smarts_rules() if use_smarts else {}
            print("Loaded SMARTS rules:", len(rules))

            # === Phase 1: Collect base entities ===
            entities = []

            # Always extract base entities if SMARTS is selected alone
            if (use_spacy or use_smarts) and nlp:
                doc = nlp(self.text)
                entities += [(ent.text, ent.label_, ent.start_char, ent.end_char) for ent in doc.ents]

            if (use_regex or use_smarts) and patterns:
                from regex_extractor import extract_fields
                regex_results = extract_fields(self.text, patterns)
                entities += [(r["text"], r["label"], r["start"], r["end"]) for r in regex_results]
            

            # === Phase 2: Apply SMARTS Rules ===
            if use_smarts:
                import json
                smarts_entities = []

                config_path = os.path.join("config", "smarts_report_configs.json")
                with open(config_path, "r", encoding="utf-8") as f:
                    all_configs = json.load(f)

                # Try to match report config by filename
                matched_config = None
                for cfg in all_configs:
                    report_name = cfg.get("report_name", "").lower()
                    if report_name and report_name in self.filename.lower():
                        matched_config = cfg
                        break

                if matched_config:
                    print("Matched SMART report config:", matched_config["report_name"])
                    smarts_entities = extract_spans_from_smart_config(self.text, matched_config)
                else:
                    print("No SMART config matched for file:", self.filename)

                entities += smarts_entities


            # === Finalize ===
            from utils import clean_entity_spans
            self.entities = clean_entity_spans(entities)
            self.tree_data = self.entities.copy()
            self.refresh_table(self.tree_data)


        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messagebox.showerror("Detection Error", str(e))



    def show_extraction_menu(self):
        popup = tk.Toplevel(self.root)
        popup.title("Select Extraction Types")
        popup.geometry("200x150")
        tk.Label(popup, text="Choose Extraction Methods:").pack(pady=5)

        for name, var in self.extraction_types.items():
            tk.Checkbutton(popup, text=name, variable=var).pack(anchor="w")

        tk.Button(popup, text="Close", command=popup.destroy).pack(pady=10)

    def refresh_table(self, entities):
        self.tree.delete(*self.tree.get_children())
        counts = Counter()
        if entities is not None:
            self.tree_data = entities

        for ent in self.tree_data:
            try:
                value = ent[0]
                label = ent[1]
                start = int(ent[2])
                end = int(ent[3])
                span = f"{start}-{end}"
            except Exception as e:
                print("Skipping malformed entity:", ent, e)
                continue

            self.tree.insert("", "end", values=(value, label, span))
            counts[label] += 1

        summary = f"Total Entities: {len(self.tree_data)}\n"
        summary += "Entity Counts: " + ", ".join(f"{k}: {v}" for k, v in counts.items())
        self.summary_label.config(text=summary)


    def obfuscate_and_save(self):
        if not self.text or not self.tree_data:
            messagebox.showwarning("No Action", "No valid entities to obfuscate.")
            return

        # Get confirmed entities from terminal
        updated_entities = collect_user_feedback(self.text, self.tree_data)

        if not updated_entities:
            messagebox.showinfo("No Action", "No confirmed entities to save.")
            

        # Write full metadata to feedback and train
        train_model(self.text, updated_entities, FEEDBACK_FILE)

        # Only use (start, end, label) for obfuscation
        spans_for_obfuscation = [(e["start"], e["end"], e["label"]) for e in updated_entities]
        obfuscated = obfuscate_text(self.text, spans_for_obfuscation)

        with open("obfuscated_output.txt", "w", encoding="utf-8") as f:
            f.write(obfuscated)

        messagebox.showinfo("Success", "Obfuscation and training completed. Output saved.")



    def delete_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Select rows to delete.")
            return

        for item_id in selected_items:
            selected_values = self.tree.item(item_id)['values']
            selected_span = selected_values[2]
            start, end = map(int, selected_span.split('-'))
            self.tree_data = [
                row for row in self.tree_data
                if not (row[2] == start and row[3] == end)
            ]

        self.refresh_table(self.tree_data)

    def edit_selected(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("No Selection", "Please select an entity to edit.")
            return

        item = self.tree.item(selected_item)
        values = item["values"]
        if len(values) < 3:
            messagebox.showwarning("Invalid Selection", "Selected item is malformed.")
            return

        old_value, old_label, old_span = values[:3]
        new_value = simpledialog.askstring("Edit Value", "New Value:", initialvalue=old_value)
        new_label = simpledialog.askstring("Edit Label", "New Label:", initialvalue=old_label)

        if not new_value or not new_label:
            return

        # Extract original start/end
        try:
            new_start, new_end = map(int, old_span.split('-'))
        except:
            return

        # Update matching row in self.tree_data
        for idx, row in enumerate(self.tree_data):
            if row[0] == old_value and row[1] == old_label and str(row[2]) == str(new_start) and str(row[3]) == str(new_end):
                # preserve any extra columns
                updated_row = (new_value, new_label, new_start, new_end) + tuple(row[4:])
                self.tree_data[idx] = updated_row
                break

        self.refresh_table(self.tree_data)



if __name__ == "__main__":
    root = tk.Tk()
    app = ShieldGUI(root)
    root.mainloop()
