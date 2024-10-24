# Sentinel 3 L2 WCT and WST Products are generated and maintained by EUMETSAT.
# Description: https://www.eumetsat.int/sea-surface-temperature-services.
# https://user.eumetsat.int/resources/user-guides/eumetsat-data-access-client-eumdac-guide

# DISCOVERING PRODUCT ID (using bin client)
# eumdac describe | grep -i temp
# EO:EUM:DAT:0412 - SLSTR Level 2 Sea Surface Temperature (SST) - Sentinel-3

import time
from pprint import pprint
import requests
import shutil
import datetime
import eumdac
import importlib

import FunConnect as FConn
importlib.reload(FConn)

# ----------------------------------------------------------------
# Connect to EUMETSAT
# ----------------------------------------------------------------
consumer_key = FConn.get_cred("EUMETSAT", "consumer_key")
consumer_secret = FConn.get_cred("EUMETSAT", "consumer_secret")
credentials = (consumer_key, consumer_secret)
token = eumdac.AccessToken(credentials)
datastore = eumdac.DataStore(token)
try:
    print(f"This token '{token}' expires {token.expiration}")
except requests.exceptions.HTTPError as exc:
    print(f"Error when trying the request to the server: '{exc}'")

# ----------------------------------------------------------------
# Select a collection
# eumdac describe | grep -i temp (using bin client)
# EO:EUM:DAT:0412 - SLSTR Level 2 Sea Surface Temperature (SST) - Sentinel-3
# ----------------------------------------------------------------
collection_id = "EO:EUM:DAT:0412"          # SST
# collection_id = "EO:EUM:DAT:MSG:HRSEVIRI"  # EXAMPLE
roi = {"NSWE": [20.478913201345947, 18.53783353542049, -
                93.1910043327223, -90.48797364280666]}  # NSWE
start = datetime.datetime(2020, 8, 21, 0, 0)
end = datetime.datetime(2020, 9, 1, 23, 59)

selected_collection = datastore.get_collection(collection_id)
latest = selected_collection.search().first()
try:
    print(latest)
except eumdac.datastore.DataStoreError as error:
    print(f"Error related to the data store: '{error.msg}'")
except eumdac.collection.CollectionError as error:
    print(f"Error related to the collection: '{error.msg}'")
except requests.exceptions.RequestException as error:
    print(f"Unexpected error: {error}")

# ----------------------------------------------------------------
# Filter products of selected collection by time and area.
# ----------------------------------------------------------------
# Add vertices for polygon, wrapping back to the start point.
geometry = [[-1.0, -1.0], [4.0, -4.0], [8.0, -2.0],
            [9.0, 2.0], [6.0, 4.0], [1.0, 5.0], [-1.0, -1.0]]
# Set sensing start and end time

# Retrieve datasets that match our filter
products = selected_collection.search(
    # geo='POLYGON(({}))'.format(
    #    ','.join(["{} {}".format(*coord) for coord in geometry])),
    geo=roi,
    dtstart=start,
    dtend=end)

print(f'Found Datasets: {
      products.total_results} datasets for the given time range')

for product in products:
    print(str(product))


# ----------------------------------------------------------------
# Download all products from above search
# ----------------------------------------------------------------
for product in products:
    with product.open() as fsrc, \
            open(fsrc.name, mode='wb') as fdst:
        shutil.copyfileobj(fsrc, fdst)
        print(f'Download of product {product} finished.')
print('All downloads are finished.')

# Defining the chain configuration
chain = eumdac.tailor_models.Chain(
    product='HRSEVIRI',
    format='png_rgb',
    filter={"bands": ["channel_3", "channel_2", "channel_1"]},
    projection='geographic',
    roi={"NSWE": [20.478913201345947, 18.53783353542049, -
                  93.1910043327223, -90.48797364280666]}
)
# roi parameter can be:
#  - a pre-defined one.
#  - as "{"NSWE" : [37, 2, -19, 21]}".


# ----------------------------------------------------------------
# Customising products with the Data Tailor
# To customise a product with the Data Tailor, we need to provide following information;
# - A product object (we have, 'latest')
# - A chain configuration (to be defined)
# ----------------------------------------------------------------

# To check if Data Tailor works as expected, we are requesting our quota information
datatailor = eumdac.DataTailor(token)
try:
    pprint(datatailor.quota)
except eumdac.datatailor.DataTailorError as error:
    print(f"Error related to the Data Tailor: '{error.msg}'")
except requests.exceptions.RequestException as error:
    print(f"Unexpected error: {error}")

# ----------------------------------------------------------------
# Defining your own configuration chain
# ----------------------------------------------------------------
chain = eumdac.tailor_models.Chain(
    product='HRSEVIRI',
    format='png_rgb',
    filter={"bands": ["channel_3", "channel_2", "channel_1"]},
    projection='geographic',
    roi='west_africa'
)
# roi parameter above is a pre-defined one. It's possible to use "roi=" as follows "{"NSWE" : [37,2,-19,21]}".

# Send the customisation to Data Tailor Web Services
customisation = datatailor.new_customisation(latest, chain)

try:
    print(f"Customisation {customisation._id} started.")
except eumdac.datatailor.DataTailorError as error:
    print(f"Error related to the Data Tailor: '{error.msg}'")
except requests.exceptions.RequestException as error:
    print(f"Unexpected error: {error}")

# After the customisation has started, it's possible to run 'Customisation Loop' below.
# It checks the status of the customisation until the customisation is completed.
# While it loops, it prints the status of the job. I
status = customisation.status
sleep_time = 10  # seconds

# Customisation Loop
while status:
    # Get the status of the ongoing customisation
    status = customisation.status

    if "DONE" in status:
        print(f"Customisation {customisation._id} is successfully completed.")
        break
    elif status in ["ERROR", "FAILED", "DELETED", "KILLED", "INACTIVE"]:
        print(f"Customisation {
              customisation._id} was unsuccessful. Customisation log is printed.\n")
        print(customisation.logfile)
        break
    elif "QUEUED" in status:
        print(f"Customisation {customisation._id} is queued.")
    elif "RUNNING" in status:
        print(f"Customisation {customisation._id} is running.")
    time.sleep(sleep_time)

# ----------------------------------------------------------------
# How to list, create, delete saved configuration chains in Data Tailor
# ----------------------------------------------------------------
for chain in datatailor.chains.search():
    print(chain)
    print('---')

for chain in datatailor.chains.search(product="HRSEVIRI"):
    print(chain)
    print('---')

# ----------------------------------------------------------------
# Clearing customisations from the Data Tailor
# The Data Tailor Web Service has a 20 Gb limit, so it's important to clear old customisations.
# ----------------------------------------------------------------
try:
    customisation.delete()
except eumdac.datatailor.CustomisationError as exc:
    print("Customisation Error:", exc)
except requests.exceptions.RequestException as error:
    print("Unexpected error:", error)
