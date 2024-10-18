from os.path import expanduser
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session

# A cross-platform way to get the home directory
home = expanduser("~")


def get_cred(org, keyword):
    # org="EUMETSAT"; keyword="consumer_key"
    with open(f"{home}/ProjDocs/Projects/Credentials_{org}.txt") as credfile:
        content = credfile.read().split("\n")  # split it into lines
        content = [x for x in content if len(x) > 0]
        content = [x.strip() for x in content if x[0] != "#"]
        res = [x for x in content if keyword in x][0].split(":")[1]
    return (res)


def get_token_copernicus():
    # Your client credentials
    client_id = 'sh-d24f4817-0580-483e-8848-9da97d8c598b'
    client_secret = 'tyIiP93xpxV2nHyPVJ87YmDKwBIvsmoR'

    # Create a session
    client = BackendApplicationClient(client_id=client_id)
    oauth = OAuth2Session(client=client)

    # Get token for the session
    token = oauth.fetch_token(token_url='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
                              client_secret=client_secret, include_client_id=True)
    return (token, oauth)


def get_requests_copernicus():
    # Get token for the session
    _, oauth = get_token_copernicus()

    # All requests using this session will have an access token automatically added
    resp = oauth.get(
        "https://sh.dataspace.copernicus.eu/configuration/v1/wms/instances")
    print(resp.content)
    return
