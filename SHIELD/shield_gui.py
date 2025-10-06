# shield_gui.py
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog
import os
from collections import Counter
import json
from pathlib import Path

from file_loader import get_file_text
from regex_extractor import extract_fields, load_regex_patterns
from pii_detection import detect_entities, load_model
from feedback_loop import collect_user_feedback
from obfuscator import obfuscate_text
from trainer import train_model
from utils import clean_entity_spans, extract_spans_from_smart_config
from smarts_engine import load_smarts_rules

FEEDBACK_FILE = "data/feedback.json"
OUTPUT_DIR = Path("data/obfuscated")

class ShieldGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SHIELD - PII Detection & Obfuscation")
        self.text = ""
        self.filename = None
        self.entities = []
        self.tree_data = []
        self.setup_ui()
        # --- SMARTS selection state (directory-based) ---
        self.smarts_dir = os.path.join("config")  # folder containing individual report configs
        self.smarts_var = tk.StringVar(value="")          # bound to dropdown (shows a friendly name)
        self.smarts_files = {}                    # display_name -> full path
        self.selected_smarts_path = None          # full path to selected JSON
        # JSONs to ignore (schema helpers / non-report configs)
        self._ignore_json = {
            "smarts_rules.json",
            "smarts_report_configs.json",  # legacy aggregate file
            "field_patterns.json",         # if you ever have one
        }
        self.extraction_types = {
            "spaCy NLP": tk.BooleanVar(value=True),
            "Regex": tk.BooleanVar(value=True),
            "SMARTS": tk.BooleanVar(value=True),
        }

    def setup_ui(self):
        self.root.geometry("1100x700")

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Left-side actions
        tk.Button(top_frame, text="Upload File", command=self.load_file).pack(side="left", padx=5)
        tk.Button(top_frame, text="Extract Entities", command=self.extract_entities).pack(side="left", padx=5)
        tk.Button(top_frame, text="Extraction Options", command=self.show_extraction_menu).pack(side="left", padx=5)
        tk.Button(top_frame, text="Obfuscate & Save", command=self.obfuscate_and_save).pack(side="left", padx=5)
        tk.Button(top_frame, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(top_frame, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=5)

        # --- SMARTS dropdown (directory-based) ---
        # Ensure state exists even if __init__ ordering changes
        if not hasattr(self, "smarts_var"):
            self.smarts_var = tk.StringVar()
        if not hasattr(self, "smarts_dir"):
            self.smarts_dir = os.path.join("config")
        if not hasattr(self, "smarts_files"):
            self.smarts_files = {}
        if not hasattr(self, "_ignore_json"):
            self._ignore_json = {"smarts_rules.json", "smarts_report_configs.json", "field_patterns.json"}
        if not hasattr(self, "selected_smarts_path"):
            self.selected_smarts_path = None

        tk.Label(top_frame, text="SMARTS Config:").pack(side="left", padx=(10, 2))
        self.smarts_combo = ttk.Combobox(
            top_frame,
            textvariable=self.smarts_var,
            state="readonly",
            width=28
        )
        self.smarts_combo.pack(side="left", padx=5)
        self.smarts_combo.bind("<<ComboboxSelected>>", self.on_smarts_selected)

        ttk.Button(top_frame, text="Refresh SMARTS", command=self.refresh_smarts_dropdown).pack(side="left", padx=5)

        # populate on launch
        self.refresh_smarts_dropdown()

        # --- Main split view ---
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
            self.filename = os.path.basename(path) if path else ""
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

            # Warm up model/rules/patterns
            nlp = load_model() if use_spacy else None  # triggers loader & fallback once
            patterns = load_regex_patterns() if use_regex else []
            rules = load_smarts_rules() if use_smarts else {}
            print("Loaded SMARTS rules:", len(rules))

            entities = []

            # --- spaCy ---
            if use_spacy:
                # use centralized detect_entities to benefit from fallback normalization
                spacy_ents = detect_entities(self.text)
                # convert to (value,label,start,end) tuples for unified handling
                entities += [(val, lbl, s, e) for (val, lbl, s, e) in spacy_ents]

            # --- Regex ---
            if use_regex and patterns:
                regex_results = extract_fields(self.text, patterns)
                entities += [(r["text"], r["label"], r["start"], r["end"]) for r in regex_results]


            # --- SMARTS (optional via dropdown; robust selection resolution) ---
            if use_smarts:
                # Read from the widget first (most reliable), then var as fallback
                chosen_name = ""
                try:
                    if hasattr(self, "smarts_combo"):
                        chosen_name = (self.smarts_combo.get() or "").strip()
                except Exception:
                    pass
                if not chosen_name:
                    chosen_name = (self.smarts_var.get() or "").strip()

                print(f"[SMARTS] combobox.get='{(self.smarts_combo.get() if hasattr(self, 'smarts_combo') else '')}', "
                      f"var='{self.smarts_var.get() if hasattr(self, 'smarts_var') else ''}', "
                      f"resolved='{chosen_name}'")

                if not chosen_name:
                    print("[SMARTS] skipped: blank selection.")
                else:
                    # Always resolve the path at use-time in case event didn’t fire
                    cfg_path = self.smarts_files.get(chosen_name)
                    if not cfg_path:
                        # try case-insensitive match
                        for k, v in self.smarts_files.items():
                            if k.lower() == chosen_name.lower():
                                cfg_path = v
                                break

                    if not cfg_path or not os.path.isfile(cfg_path):
                        messagebox.showwarning("SMARTS", f"Config not found for '{chosen_name}'. Skipping SMARTS.")
                        print(f"[SMARTS] not found: '{chosen_name}'")
                    else:
                        try:
                            with open(cfg_path, "r", encoding="utf-8") as f:
                                cfg = json.load(f)
                            # Use your existing util which must return (value,label,start,end)
                            smarts_entities = extract_spans_from_smart_config(self.text, cfg) or []
                            print(f"[SMARTS] file: {cfg_path} -> entities: {len(smarts_entities)}")
                            if not smarts_entities:
                                print("[SMARTS] NOTE: config applied but returned 0 entities (check line/left/right/header/footer).")
                            entities += smarts_entities
                        except Exception as ex:
                            import traceback; print(traceback.format_exc())
                            messagebox.showerror("SMARTS Error", f"Failed applying SMARTS config:\n{ex}")
                            return


            # --- Finalize / dedupe / sort ---
            entities = clean_entity_spans(entities)  # keeps (value,label,start,end)
            # Stable sort by (start,end,label) for nicer UI
            entities.sort(key=lambda t: (int(t[2]), int(t[3]), str(t[1])))

            self.entities = entities
            self.tree_data = entities.copy()
            self.refresh_table(self.tree_data)

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messagebox.showerror("Detection Error", str(e))

    def show_extraction_menu(self):
        popup = tk.Toplevel(self.root)
        popup.title("Select Extraction Types")
        popup.geometry("220x160")
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
        if counts:
            summary += "Entity Counts: " + ", ".join(f"{k}: {v}" for k, v in counts.items())
        else:
            summary += "Entity Counts: —"
        self.summary_label.config(text=summary)

    def obfuscate_and_save(self):
        if not self.text or not self.tree_data:
            messagebox.showwarning("No Action", "No valid entities to obfuscate.")
            return

        updated_entities = collect_user_feedback(self.text, self.tree_data)
        if not updated_entities:
            messagebox.showinfo("No Action", "No confirmed entities to save.")
            return  # <-- important, avoid training/obfuscating nothing

        # Write full metadata to feedback and train
        summary = train_model(self.text, updated_entities, FEEDBACK_FILE)

        # Only use (start, end, label) for obfuscation
        spans_for_obfuscation = [(e["start"], e["end"], e["label"]) for e in updated_entities]
        obfuscated = obfuscate_text(self.text, spans_for_obfuscation)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "obfuscated_output.txt"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(obfuscated)

        msg = "Obfuscation and training completed.\n"
        if isinstance(summary, dict) and summary.get("status"):
            msg += f"\nModel: {summary.get('model_path')}\n"
            msg += f"Examples trained: {summary.get('examples_trained')}\n"
            msg += f"Dropped (misaligned): {summary.get('dropped_misaligned')}"
        messagebox.showinfo("Success", msg)

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
                if not (int(row[2]) == start and int(row[3]) == end)
            ]

        self.refresh_table(self.tree_data)

    def edit_selected(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select an entity to edit.")
            return

        item = self.tree.item(selected_items[0])
        values = item["values"]
        if len(values) < 3:
            messagebox.showwarning("Invalid Selection", "Selected item is malformed.")
            return

        old_value, old_label, old_span = values[:3]
        new_value = simpledialog.askstring("Edit Value", "New Value:", initialvalue=old_value)
        new_label = simpledialog.askstring("Edit Label", "New Label:", initialvalue=old_label)

        if not new_value or not new_label:
            return

        try:
            new_start, new_end = map(int, old_span.split('-'))
        except Exception:
            return

        for idx, row in enumerate(self.tree_data):
            if (
                str(row[0]) == str(old_value)
                and str(row[1]) == str(old_label)
                and int(row[2]) == new_start
                and int(row[3]) == new_end
            ):
                updated_row = (new_value, new_label, new_start, new_end) + tuple(row[4:])
                self.tree_data[idx] = updated_row
                break

        self.refresh_table(self.tree_data)

    def refresh_smarts_dropdown(self):
        """Scan config/ for SMARTS JSON configs and populate the dropdown (blank first),
        while preserving the user's current selection if still available."""
        self.smarts_files = {}

        # read what's currently visible in the Combobox (more reliable than var)
        current_display = ""
        try:
            if hasattr(self, "smarts_combo"):
                current_display = (self.smarts_combo.get() or "").strip()
        except Exception:
            pass

        display_names = [""]  # blank option first

        try:
            if not os.path.isdir(self.smarts_dir):
                os.makedirs(self.smarts_dir, exist_ok=True)

            for fname in sorted(os.listdir(self.smarts_dir)):
                if not fname.lower().endswith(".json"):
                    continue
                if fname in getattr(self, "_ignore_json", set()):
                    continue

                full = os.path.join(self.smarts_dir, fname)
                display = os.path.splitext(fname)[0]
                try:
                    with open(full, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    rn = (isinstance(data, dict) and data.get("report_name")) or ""
                    rn = str(rn).strip()
                    if rn:
                        display = rn
                except Exception as e:
                    print(f"[SMARTS] warn: cannot parse {fname}: {e}")

                if display in self.smarts_files:
                    display = f"{display} ({fname})"

                self.smarts_files[display] = full
                display_names.append(display)

            print(f"[SMARTS] dropdown loaded {len(display_names)-1} configs")
        except Exception as e:
            print(f"[SMARTS] scan error: {e}")

        if hasattr(self, "smarts_combo"):
            self.smarts_combo["values"] = display_names

            # prefer preserving what the user sees, if it still exists
            if current_display in display_names and current_display != "":
                self.smarts_combo.set(current_display)
                self.smarts_var.set(current_display)  # keep var in sync
                self.selected_smarts_path = self.smarts_files.get(current_display)
            else:
                # keep/reset to blank
                self.smarts_combo.set("")
                self.smarts_var.set("")
                self.selected_smarts_path = None


    def on_smarts_selected(self, event=None):
        name = (self.smarts_var.get() or "").strip()
        self.selected_smarts_path = self.smarts_files.get(name) if name else None


    def _validate_smarts_config(self, cfg: dict) -> tuple[bool, str]:
        if not isinstance(cfg, dict):
            return False, "Config is not a JSON object."
        if "fields" not in cfg or not isinstance(cfg["fields"], list):
            return False, "Missing 'fields' list."
        # soft validation of fields
        for i, f in enumerate(cfg["fields"]):
            if not isinstance(f, dict):
                return False, f"Field #{i+1} is not an object."
            for k in ("label", "line", "left", "right"):
                if k not in f:
                    return False, f"Field #{i+1} missing '{k}'."
        return True, ""



if __name__ == "__main__":
    root = tk.Tk()
    app = ShieldGUI(root)
    root.mainloop()
