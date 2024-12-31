import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request


API_KEY = "AIzaSyBOHqgJq1SLlb7-IIzntJrRwNUX0Wt7Anw"
BASE_URL = "https://places.googleapis.com/v1/places:searchText"
SERVICE_ACCOUNT_FILE = "foodie-advisor-e02c03a87c85.json"


credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def get_access_token(credentials):
    credentials.refresh(Request())
    return credentials.token

# places.displayName,places.id TO SELECT specific fields
def make_api_call(token, search_text: str):
    header = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.id"
    }

    body = {
        "textQuery": search_text
    }
    response = requests.post(url=BASE_URL,
                             headers=header,
                             json=body)

    print(response.status_code)
    print(response.text)


if __name__ == "__main__":
    access_token = get_access_token(credentials)

    make_api_call(token=access_token,
                  search_text="Vegetarian Food in Porto, Portugal")
