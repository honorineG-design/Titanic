"""
Titanic Survey — Model Training Script
Run this ONCE before starting the backend.
1. Download train.csv from https://www.kaggle.com/c/titanic/data
2. Place train.csv in this folder (training/)
3. Run: python train_model.py
Output: ../backend/models/titanic_model.pkl + sex_encoder.pkl
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import cross_val_score
import joblib
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH  = os.path.join(SCRIPT_DIR, 'train.csv')
MODEL_DIR  = os.path.join(SCRIPT_DIR, '..', 'backend', 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

print(' Loading dataset...')
df = pd.read_csv(DATA_PATH)
print(f'   {df.shape[0]} passengers loaded')

df = df[['Survived', 'Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked']].copy()
df['Age'].fillna(df['Age'].median(), inplace=True)
df['Fare'].fillna(df['Fare'].median(), inplace=True)
df['Embarked'].fillna('S', inplace=True)

sex_encoder      = LabelEncoder()
df['Sex']        = sex_encoder.fit_transform(df['Sex'])   
df['Embarked']   = df['Embarked'].map({'S': 0, 'C': 1, 'Q': 2})

print('Training model...')
features = ['Pclass', 'Sex', 'Age', 'SibSp', 'Parch', 'Fare', 'Embarked']
X, y     = df[features], df['Survived']

model = LogisticRegression(max_iter=1000, random_state=42)
model.fit(X, y)

scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
print(f'   Accuracy: {scores.mean():.1%} ± {scores.std():.1%}')

joblib.dump(model,       os.path.join(MODEL_DIR, 'titanic_model.pkl'))
joblib.dump(sex_encoder, os.path.join(MODEL_DIR, 'sex_encoder.pkl'))
print(f'Saved to {os.path.abspath(MODEL_DIR)}')
print(' You can now run: cd backend && python app.py')