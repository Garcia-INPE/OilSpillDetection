#
# Function to return data from the XML annotation file
#
# ***** NOT BEING USED ******
#
import os
import re
import gzip
import shutil


def get_data_from_annot(dir_raw_data, bname):
    # In case of returning data from annotation.xml
    root_name = bname.split(" ")[1][:33]  # Root pattern of the name
    flds = get_S1A_name_fields(root_name)
    patt_dir = get_S1A_SAFE_dir_patt(flds)
    dir_SAFE = [d[0] for d in os.walk(dir_raw_data) if re.search(
        patt_dir, os.path.basename(d[0]))][0]

    dir_annot = f"{dir_SAFE}/annotation/"
    flds_xml = get_S1A_name_fields(os.path.basename(dir_SAFE))
    fname_xml = get_S1A_XML_file_patt(
        flds_xml).lower().replace("_", "-")
    fname_xml = f"{dir_annot}/{fname_xml}"
    if not os.path.exists(fname_xml):
        fname_gz = f"{fname_xml}.gz"
        assert os.path.exists(f"{fname_gz}")
        with gzip.open(fname_gz, 'rb') as f_in:
            with open(fname_xml, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    return


def get_S1A_SAFE_dir_patt(flds):
    return (f"^{flds['mission']}_{flds['beam_mode']}_{flds['prod_type']}{flds['res']}_{
            flds['proc_lev']}{flds['prod_class']}{flds['polariz']}_{flds['date_on']}T{
                flds['hour_on']}_[0-9]{{8}}T[0-9]{{6}}_[0-9A-F]{{6}}_[0-9A-F]{{6}}_[0-9A-F]{{4}}.SAFE$")


def get_S1A_XML_file_patt(flds):
    # flds completos
    return (f"{flds['mission']}_{flds['beam_mode']}_{flds['prod_type']}_vv_{flds['date_on']}T{
        flds['hour_on']}_{flds['date_off']}T{flds['hour_off']}_{flds['orbit']}_{flds['take_id']}-001.xml")


def get_S1A_name_fields(root_name):
    # https://sentiwiki.copernicus.eu/web/s1-products#S1Products-SARNamingConventionS1-Products-SAR-Naming-Convention
    # root_name = "S1A_IW_GRDH_1SDV_20200117T001541_20200117T001606_030833_03899B_5AEE.SAFE"
    mission = root_name[:3]        # S1A     S1A | S1B | S1C                                      # nopep8
    beam_mode = root_name[4:6]     # IW      S[1-6] | IW | EW | WV | EN | N[1-6] | Z[1-6,I,E,W]   # nopep8
    prod_type = root_name[7:10]    # GRD     RAW | SLC | GRD | OCN | ETA                          # nopep8
    res = root_name[10:11]         # H       Full | High | Medium | _ (N/A)                       # nopep8
    proc_lev = root_name[12:13]    # 1       0 | 1 | 2 | A                                        # nopep8
    prod_class = root_name[13:14]  # S       SAR | Annotation | Noise | Calibration | X (only for ETAD product)   # nopep8
    polariz = root_name[14:16]     # DV      SH | SV | DH | DV | HH | HV | VV | VH                # nopep8
    date_on = root_name[17:25]
    hour_on = root_name[26:32]
    date_off = hour_off = orbit = take_id = prod_id = ""
    if len(root_name) >= 62:
        date_off = root_name[33:41]
        hour_off = root_name[42:48]
        orbit = root_name[49:55]
        take_id = root_name[56:62]
        if len(root_name) >= 67:
            prod_id = root_name[63:67]

    return {'mission': mission, 'beam_mode': beam_mode, 'prod_type': prod_type, 'res': res, 'proc_lev': proc_lev,
            'prod_class': prod_class, 'polariz': polariz, 'date_on': date_on, 'hour_on': hour_on, 'date_off': date_off,
            'hour_off': hour_off, 'orbit': orbit, 'take_id': take_id, 'prod_id': prod_id}
