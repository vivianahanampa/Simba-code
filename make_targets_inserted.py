"""
Build SimBA targets_inserted files from features_extracted files + the scoring-sheet labels.

Replaces SimBA's "Label behavior" step when the labels already exist in the scoring sheet.
Run it once per behavior. Each run fills ONE behavior column and keeps every other behavior
column that is already in the file (so a Flee run does not erase Attack).

Usage (inside the SimBA conda environment, Windows or Mac):
    # Attack (done already)
    python make_targets_inserted.py --config "...\\project_config.ini" --labels attack_sheet_bouts.json --scorer rater1 --behavior Attack --holdout 778 784 787
    # Flee, same project
    python make_targets_inserted.py --config "...\\project_config.ini" --labels flee_sheet_bouts.json --scorer rater1 --behavior Flee --holdout 778 784 787

Reads:   <project_folder>/csv/features_extracted/*.csv
         <project_folder>/csv/targets_inserted/*.csv and csv/heldout_test_annotations/*.csv, if they exist (labels to keep)
Writes:  <project_folder>/csv/targets_inserted/<same name>.csv             training trials
         <project_folder>/csv/heldout_test_annotations/<same name>.csv     --holdout trials, NOT used for training
         <project_folder>/csv/heldout_<behavior>/<same name>.csv           held-out trials scored for this behavior:
                                                                           use this folder for --annotations when evaluating

Held-out trials are per project: holding a trial out for Flee also takes it out of Attack training,
so use the same --holdout list for every behavior.

Labels JSON format (see example_bouts.json): {"rater1": {"776": [[onset, offset], ...], ...}, "rater2": {...}}
with inclusive 0-based frames; --scorer picks the key.
A trial with an empty list was scored and has none of the behavior.
A trial missing from the JSON was not scored for this behavior: its file is left as it is, and if it sits in
targets_inserted you get a warning, because SimBA would learn "no <behavior>" from all of its frames.
"""
import argparse
import configparser
import json
import os
import re
import shutil
import sys

import numpy as np
import pandas as pd


def trial_number(name):
    # First 3+ digit number, so "Trial 776DLC_Resnet50_..._best-140.csv" still gives 776.
    found = re.findall(r"\d{3,}", name)
    return found[0] if found else None


def behaviors_from_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    n = config.getint("SML settings", "no_targets")
    return [config.get("SML settings", f"target_name_{i}") for i in range(1, n + 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", required=True, help="Path to the project's project_config.ini")
    parser.add_argument("--labels", required=True, help="attack_sheet_bouts.json or flee_sheet_bouts.json")
    parser.add_argument("--scorer", required=True, help="Which scorer's bouts to use (a top-level key of the labels JSON)")
    parser.add_argument("--behavior", default="Attack", help="Behavior the bouts belong to (default Attack)")
    parser.add_argument("--holdout", nargs="*", default=[], help="Trial numbers to keep out of training")
    args = parser.parse_args()

    project = os.path.dirname(os.path.abspath(args.config))
    features_dir = os.path.join(project, "csv", "features_extracted")
    train_dir = os.path.join(project, "csv", "targets_inserted")
    heldout_dir = os.path.join(project, "csv", "heldout_test_annotations")
    eval_dir = os.path.join(project, "csv", f"heldout_{args.behavior}")
    behaviors = behaviors_from_config(args.config)
    if args.behavior not in behaviors:
        sys.exit(f"'{args.behavior}' is not one of the project's behaviors: {behaviors}")
    labels_json = json.load(open(args.labels))
    if args.scorer not in labels_json:
        sys.exit(f"No scorer '{args.scorer}' in {args.labels}. Choose one of: {[k for k in labels_json if not k.startswith('_')]}")
    bouts_by_trial = labels_json[args.scorer]

    files = sorted(f for f in os.listdir(features_dir) if f.endswith(".csv"))
    if not files:
        sys.exit(f"No .csv files in {features_dir}. Run Extract features first.")
    for d in (train_dir, heldout_dir, eval_dir):
        os.makedirs(d, exist_ok=True)

    unscored_in_training = []
    for name in files:
        trial = trial_number(name)
        train_path, heldout_path = os.path.join(train_dir, name), os.path.join(heldout_dir, name)
        if trial not in bouts_by_trial:
            if os.path.exists(train_path):
                unscored_in_training.append(trial)
            print(f"[skip] {name}: trial {trial} has no {args.scorer} {args.behavior} labels in {args.labels}")
            continue

        df = pd.read_csv(os.path.join(features_dir, name), index_col=0)
        n = len(df)
        # Labels of the other behaviors come from the existing labelled file, if there is one.
        existing = heldout_path if os.path.exists(heldout_path) else train_path if os.path.exists(train_path) else None
        old = None
        if existing:
            label_cols = [c for c in pd.read_csv(existing, nrows=0).columns if c in behaviors]
            old = pd.read_csv(existing, usecols=label_cols)
        if old is not None and len(old) != n:
            sys.exit(f"{existing} has {len(old)} rows but the features file has {n}. Stopping so no labels get misaligned.")
        label = np.zeros(n, dtype=int)
        for onset, offset in bouts_by_trial[trial]:
            if offset >= n:
                print(f"[warn] {name}: bout {onset}-{offset} goes past the last frame ({n - 1}); clipped")
            label[onset:min(offset, n - 1) + 1] = 1
        cols = {b: label if b == args.behavior else (old[b].to_numpy() if old is not None and b in old.columns else 0) for b in behaviors}
        df = pd.concat([df.drop(columns=[b for b in behaviors if b in df.columns]), pd.DataFrame(cols, index=df.index)], axis=1)
        kept = [b for b in behaviors if b != args.behavior and df[b].sum() > 0]

        held = trial in args.holdout
        out_path = heldout_path if held else train_path
        other_path = train_path if held else heldout_path
        df.to_csv(out_path)
        if os.path.exists(other_path):
            os.remove(other_path)
            print(f"[moved] {name}: removed the copy in {'targets_inserted' if held else 'heldout_test_annotations'}; "
                  f"it is now {'HELD OUT' if held else 'training'} for every behavior")
        if held:
            shutil.copyfile(out_path, os.path.join(eval_dir, name))
        where = "HELD OUT" if held else "training"
        keep_note = f" (kept {', '.join(kept)})" if kept else ""
        print(f"{name}: {n} frames, {len(bouts_by_trial[trial])} bouts, {label.sum()} {args.behavior} frames -> {where}{keep_note}")

    print(f"\nTraining files:  {train_dir}\nHeld-out files:  {heldout_dir}\nEvaluate {args.behavior} with --annotations {eval_dir}")
    if unscored_in_training:
        print(f"\n!!! WARNING: trial(s) {', '.join(unscored_in_training)} are in targets_inserted but have no {args.behavior} labels.\n"
              f"!!! Their {args.behavior} column is all 0, so SimBA will learn 'no {args.behavior}' from them.\n"
              f"!!! Before training {args.behavior}: move those files out of targets_inserted (put them back for other behaviors),\n"
              f"!!! or add them to the JSON as [] if they truly have no {args.behavior}.")


if __name__ == "__main__":
    main()
