# Create a CSV file containing a list of Kaggle datasets with their metadata based on the txt file
# /home/jrmgarcia/ProjDocs/OilSpill/src/datain/DS_OIL_Kaggle.txt

import os

os.chdir("/home/jrmgarcia/ProjDocs/OilSpill/src")

fname_txt = "./datain/DS_OIL_Kaggle.txt"
encoding = "utf-8"

# Read the txt file
with open(fname_txt, 'r', encoding=encoding) as f_txt:
    txt = f_txt.readlines()

# Eliminate lines the starts with " " or "#"
txt = [line for line in txt if not (
    line.startswith(" ") or line.startswith("#"))]

# Remove "\n"
txt = [line.replace("\n", "") for line in txt]

# Create a CSV file from the txt list considering that each DS is reported in 4 rows
fname_csv = "./dataout/DS_OIL_Kaggle_List.csv"
with open(fname_csv, 'w', encoding=encoding) as f_csv:
    f_csv.write(
        "SOURCE,NAME,AUTHOR,PAPER,UPLOADED,UP_YS,USAB,FILES,SIZE,DOWNS,DOWNS_Y,NBS,VOTES,RELEV,REASON\n")
    i = 0
    for i in range(0, len(txt), 4):
        ds_name = txt[i].replace(", ", " - ").replace(",", " - ")
        metadata1 = txt[i+1].split("·")
        ds_author = metadata1[0].strip().replace(",", " - ")
        ds_updated_qtd = metadata1[1].split("Updated")[1].strip().split(" ")[
            0].replace("a", "1")
        ds_updated_unit = metadata1[1].split(
            "Updated")[1].strip().split(" ")[1][0]
        ds_updated = f"{ds_updated_qtd}{ds_updated_unit}"
        # Updated years (min = 1)
        ds_updated_ys = ds_updated_qtd if ds_updated_unit == "y" else "1"
        metadata2 = txt[i+2].split("·")
        # Check if the term "Usability" rating is reported in metadada and get its value
        ds_usab = ""
        ds_files = 0
        ds_size = ""
        ds_downloads = 0
        ds_downloads_y = 0
        ds_notebooks = 0
        for m in metadata2:
            m = m.strip().replace(",", "")
            if "Usability" in m:
                ds_usab = m.split("Usability")[1].strip()
            if "File" in m:
                ds_files = int(m.split("File")[0].strip())
            if "kB" in m:
                ds_size = m.split("kB")[0].strip()
            if "MB" in m:
                ds_size = m.split("MB")[0].strip()
            if "GB" in m:
                ds_size = m.split("GB")[0].strip()
            if "download" in m:
                ds_downloads = int(m.split("download")[0])
                ds_downloads_y = round(ds_downloads / int(ds_updated_ys))
            if "notebook" in m:
                ds_notebooks = int(m.split("notebook")[0])
        ds_upvotes = int(txt[i+3].strip())
        # Write the DS info in the CSV file
        line = f"Kaggle,{ds_name},{ds_author},,{ds_updated},{ds_updated_ys},{ds_usab},{ds_files},{ds_size},{ds_downloads},{ds_downloads_y},{ds_notebooks},{ds_upvotes},,"
        x = f_csv.write(f"{line}\n")
        print(f"Written DS: {line}")

print(f"CSV file created: {fname_csv}")
