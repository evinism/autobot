import pickle

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import os

# -- EVERY CLASSIFIER --
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.gaussian_process.kernels import RBF
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, AdaBoostClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.discriminant_analysis import QuadraticDiscriminantAnalysis
from sklearn.preprocessing import OrdinalEncoder
from sklearn.compose import ColumnTransformer
# -- EVERY CLASSIFIER --

def encode_df(df):
    passthroughs = df.select_dtypes(include=['float64', 'int64']).apply(lambda x: x.fillna(x.mean()))
    passthroughs['san'] = df['san'].fillna('P')
    return passthroughs



def build_model(player, depth):
    with open(f"data/dfs/{player}/depth-{depth}.pickle", "rb") as f:
        df = pickle.load(f)

    # For testing
    #df = df[['label', 'cp_loss']]

    df = encode_df(df)
    X = df.drop(columns=['label'])
    y = df['label']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    pipeline = Pipeline([
        ("transform", ColumnTransformer(
            transformers=[
                ("san", OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1), ["san"]),
            ],
            remainder="passthrough"
        )),
        ("imputer", SimpleImputer(strategy="median", add_indicator=1)),
        ("scaler", StandardScaler()),
        #("classifier", LogisticRegression()),
        #("classifier", DecisionTreeClassifier())
        ("classifier", RandomForestClassifier(n_estimators=100, max_depth=16, verbose=True, n_jobs=12))
        #("classifier", SVC(gamma="auto", probability=True))
        #("classifier", GaussianProcessClassifier())
    ])

    pipeline.fit(X_train, y_train)
    pipeline.predict_proba(X_train)

    # Evaluate model via ROC AUC 
    # Training:
    y_pred_train = pipeline.predict_proba(X_train)
    y_pred_train = y_pred_train[:, 1]
    print(f"Training ROC AUC: {roc_auc_score(y_train, y_pred_train)}")

    # Testing:
    y_pred_test = pipeline.predict_proba(X_test)
    y_pred_test = y_pred_test[:, 1]
    print(f"Testing ROC AUC: {roc_auc_score(y_test, y_pred_test)}")



    # Save model
    if not os.path.exists(f"data/models/{player}"):
        os.makedirs(f"data/models/{player}")
    with open(f"data/models/{player}/depth-{depth}.pickle", 'wb') as f:
        pickle.dump(pipeline, f)
    print(f"Saved model to {player}/depth-{depth}.pickle")

    return pipeline


if __name__ == "__main__":
    player = input("Enter player name: ")
    depth = input("Enter depth: ")
    model = build_model(player, depth)