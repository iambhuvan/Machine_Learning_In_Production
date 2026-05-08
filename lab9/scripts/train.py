import pandas as pd
import pickle
import yaml
from sklearn.ensemble import RandomForestClassifier
from pathlib import Path

with open('params.yaml', 'r') as f:
    params = yaml.safe_load(f)

n_estimators = params['train']['n_estimators']
max_depth = params['train']['max_depth']
random_state = params['train']['random_state']

df = pd.read_csv('data/processed/train.csv')

X_train = df.drop('target', axis=1)
y_train = df['target']

model = RandomForestClassifier(
    n_estimators=n_estimators,
    max_depth=max_depth,
    random_state=random_state
)

model.fit(X_train, y_train)

Path('models').mkdir(exist_ok=True)
with open('models/classifier.pkl', 'wb') as f:
    pickle.dump(model, f)

print(f"Trained model with n_estimators={n_estimators}, max_depth={max_depth}")
