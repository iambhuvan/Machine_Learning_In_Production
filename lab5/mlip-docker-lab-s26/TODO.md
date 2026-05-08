# Lab 5 To-Do List (mlip-docker-lab-s26)

## Code + Docker TODOs
- `docker/training/train.py`: implement `RandomForestClassifier`, fit, and save model with `joblib.dump` to `/app/models/wine_model.pkl`.
- `docker/training/Dockerfile`: set `CMD` to run the training script.
- `docker/inference/server.py`: load model from `/app/models/wine_model.pkl`, parse JSON `input`, run prediction, and append logs to `/app/logs/predictions.log`.
- Create `docker/inference/Dockerfile` (python:3.11-slim, install deps, copy `server.py`, expose 8081, run server).
- Create `docker/inference/requirements.txt` (Flask, scikit-learn, joblib, numpy).
- `docker-compose.yml`: fill in build dockerfile paths, volumes (named + bind), ports, and the named volume definition.

## Run + Verify
- Build + run training container with named volume `wine_model_storage`.
- Build + run inference container with named volume + bind mount `./logs`.
- Test `GET /health` and `POST /predict`, confirm `./logs/predictions.log` is written.
- Run `docker compose up --build`, then verify endpoints and logs.
- Validate volume behavior (persisted model after `docker compose down`, removed after `docker compose down -v`).

## Deliverables Prep
- Be ready to explain:
  - Why Docker improves ML reproducibility/portability.
  - What a Dockerfile does for the inference service.
  - Named volumes vs bind mounts, and how removing volumes affects model availability.
