import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression

def data_preparation(df: pd.DataFrame):
    """
    Select target column and one categorical feature, and one-hot encode it.
    Returns (feature_df, target_series).
    """
    target = "price"
    features = ["furnishingstatus"]

    feature_df = pd.get_dummies(
        df.loc[:, features],
        columns=["furnishingstatus"]
    )
    target_series = df.loc[:, target]
    return feature_df, target_series

def data_split(features: pd.DataFrame, target: pd.Series):
    """
    Deterministic split with random_state for reproducibility.
    Returns X_train, X_test, y_train, y_test.
    """
    X_train, X_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.33,
        random_state=42
    )
    return X_train, X_test, y_train, y_test

def train_model(X_train: np.ndarray, y_train: np.ndarray):
    """Train a simple Linear Regression model."""
    reg = LinearRegression().fit(X_train, y_train)
    return reg

def eval_model(X_test: np.ndarray, y_test: np.ndarray, model: LinearRegression):
    """Return R^2 score on the test set."""
    return model.score(X_test, y_test)

if __name__ == "__main__":
    df_raw = pd.read_csv("Housing.csv")
    feature_df, target_series = data_preparation(df_raw)
    X_train, X_test, y_train, y_test = data_split(feature_df, target_series)
    reg = train_model(X_train, y_train)
    eval_score = eval_model(X_test, y_test, reg)
    print(f"Trained model score is: {eval_score}")
