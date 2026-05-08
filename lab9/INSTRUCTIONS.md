# Lab Instructions

> **Before starting**: Make sure you have completed the [Setup section in the README](README.md#setup) and can run the pipeline end-to-end.

---

## Part 1: DVC — Declarative Pipeline Management

In this part, you will use DVC to version your data, run the provided pipeline, and track experiments. The pipeline code and `dvc.yaml` are already provided — your focus is on understanding how DVC manages data, caching, and experiments.

### 1A: Initialize DVC and Track Data

**Initialize DVC** in your repository:

```bash
dvc init
git add .dvc .dvcignore
git commit -m "Initialize DVC"
```

**Configure a local remote** for storage:

```bash
dvc remote add -d local_storage /tmp/dvc-storage
git add .dvc/config
git commit -m "Configure DVC remote storage"
```

**Track the raw dataset** with DVC. Since the data file is currently tracked by Git, you need to remove it from Git first:

```bash
git rm -r --cached data/raw/data.csv
git commit -m "Stop tracking data.csv in Git"
dvc add data/raw/data.csv
git add data/raw/data.csv.dvc data/raw/.gitignore
git commit -m "Track raw dataset with DVC"
dvc push
```

Examine the `.dvc` file that was created. Notice it contains a hash of the file contents, not the data itself.

**Create a new data version** using the augmentation script:

```bash
python3 scripts/augment_data.py
dvc add data/raw/data.csv
git add data/raw/data.csv.dvc
git commit -m "Augmented dataset with synthetic samples"
dvc push
```

**Practice switching between versions**:

```bash
git log --oneline                    # find the commit before augmentation
git checkout <commit-hash> -- data/raw/data.csv.dvc
dvc checkout                         # restores the original data file
wc -l data/raw/data.csv             # verify row count changed

git checkout HEAD -- data/raw/data.csv.dvc
dvc checkout                         # back to augmented version
wc -l data/raw/data.csv             # verify row count
```

### 1B: Run the DVC Pipeline

The repo includes a `dvc.yaml` that defines three stages: preprocess, train, and evaluate. Take a look at it before running:

```bash
cat dvc.yaml
```

**Run the pipeline**:

```bash
dvc repro
```

**Visualize the dependency graph**:

```bash
dvc dag
```

You should see a three-stage DAG showing the flow from preprocess → train → evaluate.

**Test the caching**: change `n_estimators` in `params.yaml` (e.g., from 100 to 200), then:

```bash
dvc repro
```

Notice that `preprocess` is *not* re-run — only `train` and `evaluate` re-run, because DVC knows the preprocessing stage's dependencies haven't changed.

```bash
git add .
git commit -m "DVC pipeline with updated hyperparameters"
```

### 1C: Experiment Tracking

DVC can run and compare multiple experiments without manually editing files and committing each time.

**Run at least 2–3 experiments**, each with parameters **different from what is already in `params.yaml`**. Choose your own values — the point is to explore how DVC tracks each run:

```bash
dvc exp run -S train.n_estimators=<your-value> -S train.max_depth=<your-value>
dvc exp run -S train.n_estimators=<your-value> -S train.max_depth=<your-value>
dvc exp run -S train.n_estimators=<your-value> -S train.max_depth=<your-value>
```

**Compare results**:

```bash
dvc exp show
```

**Apply the best experiment** to your workspace:

```bash
dvc exp apply <best-experiment-name>
git add .
git commit -m "Apply best experiment"
```

**Push data/model artifacts**:

```bash
dvc push
```

---

## Part 2: Roar — Implicit Lineage Tracking

Now you will run the **same pipeline** using Roar. The key difference: you will not write any configuration file. Roar infers the pipeline by observing what your code actually reads and writes.

### 2A: Initialize and Run Roar

**Initialize Roar** in the same repository:

```bash
roar init
```

This creates a `.roar/` directory with a local SQLite database. No remote configuration, no YAML files. When prompted, let Roar add `.roar/` to your `.gitignore`.

**Run each pipeline step**, prefixed with `roar run`:

```bash
roar run python3 scripts/preprocess.py
roar run python3 scripts/train.py
roar run python3 scripts/evaluate.py
```

That is the entire setup. No `dvc.yaml` equivalent was needed.

> **Important**: Use `python3` (not `python`) in the `roar run` command. On macOS, `python` may not exist or may point to a SIP-protected binary, causing Roar's tracer to fail. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if you get errors here.

**Inspect the auto-inferred DAG**:

```bash
roar dag
```

Compare this DAG to your `dvc dag` output from Part 1. Roar inferred the dependencies by watching file I/O.

**Inspect a specific job**:

```bash
roar show @1
```

Notice it recorded the exact command, git commit, input/output files with content hashes, and runtime environment.

### 2B: Run Experiments with Roar

Just like you did with DVC, run 2–3 experiments with **different hyperparameters**. Edit `params.yaml` each time, then re-run the pipeline under Roar:

```bash
# Edit params.yaml with your chosen values, then:
roar run python3 scripts/train.py
roar run python3 scripts/evaluate.py
```

Repeat with different parameter values. After each run, inspect what Roar captured:

```bash
roar dag
roar show @latest
```

Think about: how does Roar track these different runs compared to `dvc exp show`? How would you compare results across runs?

### 2C: Make a Change and Trace the Impact

Now change the data itself and observe how the lineage updates.

**Augment the dataset and re-run**:

```bash
roar run python3 scripts/augment_data.py
roar run python3 scripts/preprocess.py
roar run python3 scripts/train.py
roar run python3 scripts/evaluate.py
```

**Inspect the updated DAG**:

```bash
roar dag
```

Notice how the DAG now reflects the current state. Roar keeps history but `roar dag` shows what is true *now*.

### 2D: Register and Browse Lineage on GLaaS

Roar can publish lineage to GLaaS (Global Lineage as a Service) so artifacts are globally identifiable by their content hash.

**Authenticate with GLaaS** (free, uses your GitHub account):

```bash
roar auth register
```

This prints your public key. Go to [glaas.ai](https://glaas.ai/), click "Sign in with GitHub," then paste your key under "SSH key" in your profile.

Test the connection:

```bash
roar auth test
```

**Register your model artifact**:

```bash
roar register models/classifier.pkl
```

**Browse the lineage** at [glaas.ai](https://glaas.ai/):

1. Search for your artifact hash
2. Click through: artifact → producing job → full DAG
3. See the complete trail: which data, which code, which commit produced this model

---

Now return to the [README](README.md#part-3-compare-and-reflect) for the reflection and discussion questions.
