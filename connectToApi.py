import requests
import time
import pandas as pd
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from storage import ReadWriterCSVHandler, BUCKET_NAME, FILENAME


BASE_URL = "https://places.googleapis.com/v1/places:searchText"
SERVICE_ACCOUNT_FILE = "foodie-advisor-819220732215.json"

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
        "X-Goog-FieldMask": "places.displayName,places.id,places.primaryType,places.rating,places.userRatingCount,places.priceLevel,places.location,places.viewport,nextPageToken",
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

# TODO
# def connect
# def collect_data():

def transform(df: pd.DataFrame) -> pd.DataFrame:
    df.rename(columns={"displayName": "name"}, inplace=True)
    df['name'] = df['name'].apply(lambda x: x['text'])
    df['latitude'] = df['location'].apply(lambda loc: loc.get('latitude', None))
    df['longitude'] = df['location'].apply(lambda loc: loc.get('longitude', None))
    df['city'] = 'Porto'   # TODO change to dynamic code

    return df.drop(columns=['location'])


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
        print(response)
        next_page_token = response.get("nextPageToken")
        result.extend(response.get("places"))

        page_count += 1
        print(f"Page count: {page_count}")

        if not next_page_token:
            print("No more pages to display")
            break

    print(result)

    df = pd.DataFrame(result)
    df = transform(df)

    local_writer = ReadWriterCSVHandler(filename=FILENAME,
                                        bucket_name=BUCKET_NAME,
                                        df=df)

    print(f"Number of restaurants found: {len(result)}")
    local_writer.write_df_to_csv()
    local_writer.upload_dataframe_to_gcs()
