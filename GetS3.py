import datetime
import pandas as pd
import requests
from datetime import timedelta


def get_access_token(username: str, password: str):
    # username="roberto.garcia@inpe.br"; password="A3Ws2F5wx4!Sv.%"
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
        )
        r.raise_for_status()
    except Exception as e:
        raise Exception(
            f"Access token creation failed. Reponse from the server was: {
                r.json()}"
        )
    return (r.json()["access_token"])


start_date = "2020-08-31"
end_date = "2020-09-01"
data_collection = "SENTINEL-3"
aoi = "POLYGON((5 53, 9 53, 9 56, 5 56, 5 53))'"
delta_days = 1

while datetime.datetime.strptime(start_date, '%Y-%m-%d')+timedelta(delta_days) < datetime.datetime.strptime(end_date, '%Y-%m-%d'):
    access_token = get_access_token(
        "roberto.garcia@inpe.br", "A3Ws2F5wx4!Sv.%")
    end_temp = datetime.datetime.strptime(
        start_date, '%Y-%m-%d')+timedelta(delta_days)
    end_temp = end_temp.strftime('%Y-%m-%d')
    json = requests.get(
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' and OData.CSC.Intersects(area=geography'SRID=4326;{
            aoi}) and ContentDate/Start gt {start_date}T00:00:00.000Z and ContentDate/Start lt {end_temp}T23:23:59.000Z"
    ).json()
    dat = pd.DataFrame.from_dict(json["value"])

    for name, id_ in zip(dat['Name'], dat['Id']):
        if 'WST' in name:
            url = f"https://zipper.dataspace.copernicus.eu/odata/v1/Products({
                id_})/$value"

            headers = {"Authorization": f"Bearer {access_token}"}

            session = requests.Session()
            session.headers.update(headers)
            response = session.get(url, headers=headers, stream=True)

            with open("new/"+id_+".zip", "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)
    start_date = datetime.datetime.strptime(
        start_date, '%Y-%m-%d')+timedelta(delta_days)
    start_date = start_date.strftime('%Y-%m-%d')
