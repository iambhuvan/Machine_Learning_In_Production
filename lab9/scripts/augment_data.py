"""
Augment the dataset by adding synthetic samples.
This script adds 10 new rows with random values within the feature ranges.
"""
import pandas as pd
import numpy as np

df = pd.read_csv('data/raw/data.csv')
original_size = len(df)

np.random.seed(42)
new_rows = []
for _ in range(10):
    row = {}
    for col in df.columns:
        if col == 'target':
            # Binary classification: 0 (malignant) or 1 (benign)
            row[col] = np.random.randint(0, 2)
        else:
            # Generate random values within the observed feature range
            row[col] = np.random.uniform(df[col].min(), df[col].max())
    new_rows.append(row)

new_df = pd.DataFrame(new_rows)
df = pd.concat([df, new_df], ignore_index=True)

df.to_csv('data/raw/data.csv', index=False)
print(f"Augmented dataset from {original_size} to {len(df)} samples")

