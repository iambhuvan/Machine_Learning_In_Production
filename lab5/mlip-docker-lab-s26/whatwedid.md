# What We Did (Docker Lab Overview for Non-Docker Background)

This document explains, in plain terms, what Docker is, how it operates, and what we completed for Deliverables 1–3.

## What Docker Is (Quick, Clear Picture)
- **Docker is a way to package code + dependencies into a self-contained “container.”**
- A container is like a lightweight, isolated environment that runs the same way on any machine with Docker installed.
- You define how that environment is built using a **Dockerfile**.
- You can **share data** between containers and your host machine using **volumes**.

Key terms:
- **Image**: A blueprint of a container (built from a Dockerfile).
- **Container**: A running instance of an image.
- **Dockerfile**: Instructions to build the image.
- **Volume**: Storage that survives container deletion (can be Docker-managed or host-mounted).

---

## Deliverable 1: Training in a Container + Save Model to a Shared Volume

### What we completed
- Implemented model training in `docker/training/train.py`.
- The training code creates a `RandomForestClassifier`, trains it on the Wine dataset, and saves it to `/app/models/wine_model.pkl`.
- Set the Dockerfile `CMD` so the container runs the training script automatically.
- Built and ran the training container with a **named volume**.

### How Docker was operating here
- The training environment (Python + dependencies) was **built into an image** using `docker/training/Dockerfile`.
- When the container runs, it trains the model **inside the container**.
- The model file is written to `/app/models`, which is mapped to a **named Docker volume** called `wine_model_storage`.
- That named volume **persists even if the container is deleted**.

### Why this matters
You get a fully reproducible training run on any machine:
- Same Python version
- Same dependencies
- Same code
- Same output location

---

## Deliverable 2: Inference Container + Log Predictions to Host

### What we completed
- Implemented inference logic in `docker/inference/server.py`:
  - Load the model from `/app/models/wine_model.pkl`.
  - Accept JSON with 13 features under `"input"`.
  - Run prediction.
  - Log predictions to `/app/logs/predictions.log`.
- Created `docker/inference/Dockerfile` to containerize the Flask server.
- Created `docker/inference/requirements.txt`.
- Built and ran the inference container using:
  - The **same named volume** for the model.
  - A **bind mount** for logs (`./logs` on host → `/app/logs` in container).
  - Port mapping so we can access the API from the host.

### How Docker was operating here
- The inference server runs **inside its own container**.
- It **loads the model produced by training** through the shared named volume.
- It **writes logs** to a host-visible directory using a bind mount.

### What we verified
- `/health` showed the model was loaded.
- `/predict` returned a valid class.
- `./logs/predictions.log` appeared on the host, confirming bind mounts work.

---

## Deliverable 3: Volume Lifecycle (Model Exists vs Missing)

### What we completed
- Started inference with the existing named volume: `/health` showed the model was available.
- Deleted the named volume using Docker commands.
- Started inference again: `/health` showed **model not found**.

### How Docker was operating here
- Named volumes are **Docker-managed storage**.
- They persist across container restarts.
- They are **only removed when explicitly deleted**.

### Why this matters
This proves the difference between:
- **Named volume**: persists until deleted (used for the model).
- **Bind mount**: direct mapping to a host folder (used for logs).

---

## Summary in One Sentence
We used Docker to package training and inference into repeatable containers, shared the trained model via a named volume, exposed inference as a service, logged predictions to the host via a bind mount, and demonstrated how removing the named volume deletes the model.*** End Patch"}}
