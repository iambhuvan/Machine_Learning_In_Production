import pandas as pd
import numpy as np
import yaml
from pathlib import Path
from sklearn.model_selection import train_test_split

with open('params.yaml', 'r') as f:
    params = yaml.safe_load(f)

test_split = params['preprocess']['test_split']
random_state = params['preprocess'].get('random_state', 42)

df = pd.read_csv('data/raw/data.csv')

X = df.drop('target', axis=1)
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=test_split, random_state=random_state, stratify=y
)

train_df = pd.concat([X_train, y_train], axis=1)
test_df = pd.concat([X_test, y_test], axis=1)

Path('data/processed').mkdir(parents=True, exist_ok=True)
train_df.to_csv('data/processed/train.csv', index=False)
test_df.to_csv('data/processed/test.csv', index=False)

print(f"Preprocessed data: train={len(train_df)}, test={len(test_df)}")

