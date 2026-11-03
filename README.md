# Simba-code

Helper scripts and step-by-step recipes for training [SimBA](https://github.com/sgoldenlab/simba) behavior classifiers when the hand-scored labels already live in a spreadsheet.

Built for: 2 mice × 11 body parts (22 DeepLabCut keypoints), classic (non-multi-animal) tracking, SimBA 5.4.4 on Windows, 30 fps. Behaviors so far: **Attack**, then **Flee**.

## What's here

| File | What it does |
|---|---|
| `check_two_mice.py` | For each trial and animal: % of frames tracked, % moving, x/y range, mean confidence. Catches a mouse that is **missing** (all 0) or **frozen** (positions overwritten). |
| `make_targets_inserted.py` | Writes bouts from a JSON file into SimBA's `targets_inserted` files, **one behavior per run**, keeping the labels of the other behaviors. Held-out trials go to separate folders so they're never trained on. |
| `evaluate_simba_test_videos.py` | Scores SimBA's predictions on the held-out trials: precision, recall, F1, bout counts and total time per video, plus an optional threshold sweep. |
| `example_bouts.json` | The label format (made-up numbers). |
| `flee_sheet_bouts.json` | Our Flee annotations from two raters (keys `Nick`, `HP`; `_about` explains the rest). |
| `SimBA_new_project_recipe.md` | Step-by-step rebuild of a SimBA project with the fixes below (Attack). |
| `SimBA_flee_recipe.md` | Adding a second behavior (Flee) to the same project. |

## Quick start

Inside SimBA's conda environment (`conda activate simba`; needs only pandas and numpy):

```powershell
# 1. Are both mice there and moving?
python check_two_mice.py "<project_folder>\csv\outlier_corrected_movement_location"

# 2. Labels -> SimBA (once per behavior; use the same held-out trials every time)
python make_targets_inserted.py --config "<project_folder>\project_config.ini" --labels my_bouts.json --scorer rater1 --behavior Attack --holdout 778 784 787

# 3. Train and run the model in SimBA, then score the held-out trials
python evaluate_simba_test_videos.py --project "<project_folder>" --annotations "<project_folder>\csv\heldout_Attack" --classifier Attack --fps 30 --sweep
```

## Label file

One key per scorer, then one key per trial number, each with `[onset, offset]` bouts (inclusive, 0-based frames). An empty list means the trial was scored and has none of the behavior. A trial that isn't listed is treated as not scored and is skipped.

```json
{"rater1": {"101": [[120, 185], [940, 1002]], "102": []}}
```

Our Flee annotations are in `flee_sheet_bouts.json`; the Attack annotations are not in this repo.

## Lessons learned

- **Outlier correction can erase a mouse.** With the same body part chosen twice for the movement criterion (e.g. `nose_1` + `nose_1`), the cutoff is 0 px, so every movement counts as an outlier: one mouse ended up all 0 and the other frozen. Skip outlier correction or pick two different body parts, and check with `check_two_mice.py`.
- **Don't press save in SimBA's Label behavior tool** on trials labelled by script: unticked frames are saved as 0.
- **Pick the threshold and minimum bout length without looking at the held-out trials**, or the test score is optimistic.
- **Short behaviors need a short minimum bout.** 500 ms worked for Attack but would delete many Flee bouts; use ~100 ms.
- **`class_weights = balanced` does nothing after random undersampling at 1.0**: the classes are already 1:1.
