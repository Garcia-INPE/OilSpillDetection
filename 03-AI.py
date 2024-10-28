from sklearn.ensemble import RandomForestClassifier
from matplotlib import pyplot as plt
from pprint import pprint
import xgboost as xgb
import importlib
import FunDiv as FunDiv
import FunPlot as FunPlot
import FunAI as FunAI

from Config import *

importlib.reload(FunDiv)
importlib.reload(FunPlot)
importlib.reload(FunAI)

X_train, y_train, X_test, y_test, features = FunAI.get_ds('stats.csv')

dict_res = {}
# ===============================================================
# RANDOM FOREST
# https://www.kaggle.com/code/wrecked22/basic-binary-classification-using-xgboost
# ===============================================================
title = "RF-Sklearn"
model = RandomForestClassifier()
dict_res[title] = FunAI.eval(model, X_train, y_train, X_test, y_test, title)
FunAI.plot_feat_imp_skl(model, title, features)
pprint(dict_res)

# ===============================================================
# XG Boost
# https://www.kaggle.com/code/wrecked22/basic-binary-classification-using-xgboost
# ===============================================================
title = "XGBoost"
model = xgb.XGBClassifier()
dict_res[title] = FunAI.eval(model, X_train, y_train, X_test, y_test, title)
FunAI.plot_feat_imp(model, title)
pprint(dict_res)

# ===============================================================
# RF from XG Boost
# https://xgboosting.com/random-forest-for-classification-with-xgboost/
# ===============================================================
title = "RF-XGBoost"
# Define XGBRFClassifier parameters
params = {
    'n_estimators': 100,
    'subsample': 0.8,
    'colsample_bynode': 0.8,
    'max_depth': 3,
    'random_state': 42
}
model = xgb.XGBRFClassifier(**params)
dict_res[title] = FunAI.eval(model, X_train, y_train, X_test, y_test, title)
FunAI.plot_feat_imp(model, title)
pprint(dict_res)
