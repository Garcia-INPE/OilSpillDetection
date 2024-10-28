from sklearn import metrics
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, confusion_matrix, classification_report
from matplotlib import pyplot as plt
import xgboost as xgb
import itertools
import pandas as pd
import seaborn as sns

import importlib
import FunDiv as FunDiv
import FunPlot as FunPlot

from Config import *

importlib.reload(FunDiv)
importlib.reload(FunPlot)

dir_res = "./results"


def eval(model, X_train, y_train, X_test, y_test, title):
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    acc = metrics.accuracy_score(y_test, y_pred)

    multiplot(y_train, y_test, y_pred, title, acc)
    # plot_confusion_matrix(
    #    (tn, fp, fn, tp), classes=range(2), title=f"{title} - Acc:{acc*100:0.2f}%", save=True)
    return (float(acc))


def get_ds(fname_csv="stats.csv"):
    pd.set_option("display.max_columns", 80)

    # 1632 rows
    DS_all = pd.read_csv(fname_csv, sep=";")
    DS_all.columns

    # List of the features to do AI
    features = ['MONTH', 'SHP_AREA_KM2', 'SHP_PERIM_KM',
                'SHP_COMPLEX_MEAS', 'SHP_SPREAD', 'SHP_FACT', 'SHP_CIRCUL',
                'SHP_PER_AREA_RATIO', 'SHP_HU_MOM1', 'SHP_HU_MOM2', 'SHP_HU_MOM3',
                'SHP_HU_MOM4', 'SHP_HU_MOM5', 'SHP_HU_MOM6', 'SHP_HU_MOM7', 'IN_STD',
                'IN_VAR', 'IN_MIN', 'IN_MAX', 'IN_MEAN', 'IN_MEDIAN', 'IN_VAR_COEF',
                'OUT_STD', 'OUT_VAR', 'OUT_MIN', 'OUT_MAX', 'OUT_MEAN', 'OUT_MEDIAN',
                'OUT_VAR_COEF', 'TEXT_CONTR_GLCM', 'TEXT_HOMOG_GLCM', 'TEXT_ENTRO_GLCM',
                'TEXT_CORREL_GLCM', 'TEXT_DISSIM_GLCM', 'TEXT_VAR_GLCM',
                'TEXT_ENERGY_GLCM', 'TEXT_MEAN_GLCM', 'SLICK_DARKNESS', 'CLASSE']
    DS = DS_all[features].copy()
    DS.dropna(how='any', axis=0, inplace=True)  # 1589 rows now! (1633)
    DS.reset_index(inplace=True)
    # 1 = OIL SPILL, 0 = SEEPAGE SLICK
    DS["CLASSE"] = [0 if x == "SEEPAGE SLICK" else 1 for x in DS["CLASSE"]]
    DS.groupby("CLASSE")["CLASSE"].count()
    # OIL SPILL        1221 (1)
    # SEEPAGE SLICK     367 (0)

    # read data
    X_train, X_test, y_train, y_test = train_test_split(
        DS[features[:-1]], DS['CLASSE'], test_size=.2)
    return (X_train, y_train, X_test, y_test, features[:-1])


def multiplot(y_train, y_test, y_pred, title, acc):
    plot_conf_matrix2(y_test, y_pred, title, acc)
    plot_balance(y_train, y_test, title)
    report = classification_report(y_test, y_pred)
    print(f"Classification Report:\n{report}")
    return


def plot_feat_imp(model, title):
    # https://stackoverflow.com/questions/37627923/how-to-get-feature-importance-in-xgboost
    feature_important = model.get_booster().get_score(importance_type='weight')
    keys = list(feature_important.keys())
    values = list(feature_important.values())
    data = pd.DataFrame(data=values, index=keys, columns=[
                        "score"]).sort_values(by="score", ascending=False)
    data.nlargest(10, columns="score").plot(
        kind='barh', figsize=(20, 10))  # plot top 40 features
    plt.savefig(f"{dir_res}/{title}_FeatImport_v1.png")
    plt.close()

    xgb.plot_importance(model)
    plt.savefig(f"{dir_res}/{title}_FeatImport_v2.png")
    # plt.show()
    plt.close()
    return


def plot_feat_imp_skl(model, title, features):
    # https://scikit-learn.org/stable/auto_examples/ensemble/plot_forest_importances.html
    importances = model.feature_importances_
    std = np.std(
        [tree.feature_importances_ for tree in model.estimators_], axis=0)
    forest_importances = pd.Series(
        importances, index=features).sort_values(ascending=False)

    fig, ax = plt.subplots()
    forest_importances.plot.bar(yerr=std, ax=ax)
    ax.set_title("Feature importances")  # using MDI")
    ax.set_ylabel("Mean decrease in impurity")
    fig.tight_layout()
    plt.savefig(f"{dir_res}/{title}_FeatImport_skl.png")
    # plt.show()
    plt.close()


def plot_conf_matrix2(y_test, y_pred, title, acc):
    # Conf Matrix (Contingency Table) from sklearn is weird, repositioning the elements
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    conf_matrix = [[tp, fp], [fn, tn]]

    _, ax = plt.subplots(figsize=(4, 4))
    sns.heatmap(conf_matrix, annot=True, fmt='g', cmap='coolwarm',
                xticklabels=['1', '0'], yticklabels=['1', '0'], ax=ax)
    plt.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    ax.set(xlabel='Obs', ylabel='Fct', title=f"{title}\nAcc: {acc:0.2f}")
    ax.xaxis.set_label_position('top')
    plt.tight_layout()
    # plt.show()
    plt.savefig(f"{dir_res}/{title}_ConfMatrix.png")
    plt.close()
    return


def plot_balance(y_train, y_test, title):
    # Checking the balance of the target variable in the dataset
    _, ax = plt.subplots(figsize=(4, 4))
    pd.concat([y_train, y_test]).value_counts(normalize=True).plot.bar(
        color=['skyblue', 'navy'], alpha=0.9, rot=0, ax=ax)
    plt.xticks(ticks=[1, 0], labels=["SEEPAGE", "OIL PILL"])
    # plt.bar_label(ax.containers[0], fmt='%.2f%%')
    plt.annotate('Imbalanced!', xy=(.7, 0.6), fontsize=12,
                 color='red', fontweight='bold')
    ax.set(title=f"CLASSE Balancing")
    plt.tight_layout()
    # plt.show()
    plt.savefig(f"{dir_res}/{title}_Balance.png")
    plt.close()
    return


def plot_confusion_matrix1(cm, classes,
                           normalize=False,
                           title='Confusion matrix',
                           cmap=plt.cm.Blues, save=False):
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes)
    plt.yticks(tick_marks, classes)
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, cm[i, j],
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    if save:
        plt.savefig(f"{dir_res}/{title}.png")
    plt.show()
    plt.close()
    return
