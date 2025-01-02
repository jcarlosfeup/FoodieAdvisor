import requests
import time
from google.oauth2 import service_account
from google.auth.transport.requests import Request


API_KEY = "AIzaSyBOHqgJq1SLlb7-IIzntJrRwNUX0Wt7Anw"
BASE_URL = "https://places.googleapis.com/v1/places:searchText"
SERVICE_ACCOUNT_FILE = "foodie-advisor-e02c03a87c85.json"


credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def get_access_token(credentials):
    credentials.refresh(Request())
    return credentials.token


def make_api_call(token, next_page_token, search_text: str):
    header = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "places.displayName,places.id,places.primaryType,places.rating,places.userRatingCount,places.priceLevel,nextPageToken",
    }

    body = {
        "textQuery": search_text,
        "includedType": "restaurant",
        "minRating": 4.3,
        "pageToken": next_page_token,
    }

    response = requests.post(url=BASE_URL, headers=header, json=body).json()

    # with open("output2.txt", 'w') as file:
    #    print(response.text, file=file)
    time.sleep(2)

    return response


if __name__ == "__main__":
    access_token = get_access_token(credentials)
    next_page_token = ""
    page_count = 0

    result = []

    while True:
        response = make_api_call(
            token=access_token,
            next_page_token=next_page_token,
            search_text="Portuguese traditional food in Porto, Portugal",
        )

        next_page_token = response.get("nextPageToken")
        result.extend(response.get("places"))

        page_count += 1
        print(f"Page count: {page_count}")

        if not next_page_token:
            print("No more pages to display")
            break

    print(result)
    print(f"Number of restaurants found: {len(result)}")
