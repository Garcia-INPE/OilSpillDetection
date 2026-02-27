import os
import pandas as pd
from matplotlib import pyplot as plt
pd.set_option('display.max_columns', None)
os.chdir("/home/jrmgarcia/ProjDocs/OilSpill/src")

fname_csv = "dataout/DS/CSV/Oil_Stats_16bits.csv"
STATS = pd.read_csv(fname_csv, delimiter=";")

STATS.dtypes
STATS.columns
DS = STATS[["CENTR_KM_LAT", "CENTR_KM_LON", "UTM_ZONE", "AREA_KM2", "PERIM_KM", "COMPLEX_MEAS", "SPREAD", "SHP_FACT", "HU_MOM1", "HU_MOM2", "HU_MOM3", "HU_MOM4", "HU_MOM5", "HU_MOM6", "HU_MOM7", "CIRCULARITY", "PERI_AREA_RATIO", "FG_STD", "FG_VAR",
            "FG_MIN", "FG_MAX", "FG_MEAN", "FG_MEDIAN", "FG_VAR_COEF", "BG_STD", "BG_VAR", "BG_MIN", "BG_MAX", "BG_MEAN", "BG_MEDIAN", "BG_VAR_COEF", "FG_DARK_INTENS", "FG_BG_KS_STAT", "FG_BG_KS_RES", "FG_BG_MW_STAT", "FG_BG_MW_RES", "FG_BG_RAT_ARI", "FG_BG_RAT_QUA", "AREA_KM_DS", "PERIM_KM_DS", "CLASSE", "SUBCLASSE"]]
DS.describe

# Show all existent combination betwee CLASSE and SUBCLASSE
DS.groupby(by=["CLASSE", "SUBCLASSE"]).size()
# -----------------------------------------
# CLASSE         SUBCLASSE
# -----------------------------------------
# OIL SPILL      IDENTIFIED TARGET      224
#                UNIDENTIFIED TARGET    103
# SEEPAGE SLICK  CANTAREL                26
#                CLUSTER SEEPAGE         20
#                ORPHAN SEEPAGE          12

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
