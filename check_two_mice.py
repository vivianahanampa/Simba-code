"""
Check whether both animals have pose coordinates in every file of a SimBA folder.

Works on any SimBA csv folder (input_csv, outlier_corrected_movement_location, features_extracted,
targets_inserted, machine_results) and on .parquet files. Animals are found from the column names
(<bodypart>_<animal>_x / _y / _p), so it also works for configs other than 2 x 11 body-parts.

Usage:
    python check_two_mice.py /path/to/project_folder/csv/input_csv
    python check_two_mice.py folder1 folder2 ...      # e.g. one folder per SimBA step

For each file and animal it prints:
    tracked   % of frames where at least one body-part is not at x = y = 0 (and not empty)
    moves     % of tracked frames where the animal's position changes from the previous frame
    x / y     range of the animal's coordinates over the whole video
    conf      mean likelihood (_p) of that animal's body-parts
An animal with tracked = 0% and x, y = 0-0 has no position data in that file.
An animal with tracked > 0% but moves near 0% is frozen: its positions were overwritten.

input_csv keeps DeepLabCut's 3 header rows; this script reads files with one header row, so for
input_csv it will report "no <part>_<n>_x columns found". Check outlier_corrected_movement_location
and later folders with it.
"""
import os
import re
import sys

import pandas as pd

COORD = re.compile(r"^(?P<part>.+)_(?P<animal>\d+)_(?P<axis>[xyp])$")


def read_table(path):
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path, index_col=0, low_memory=False)


def check_file(path):
    df = read_table(path)
    animals = {}
    for col in df.columns:
        m = COORD.match(str(col))
        if m:
            animals.setdefault(m["animal"], {}).setdefault(m["axis"], []).append(col)
    rows = []
    for animal, cols in sorted(animals.items(), key=lambda kv: int(kv[0])):
        x = df[cols.get("x", [])].apply(pd.to_numeric, errors="coerce")
        y = df[cols.get("y", [])].apply(pd.to_numeric, errors="coerce")
        p = df[cols.get("p", [])].apply(pd.to_numeric, errors="coerce")
        xv, yv = x.fillna(0).to_numpy(), y.fillna(0).to_numpy()
        present = (xv != 0) | (yv != 0)
        # A frozen animal has coordinates but never moves (e.g. after bad outlier correction).
        changed = (abs(xv[1:] - xv[:-1]) + abs(yv[1:] - yv[:-1]) > 0.01).any(axis=1)
        present_any = present.any(axis=1)
        moves = changed[present_any[1:]].mean() if present_any[1:].any() else 0.0
        rows.append(dict(
            file=os.path.basename(path), animal=animal, body_parts=len(cols.get("x", [])), frames=len(df),
            tracked=f"{present_any.mean():.0%}", moves=f"{moves:.0%}",
            x=f"{x.min().min():.0f}-{x.max().max():.0f}", y=f"{y.min().min():.0f}-{y.max().max():.0f}",
            conf=round(float(p.mean().mean()), 2) if len(p.columns) else None,
        ))
    if not rows:
        rows.append(dict(file=os.path.basename(path), animal="?", body_parts=0, frames=len(df),
                         tracked="no <part>_<n>_x columns found", x="", y="", conf=None))
    return rows


def main(folders):
    pd.set_option("display.width", 200)
    for folder in folders:
        files = sorted(f for f in os.listdir(folder) if f.endswith((".csv", ".parquet")))
        print(f"\n=== {folder}  ({len(files)} files)")
        rows = []
        for name in files:
            try:
                rows.extend(check_file(os.path.join(folder, name)))
            except Exception as error:  # keep going so one bad file doesn't hide the rest
                rows.append(dict(file=name, animal="!", tracked=f"could not read: {error}"))
        if rows:
            print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
