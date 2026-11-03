# Recipe: add Flee to `SDS_version4` (same project)

**Don't start a new project.** Steps 1–8 of `SimBA_new_project_recipe.md` (import, tracking, skip outlier correction, features) don't depend on the behavior, and `SDS_version4` already has them done. Flee is already behavior #2 in its config. You only redo the end: **labels → train → run → score**.

```
recipe step:   1  2  3  4  5  6  7  8 | 9  10  11  12
               ✅ done for SDS_version4 | 🔁 redo for Flee
```

## 🧺 Ingredients

| What | Where |
|---|---|
| Flee bouts from the sheet's **Flee** tab (two raters) | `flee_sheet_bouts.json` (not in the public repo; format: `example_bouts.json`) |
| Labels script (**new version**, keeps Attack) | `make_targets_inserted.py` (replace the old one) |
| Evaluation script (same as before) | `evaluate_simba_test_videos.py` |

📁 Put all 3 in `C:\path\to\simba-checks\simba_tools\`.

⚠️ **Use the new `make_targets_inserted.py`.** The old one sets every other behavior to 0, so running it for Flee would **erase your Attack labels**.

---

## Step A: Back up the Attack labels (1 min)

In File Explorer, copy the folder
`C:\path\to\projects\SDS_version4\project_folder\csv\targets_inserted`
and paste it next to itself, renamed **`targets_inserted_BACKUP_attack`**.

---

## Step B: Insert the Flee labels

```powershell
conda activate simba
cd "C:\path\to\simba-checks"
python simba_tools/make_targets_inserted.py --config "C:\path\to\projects\SDS_version4\project_folder\project_config.ini" --labels simba_tools/flee_sheet_bouts.json --scorer rater1 --behavior Flee --holdout 778 784 787
```

➡️ Keep `--holdout 778 784 787`, the **same** test trials as Attack. Held-out trials are shared by every behavior in a project.

✅ **Check:** each line ends with `(kept Attack)`, and the Flee frames match:

| Trial | 1106 | 776 | 780 | 782 | 791 | 778 (test) | 787 (test) |
|---|---|---|---|---|---|---|---|
| Flee frames | 701 | 510 | 125 | 9 | 168 | 476 | 111 |

(These count both the first and the last frame, so they're slightly higher than the sheet's Frames column.)

✅ It ends with a **WARNING about 786**. That's expected, see step C.

- [ ] `csv\heldout_Flee\` has **2 files** (778, 787). You'll use it in step F.

---

## Step C: Take 786 out while training Flee

786 is in `targets_inserted` (it's an Attack training trial) but **nobody scored Flee in it**. Left there, SimBA would learn "no Flee" from all 2,946 frames.

1. Make a folder `csv\not_scored_Flee\`.
2. Move `Trial 786…csv` from `csv\targets_inserted\` into it.
3. ↩️ **Move it back** before you retrain Attack.

(If the rater confirms 786 has no flee at all, add `"786": []` to the JSON and skip this step.)

✅ `csv\targets_inserted\` now has **5 files**: 776, 780, 782, 791, 1106.

---

## Step D: Train the Flee model

**Train machine model tab → SETTINGS**: same as Attack (recipe step 10), but change **one** thing:

| Setting | Value |
|---|---|
| **Behavior** | **`Flee`** |
| everything else | same as Attack: RF, 2000, sqrt, gini, 0.2, BOUTS, leaf 1, random undersample 1.0, class weights balanced |
| SHAP | ⬜ off for now |

**SAVE SETTINGS (GLOBAL ENVIRONMENT)** → **TRAIN SINGLE MODEL (GLOBAL ENVIRONMENT)**.

✅ **Check:** `SDS_version4\models\generated_models\` now has **`Flee.sav`** next to `Attack.sav`.

---

## Step E: Run the models

**Run machine model tab → RUN MODELS**

| Behavior | Model path | Threshold | Min bout (ms) |
|---|---|---|---|
| Attack | `...\generated_models\Attack.sav` | `0.6` | `500` |
| **Flee** | `...\generated_models\Flee.sav` | **`0.5`** | **`100`** |

⚠️ **Don't use 500 ms for Flee.** Flee bouts are short: 40% of ours were ≤ 0.5 s, and a 500 ms minimum would delete them. 100 ms (3 frames) is just below our shortest bouts (0.17 s).

✅ `csv\machine_results\` files now have `Probability_Flee` and `Flee` columns.

---

## Step F: Score the held-out trials for Flee

```powershell
python simba_tools/evaluate_simba_test_videos.py --project "C:\path\to\projects\SDS_version4\project_folder" --annotations "C:\path\to\projects\SDS_version4\project_folder\csv\heldout_Flee" --classifier Flee --fps 30 --sweep
```

⚠️ Use **`heldout_Flee`**, not `heldout_test_annotations`: 784 is in the shared folder with no Flee labels.

📏 **The bar to beat:** how well two human raters agree on the same trial (ours: **F1 0.80** for Flee, 0.91 for Attack).

📋 Paste the output into your diary; I'll make the graphs.

---

## 🔁 Afterwards

- ↩️ Move `Trial 786…csv` back into `targets_inserted`.
- Want the rater's uncertain (**"?"**) bouts counted as flee? Put them under a second scorer key (we used `rater1_with_unsure`), re-run step B with that `--scorer`, then D–F.
