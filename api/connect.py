import requests
import time
import logging
import pandas as pd
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from storage import ReadWriterCSVHandler
from db.helper import create_db_engine


logger = logging.getLogger(__name__)

BASE_URL = "https://places.googleapis.com/v1/places:searchText"
SERVICE_ACCOUNT_FILE = "foodie-advisor-819220732215.json"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def get_access_token(credentials):
    """Get access token from Google credentials.
    
    Args:
        credentials: Google service account credentials
        
    Returns:
        Access token string
    """
    try:
        credentials.refresh(Request())
        logger.debug("Access token refreshed successfully")
        return credentials.token
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")
        raise


def make_api_call(token, next_page_token, search_text: str):
    """Make an API call to Google Places API.
    
    Args:
        token: Authorization token
        next_page_token: Token for pagination
        search_text: Search query text
        
    Returns:
        JSON response from API
    """
    try:
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

        response = requests.post(url=BASE_URL,
                                 headers=header,
                                 json=body)
        response.raise_for_status()  # Raise exception for bad status codes
        time.sleep(2)
        logger.debug(f"API call successful for search: {search_text}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for search '{search_text}': {e}")
        raise


def connect_and_collect(city_name: str):
    """Collect restaurant data from Google Places API for a city.
    
    Args:
        city_name: Name of the city to search
        
    Returns:
        List of restaurant data
    """
    try:
        access_token = get_access_token(credentials)
        next_page_token = ""
        page_count = 0
        result = []

        while True:
            response = make_api_call(
                token=access_token,
                next_page_token=next_page_token,
                # TODO call LLM to get the type of cuisine and country 
                search_text=f"Portuguese traditional food in {city_name}, Portugal",
            )
            next_page_token = response.get("nextPageToken")
            places = response.get("places", [])
            result.extend(places)

            page_count += 1
            logger.info(f"Page {page_count}: Retrieved {len(places)} restaurants")

            if not next_page_token:
                logger.info("All pages retrieved")
                break

        logger.info(f"Total restaurants collected: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error collecting restaurants for city '{city_name}': {e}")
        raise


def transform(data: list) -> pd.DataFrame:
    df = pd.DataFrame(data)
    df.rename(columns={"displayName": "name", "priceLevel": "price_level", "userRatingCount": "ratings_count"},
              inplace=True)

    df["name"] = df["name"].apply(lambda x: x["text"])
    df["latitude"] = df["location"].apply(lambda loc: loc.get("latitude", None))
    df["longitude"] = df["location"].apply(lambda loc: loc.get("longitude", None))
    df["city"] = "Porto"  # TODO change to dynamic code

    df = df.drop(columns=["id", "location", "primaryType", "viewport"])

    return df[["name", "city", "rating", "ratings_count", "price_level", "latitude", "longitude"]] 


if __name__ == "__main__":
    result = connect_and_collect()
    print(f"Number of restaurants found: {len(result)}")

    df = transform(data=result)
    print(df)

    engine = create_db_engine()
    print(df.columns)
    df.to_sql('restaurant',
              con=engine,
              if_exists='append',
              index=False)

    local_writer = ReadWriterCSVHandler(
        filename=FILENAME, bucket_name=BUCKET_NAME, df=df
    )
    local_writer.write_df_to_csv()
    #local_writer.upload_dataframe_to_gcs()
