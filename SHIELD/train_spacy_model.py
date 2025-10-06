# train_spacy_model.py
import subprocess
from pathlib import Path
import shutil
import sys

OUTPUT_DIR = Path("model/on_prem_nlp_model")    # parent dir
TRAIN_PATH = Path("model/training/train.spacy")
DEV_PATH   = Path("model/dev/dev.spacy")
ACTIVE_DIR = OUTPUT_DIR / "active"              # stable, always-loadable model

def _copytree_overwrite(src: Path, dst: Path):
    if dst.exists():
        if dst.is_file():
            dst.unlink(missing_ok=True)
        else:
            shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)

def train_model():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Starting spaCy training...")
    cmd = [
        sys.executable, "-m", "spacy", "train", "config.cfg",
        "--output", str(OUTPUT_DIR),
        "--paths.train", str(TRAIN_PATH),
        "--paths.dev", str(DEV_PATH),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Training failed.\n--- STDOUT ---\n", result.stdout, "\n--- STDERR ---\n", result.stderr)
        return 1

    print(result.stdout)
    best = OUTPUT_DIR / "model-best"
    last = OUTPUT_DIR / "model-last"

    if best.exists():
        _copytree_overwrite(best, ACTIVE_DIR)
        promoted = "model-best"
    elif last.exists():
        _copytree_overwrite(last, ACTIVE_DIR)
        promoted = "model-last"
    else:
        print("No model-best or model-last produced; cannot promote an active model.")
        return 2

    print(f"Training complete.\n - Best: {best}\n - Last: {last}\n → Promoted: {promoted} → {ACTIVE_DIR}")
    return 0

if __name__ == "__main__":
    raise SystemExit(train_model())
