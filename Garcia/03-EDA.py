import pandas as pd
from matplotlib import pyplot as plt
pd.set_option('display.max_columns', None)

fname_csv = "Oil_Stats.csv"
STATS = pd.read_csv(fname_csv, delimiter=";")
STATS.dtypes
STATS.columns
DS = STATS[['AREA_KM2', 'PERIM_KM', 'COMPLEX_MEAS', 'SPREAD', 'SHP_FACT',
            'HU_MOM1', 'HU_MOM2', 'HU_MOM3', 'HU_MOM4', 'HU_MOM5', 'HU_MOM6', 'HU_MOM7',
            'CIRCULARITY', 'PERI_AREA_RATIO',
            'FG_STD', 'FG_VAR', 'FG_MIN', 'FG_MAX', 'FG_MEAN', 'FG_MEDIAN', 'FG_VAR_COEF',
            'FG_DARK_INTENS', "CLASSE"]]
DS.describe

# HISTOGRAMAS
DS.hist(['FG_STD'], by='CLASSE', sharex=True, sharey=True)
plt.show()


DS.groupby(by="CLASSE").mean()

#               ,
#
# CLASSE = SEEPAGE SLICK | OIL SPILL
# SUBCLASSE = UNIDENTIFIED TARGET | ORPHAN SEEPAGE

STATS[['AREA_KM2']].groupby(by="CLASSE").mean()
X = STATS[['AREA_KM2', "CLASSE"]]
l = [[1, 2, 3], [1, None, 4], [2, 1, 3], [1, 2, 2]]
df = pd.DataFrame(l, columns=["a", "b", "c"])
