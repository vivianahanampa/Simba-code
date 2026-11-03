# Recipe: new SimBA project `SDS_version3` (Attack, fixed)

**Goal:** rebuild the Attack classifier with the 3 fixes, and keep every other setting the same as `SDS_version2`. Then the before/after comparison only shows the effect of the fixes.

**The 3 fixes**
1. ❌→✅ **Skip outlier correction.** The old settings erased mouse 1 and froze mouse 2.
2. ❌→✅ **Labels for all 9 trials.** 778, 784 and 787 were all zeros before.
3. ❌→✅ **Real pixels-per-mm calibration.** The old config had `distance_mm = 0.0`.

All "old" values below come from `SDS_version2/project_folder/project_config.ini`. Button names are from the SimBA docs and can look slightly different in your version (5.4.4).

⏱️ **Time:** about 1.5–2 hours of clicking, plus training (15–75 min per run in your last log).

---

## 📋 Settings at a glance: old vs new

| What | Old (`SDS_version2`) | New (`SDS_version3`) | Why |
|---|---|---|---|
| Project file type | CSV | **CSV** | same |
| Number of animals | 2 | **2** | same |
| Type of tracking | Classic (`id_list = None`) | **Classic tracking** | same |
| Body-part config | user-defined, 22 body-parts | **same config** | same |
| Behaviors | 9 (list in step 2) | **same 9, same spelling** | same |
| Interpolation / smoothing | None (the imported file still had empty cells) | **None / None** | same |
| Calibration (`distance_mm`) | **0.0** ❌ | **real arena size in mm** | fix 3 |
| Outlier correction | run with `nose_1` + `nose_1`, movement 1.5, location 0.7 ❌ | **SKIP** | fix 1 |
| Labels | your labels for 6 trials; 778/784/787 = 0 ❌ | **your sheet labels, all 9 trials** | fix 2 |
| Held-out test trials | 2 (which ones? ask whoever trained it) | **the same 2** | fair test |
| Random forest settings | see step 10 | **identical** | same |
| Discrimination threshold | 0.4 | **0.4** | same |
| Minimum bout length | 33 ms (1 frame at 30 fps, so no filter) | **33 ms** | same |
| SimBA version | 5.4.4 | **5.4.4 (don't upgrade yet)** | same |

---

## 📁 Paths cheat sheet (Windows PC)

The old project lives at `C:\path\to\projects\SDS_version2\` (from `project_path` in its `project_config.ini`). SimBA keeps its own copy of everything it imports, so the old project's folders **are** your inputs: same videos, same tracking.

| What | Take it from (old, don't change) | Goes to (new) |
|---|---|---|
| Project folder | `C:\path\to\projects\SDS_version2\project_folder\` | `C:\path\to\projects\SDS_version3\project_folder\` |
| Videos (step 4) | `...\SDS_version2\project_folder\videos\` | `...\SDS_version3\project_folder\videos\` |
| Tracking CSVs (step 5) | `...\SDS_version2\project_folder\csv\input_csv\` | `...\SDS_version3\project_folder\csv\input_csv\` |
| Video parameters (step 6) | `...\SDS_version2\project_folder\logs\video_info.csv` (to compare) | `...\SDS_version3\project_folder\logs\video_info.csv` |
| Body-part list (step 2) | `...\SDS_version2\project_folder\logs\measures\pose_configs\bp_names\project_bp_names.csv` | `...\SDS_version3\project_folder\logs\measures\pose_configs\bp_names\project_bp_names.csv` |
| Features (step 8) | | `...\SDS_version3\project_folder\csv\features_extracted\` |
| Training labels (step 9) | | `...\SDS_version3\project_folder\csv\targets_inserted\` |
| Held-out labels (step 9) | | `...\SDS_version3\project_folder\csv\heldout_test_annotations\` |
| Old model (for reference) | `...\SDS_version2\models\generated_models\Attack.sav` (`model_path_1` in the old ini) | new model: step 10 |
| Predictions (step 11) | old: `...\SDS_version2\project_folder\csv\machine_results\` | `...\SDS_version3\project_folder\csv\machine_results\` |
| My tools (unzipped) | | `C:\Users\<you>\Desktop\simba_tools\` |
| This session's log | | `C:\Users\<you>\Desktop\simba_version3_log.txt` |

`...` = `C:\path\to\projects`

**Before you start, open the old folders in File Explorer and check:**
- [ ] `SDS_version2\project_folder\videos\` has **9 videos**: `Trial 776`, `Trial 778`, `Trial 780`, `Trial 782`, `Trial 784`, `Trial 786`, `Trial 787`, `Trial 791`, `Trial  1106` (two spaces).
- [ ] `SDS_version2\project_folder\csv\input_csv\` has **9 CSVs** with the **same names**. These are the DeepLabCut files SimBA imported. I checked `Trial 776.csv`: both mice are there.
- [ ] Are the videos **real files or shortcuts**? If they're tiny (a few KB) or show an arrow icon, they're shortcuts (SimBA "symlinks"). Right-click one → **Properties** → **Target** shows the original folder; import from that original folder instead.

---

## 🧺 Ingredients (have these ready)

- [ ] The Windows computer with the `simba` conda environment (the one in your log)
- [ ] The **9 videos**: already in `SDS_version2\project_folder\videos\` (see the paths cheat sheet)
- [ ] The **9 DeepLabCut CSV files**: already in `SDS_version2\project_folder\csv\input_csv\` (from your DeepLabCut model)
- [ ] The **real width of the arena in mm**, measured with a ruler, or from the cage spec
- [ ] **`simba_tools`** (this repo; on GitHub: **Code → Download ZIP**): unzip it onto the Windows PC's **Desktop**, so you get `Desktop\simba_tools`. It contains:
  - `check_two_mice.py`: checks both mice are there and moving
  - `make_targets_inserted.py`: writes your labels into SimBA's files
  - `attack_sheet_bouts.json`: your Attack bouts from the scoring sheet (not in the public repo; same format as `example_bouts.json`)
  - `evaluate_simba_test_videos.py`: scores the held-out trials
  - this recipe
- [ ] **Which 2 trials are held out** (ask whoever trained the old model which ones it never saw). Write them here: `____` and `____`

⚠️ **Don't open or change `SDS_version2`.** It's your "before".

---

## Step 1: Start SimBA and record a log this time

Open **PowerShell** and type:

```powershell
conda activate simba
simba 2>&1 | Tee-Object -FilePath "$env:USERPROFILE\Desktop\simba_version3_log.txt"
```

✅ After ~4 minutes the SimBA window opens. Everything SimBA prints is also saved to `Desktop\simba_version3_log.txt`.

❌ If you get the red `conda-hook.ps1` error first, ignore it. It showed up last time too, and `conda activate` still worked.

---

## Step 2: Create the project

**File → Create a new project**

| Field | Type / choose | Old value |
|---|---|---|
| Project directory | `C:\path\to\projects` | same folder as `SDS_version2` |
| Project name | `SDS_version3` | `SDS_version2` |
| Workflow file type | `CSV` | csv |
| SML settings (behaviors) | add **9 rows**, spelled exactly: `Attack`, `Flee`, `FightBack`, `Investigate(A)`, `Freeze`, `Investigate(D)`, `Vigilance`, `Inattentive`, `Submit` | same 9 |
| Type of tracking | `Classic tracking` | Classic |
| `# config` | your **user-defined** 2-animal, 22-body-part config (same one as `SDS_version2`) | user_defined |

Click **Generate Project Config** (also labelled `CREATE PROJECT CONFIG` in some versions).

✅ **Check:**
- [ ] The folder `...\projects\SDS_version3\project_folder\` exists, with `project_config.ini` inside.
- [ ] Open `project_folder\logs\measures\pose_configs\bp_names\project_bp_names.csv` in Notepad. It has **22 lines in this order** (same as the old project):

```
nose_1, right_ear_1, left_ear_1, right_shoulder_1, left_shoulder_1, body_center_1,
right_hip_1, left_hip_1, tail_base_1, tail_middle_1, tail_end_1,
nose_2, right_ear_2, ... tail_end_2   (same 11 again with _2)
```

❌ If your config isn't in the `# config` list (for example on another computer), click the button next to `# config` → **Create pose config**: name with no spaces, **2 animals**, **22 body-parts**. Enter the 22 names in the order above, with Animal ID `1` for the first 11 and `2` for the last 11.

---

## Step 3: Load the project

**File → Load project** → pick `SDS_version3\project_folder\project_config.ini`.

✅ The project tabs open. Do this every time you reopen SimBA.

---

## Step 4: Import the videos

**Import videos tab → Import multiple videos**

| Field | Value |
|---|---|
| Folder | `C:\path\to\projects\SDS_version2\project_folder\videos` |
| Video format | the extension the files in that folder have (look in File Explorer, e.g. `mp4`) |

Click **Import MULTIPLE videos**. SimBA copies them into `SDS_version3\project_folder\videos\`; the old folder isn't changed.

✅ **Check:** `project_folder\videos\` has **9 videos** with the same names as before.

---

## Step 5: Import the tracking (DeepLabCut CSVs)

**Import tracking data tab**

| Field | Value | Old |
|---|---|---|
| File type | `CSV (DLC/DeepPoseKit)` | same |
| Interpolation | `None` | None |
| Smoothing | `None` | None |
| Folder Select → Browse Folder | `C:\path\to\projects\SDS_version2\project_folder\csv\input_csv` | |

Click **Import csv to project folder**.

The old `input_csv` files are in DeepLabCut's format (3 header rows: `scorer`, `bodyparts`, `coords`), with no interpolation applied, so they import like the original DLC files. If SimBA refuses them, use the original DeepLabCut output CSVs instead (ask whoever ran DeepLabCut where it saved them).

✅ **Check:**
- [ ] `project_folder\csv\input_csv\` has **9 files**, each named exactly like its video.
- [ ] Open `Trial 776.csv` in Notepad. Line 2 starts `bodyparts,nose,nose,nose,right_ear,…`, and line 4 (frame 0) starts with real numbers: `0,339.11…,363.06…,0.998…`. That's mouse 1's nose, and it's there.

❌ If a file name has the long DLC suffix (`Trial 776DLC_Resnet50…`), rename it to match the video name.

---

## Step 6: Video parameters (fix 3: calibration)

**Video parameters tab**

1. **KNOWN DISTANCE (MILLIMETERS):** type the arena width in mm → **AUTO-POPULATE**.
2. **CONFIGURE VIDEO PARAMETERS** opens a table with one row per video:
   - **fps** must be **30** for every video.
   - For the first video, click **CALCULATE DISTANCE**, double-click the two ends of the arena, then press **Esc**.
   - If the camera didn't move between recordings, use **DUPLICATE INDEX 1** for the rest.
3. Click **SAVE PIXEL PER MILLIMETER DATA**.

✅ **Check:** open `SDS_version3\project_folder\logs\video_info.csv`. There are 9 rows, `fps = 30`, and the pixels/mm column is a real number (not 0, not blank).

🔎 **Compare** with the old `SDS_version2\project_folder\logs\video_info.csv`. If the old pixels/mm were real numbers, the calibration was fine after all (`distance_mm = 0.0` was just an empty box), and your new values should be close to the old ones. If the old values were 0, 1 or blank, the old features in mm were wrong. Note it for the comparison.

---

## Step 7: Outlier correction (fix 1: SKIP)

**Outlier correction tab → `SKIP OUTLIER CORRECTION (CAUTION)`**

⚠️ **Don't** click **Settings** or **Run outlier correction**. That's what erased the mice.

✅ **Check (the most important check of the whole recipe).** In a **new** PowerShell window:

```powershell
conda activate simba
cd "$env:USERPROFILE\Desktop\simba_tools"
python check_two_mice.py "C:\path\to\projects\SDS_version3\project_folder\csv\outlier_corrected_movement_location"
```

What you want to see for **every** trial, for **both** animals:

| Column | ✅ Good | ❌ Bad (what the old project had) |
|---|---|---|
| `tracked` | roughly 80–95% | `0%` (mouse erased) |
| `moves` | close to `100%` | close to `0%` (mouse frozen) |
| `x` / `y` | wide ranges like `240-540` | `0-0` |

If **784** or **1106** still show 0% for both mice, their DeepLabCut file itself has no tracking. Leave that trial out of training (step 9) and tell me.

---

## Step 8: Extract features

**Extract features tab → EXTRACT FEATURES** (leave "user-defined feature extraction script" **off**).

✅ **Check:**
- [ ] `project_folder\csv\features_extracted\` has **9 files**.
- [ ] Optional: run the checker again on that folder. You should get the same good numbers as step 7.

---

## Step 9: Insert the labels (fix 2), with a script instead of the Label tool

Your labels are already in the scoring sheet, so a script writes them in. It adds your Attack bouts to each feature file and sends the 2 held-out trials to a separate folder so they're never trained on.

```powershell
conda activate simba
cd "$env:USERPROFILE\Desktop\simba_tools"
python make_targets_inserted.py --config "C:\path\to\projects\SDS_version3\project_folder\project_config.ini" --labels attack_sheet_bouts.json --scorer rater1 --holdout 780 787
```

➡️ Replace `780 787` with **your 2 held-out trials** from the ingredients list.

✅ **Check:** it prints one line per trial. The Attack frames must match this table (from your sheet):

| Trial | 776 | 778 | 780 | 782 | 784 | 786 | 787 | 791 | 1106 |
|---|---|---|---|---|---|---|---|---|---|
| Attack frames | 2718 | 1458 | 838 | 64 | 875 | 0 | 1251 | 1751 | 454 |

- [ ] `csv\targets_inserted\` has **7 files** (training).
- [ ] `csv\heldout_test_annotations\` has **2 files** (test).

⚠️ Only **Attack** is filled in; the other 8 behavior columns are all 0. Don't train Flee or the others with these files until they're labelled.

⚠️ Don't open these trials in **Label behavior** and press save. In standard mode SimBA treats every unticked frame as "no behavior", so saving can wipe labels. That may be how 778/784/787 ended up all zeros.

---

## Step 10: Train the model (same settings as before)

**Train machine model tab → SETTINGS.** Enter exactly these values (from the old `[create ensemble settings]`):

| Setting in SimBA | Value | ini key (old) |
|---|---|---|
| Machine model algorithm | `RF` | `model_to_run = RF` |
| Behavior | `Attack` | `classifier = Attack` |
| Random forest estimators | `2000` | `rf_n_estimators` |
| Max features | `sqrt` | `rf_max_features` |
| Criterion | `gini` | `rf_criterion` |
| Test size | `0.2` | `train_test_size` |
| Train-test split type | `BOUTS` | `train_test_split_type` |
| Minimum sample leaf | `1` | `rf_min_sample_leaf` |
| Under-sample setting | `random undersample` | `under_sample_setting` |
| Under-sample ratio | `1.0` | `under_sample_ratio` |
| Over-sample setting | `None` | `over_sample_setting` |
| Class weights | `balanced` | `class_weights` |

Evaluation options:

| Option | On/off | ini key (old) |
|---|---|---|
| Create model meta data file | ✅ on | `rf_meta_data = True` |
| Example decision tree / fancy tree | ⬜ off | `generate_example_decision_tree*` |
| Feature importance log | ✅ on | `generate_features_importance_log` |
| Feature importance bar graph, **20** bars | ✅ on | `generate_features_importance_bar_graph`, `n_feature_importance_bars` |
| Feature permutation importance | ⬜ off | `compute_feature_permutation_importance` |
| Learning curves, **5** k-splits, **5** data splits | ✅ on | `generate_sklearn_learning_curves`, `learning_curve_*` |
| Precision-recall curves | ✅ on | `generate_precision_recall_curves` |
| Classification report | ✅ on | `generate_classification_report` |
| SHAP scores | ⬜ off | `generate_shap_scores` |
| Partial dependency | ⬜ off | `partial_dependency` |

Then: **SAVE SETTINGS (GLOBAL ENVIRONMENT)** → **TRAIN SINGLE MODEL (GLOBAL ENVIRONMENT)**.

⏱️ 15–75 min. The terminal fills with `[Parallel(n_jobs=-1)] Done … out of 2000` lines. That's normal.

✅ **Check:**
- [ ] `Attack.sav` exists in `SDS_version3\project_folder\models\generated_models\`. In the old project it ended up in `SDS_version2\models\generated_models\` (outside `project_folder`). If you can't find it, search File Explorer under `SDS_version3` for `Attack.sav`, and use that path in step 11.
- [ ] The `model_evaluations` folder next to it has the classification report, PR curve, learning curve and feature-importance graph.
- [ ] 👀 Look at the feature-importance bar graph. With both mice tracked, features about **distance between the two mice** should now appear near the top.

⚠️ Avoid the **add/remove classifier** pop-up. It crashed in your last log (`'TwoOptionQuestionPopUp' object has no attribute 'selected_option'`).

---

## Step 11: Run the model

**Run machine model tab → RUN MODELS**

| Field | Value | Old |
|---|---|---|
| Model path (Attack) | the **new** `Attack.sav` from step 10 (inside `SDS_version3`, **not** `SDS_version2`) | old: `...\SDS_version2\models\generated_models\Attack.sav` |
| Discrimination threshold | `0.4` | `threshold_1 = 0.4` |
| Minimum bout length (ms) | `33` | `min_bout_1 = 33` |

Click **RUN**.

✅ **Check:** `csv\machine_results\` has **9 files** (SimBA runs on every feature file, including the held-out ones). Each has a `Probability_Attack` and an `Attack` column.

---

## Step 12: Score the 2 held-out trials

```powershell
conda activate simba
cd "$env:USERPROFILE\Desktop\simba_tools"
python evaluate_simba_test_videos.py --project "C:\path\to\projects\SDS_version3\project_folder" --annotations "C:\path\to\projects\SDS_version3\project_folder\csv\heldout_test_annotations" --classifier Attack --fps 30 --sweep
```

✅ It prints precision, recall and F1 for each held-out trial, plus the total attack time (human vs SimBA). This is the **honest** score, because the model never saw these trials. For reference, our two human raters agreed at **F1 ≈ 0.91**.

---

## Step 13: Send me these for the before/after comparison

- [ ] `Desktop\simba_version3_log.txt`
- [ ] `project_folder\project_config.ini`
- [ ] `project_folder\logs\video_info.csv`
- [ ] The checker output from step 7 (copy and paste is fine)
- [ ] `project_folder\csv\machine_results\` (all 9)
- [ ] `project_folder\models\generated_models\model_evaluations\`
- [ ] The step 12 output


---

## 🆘 If something goes wrong

| Problem | Fix |
|---|---|
| `simba: command not found` | run `conda activate simba` first |
| Your config isn't in `# config` | recreate it (step 2, ❌ box) with the exact 22-name order |
| Import says the number of columns/body-parts doesn't match | the config isn't the 22-body-part one, or the CSV is from a different DLC model |
| A video and its tracking file don't pair | the names differ; rename so they match exactly (except the extension) |
| Checker shows `moves` ~0% after step 7 | outlier correction ran instead of being skipped. Delete `csv\outlier_corrected_movement_location\*` and redo step 7 |
| Script says `[skip] … no <scorer> labels` | that trial isn't in `attack_sheet_bouts.json`; tell me and I'll add it |
| Training is very slow | normal: 2000 trees. Don't close the PowerShell window |

---

## Later: adding your 2 new Attack trials (round 2)

Do this **after** you have the before/after result, so each change is measured separately:

1. Add the 2 new trials' bouts to the scoring sheet, and I'll add them to `attack_sheet_bouts.json`.
2. In `SDS_version3`, import the 2 videos and tracking (steps 4–5), set their video parameters (step 6), skip outlier correction (step 7), extract features (step 8).
3. Re-run step 9 (it rebuilds all files), retrain (step 10), run (step 11), score (step 12).
