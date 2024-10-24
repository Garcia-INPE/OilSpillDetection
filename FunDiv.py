import os
import re
import math


def get_epsg_from_latlon(lat, lon):
    # lat=centr_deg_lat; lon=centr_deg_lon
    utm_band = str((math.floor((lon + 180) / 6) % 60) + 1)
    if len(utm_band) == 1:
        utm_band = '0'+utm_band
    if lat >= 0:
        epsg_code = '326' + utm_band
    else:
        epsg_code = '327' + utm_band
    return epsg_code


def get_S1A_fname_fields(dir_raw_data, bname):
    # Finds which dir is the dir associated with the calibrated fname
    # And gets all fields from it (because the name of the calibrated TIFF is incomplete)
    # https://sentiwiki.copernicus.eu/web/s1-products#S1Products-SARNamingConventionS1-Products-SAR-Naming-Convention
    # root_name = "S1A_IW_GRDH_1SDV_20200117T001541_20200117T001606_030833_03899B_5AEE.SAFE"
    root_fname = bname.split(" ")[1][:33]  # Root pattern of the name
    dir_ori_tiff = [d for d in os.listdir(dir_raw_data) if re.match(
        root_fname, os.path.basename(d))][0]
    assert len(dir_ori_tiff) == 67

    mission = dir_ori_tiff[:3]        # S1A     S1A | S1B | S1C                                      # nopep8
    beam_mode = dir_ori_tiff[4:6]     # IW      S[1-6] | IW | EW | WV | EN | N[1-6] | Z[1-6,I,E,W]   # nopep8
    prod_type = dir_ori_tiff[7:10]    # GRD     RAW | SLC | GRD | OCN | ETA                          # nopep8
    res = dir_ori_tiff[10:11]         # H       Full | High | Medium | _ (N/A)                       # nopep8
    proc_lev = dir_ori_tiff[12:13]    # 1       0 | 1 | 2 | A                                        # nopep8
    prod_class = dir_ori_tiff[13:14]  # S       SAR | Annotation | Noise | Calibration | X (only for ETAD product)   # nopep8
    polariz = dir_ori_tiff[14:16]     # DV      SH | SV | DH | DV | HH | HV | VV | VH                # nopep8
    date_on = dir_ori_tiff[17:25]
    hour_on = dir_ori_tiff[26:32]
    date_off = dir_ori_tiff[33:41]
    hour_off = dir_ori_tiff[42:48]
    orbit = dir_ori_tiff[49:55]
    take_id = dir_ori_tiff[56:62]
    prod_id = dir_ori_tiff[63:67]
    return {'mission': mission, 'beam_mode': beam_mode, 'prod_type': prod_type, 'res': res, 'proc_lev': proc_lev,
            'prod_class': prod_class, 'polariz': polariz, 'date_on': date_on, 'hour_on': hour_on, 'date_off': date_off,
            'hour_off': hour_off, 'orbit': orbit, 'take_id': take_id, 'prod_id': prod_id}
