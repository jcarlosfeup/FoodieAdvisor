import requests
import time
import logging
import polars as pl
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from db.helper import get_db_connection


logger = logging.getLogger(__name__)

BASE_URL = "https://places.googleapis.com/v1/places:searchText"
SERVICE_ACCOUNT_FILE = "foodie-advisor-819220732215.json"
REQUEST_TIMEOUT_SECONDS = 30
PAGINATION_DELAY_SECONDS = 2
FIELD_MASK = (
    "places.displayName,places.rating,places.userRatingCount,"
    "places.priceLevel,places.location,nextPageToken"
)

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
        if credentials.valid and credentials.token:
            return credentials.token

        credentials.refresh(Request())
        logger.debug("Access token refreshed successfully")
        return credentials.token
    except Exception as e:
        logger.error(f"Error refreshing access token: {e}")
        raise


def make_api_call(session, token, next_page_token, search_text: str):
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
            "X-Goog-FieldMask": FIELD_MASK,
        }

        body = {
            "textQuery": search_text,
            "includedType": "restaurant",
            "minRating": 4.3,
            "pageToken": next_page_token,
        }

        response = session.post(
            url=BASE_URL,
            headers=header,
            json=body,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()  # Raise exception for bad status codes
        logger.debug(f"API call successful for search: {search_text}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for search '{search_text}': {e}")
        raise


def collect_restaurants_from_api(city_name: str, country_name: str | None = None) -> pl.DataFrame:
    """Collect restaurant data from Google Places API, transform, and store in database.
    
    Args:
        city_name: Name of the city to search
        country_name: Optional country name to improve the search location
        
    Returns:
        Polars DataFrame containing transformed restaurant data
    """
    conn = None
    try:
        location = city_name if not country_name else f"{city_name}, {country_name}"
        cuisine = f"{country_name} traditional" if country_name else "local"
        search_text = f"{cuisine} restaurants in {location}"
        logger.info(f"Searching restaurants for location: {location}")

        access_token = get_access_token(credentials)
        next_page_token = ""
        page_count = 0
        result = []

        with requests.Session() as session:
            while True:
                response = make_api_call(
                    session=session,
                    token=access_token,
                    next_page_token=next_page_token,
                    search_text=search_text,
                )
                next_page_token = response.get("nextPageToken")
                places = response.get("places", [])
                result.extend(places)

                page_count += 1
                logger.info(f"Page {page_count}: Retrieved {len(places)} restaurants")

                if not next_page_token:
                    logger.info("All pages retrieved")
                    break

                # Google requires a short delay before a next-page token is usable.
                time.sleep(PAGINATION_DELAY_SECONDS)

        logger.info(f"Total restaurants collected: {len(result)}")
        
        # Transform data
        if result:
            df = transform(data=result,
                           city_name=city_name)
            logger.info(f"Transformed {len(df)} restaurants into DataFrame")
            
            # Store in database
            store_restaurants_to_db(df)
            logger.info(f"Stored {len(df)} restaurants in database for city '{city_name}'")
            
            return df
        else:
            logger.warning(f"No restaurants found for city '{city_name}'")
            return pl.DataFrame()
            
    except Exception as e:
        logger.error(f"Error collecting restaurants for city '{city_name}': {e}")
        raise


def transform(data: list, city_name: str) -> pl.DataFrame:
    """Transform raw API restaurant data into a structured Polars DataFrame.
    
    Args:
        data: List of raw restaurant data from API
        city_name: Name of the city for the restaurants
        
    Returns:
        Polars DataFrame with transformed restaurant data
    """
    try:
        if not data:
            logger.warning("No data to transform")
            return pl.DataFrame()
        
        # Extract relevant fields from nested API response
        transformed_data = []
        for restaurant in data:
            try:
                location = restaurant.get("location", {})
                display_name = restaurant.get("displayName", {})
                
                transformed_data.append({
                    "name": display_name.get("text", "Unknown"),
                    "city": city_name,
                    "rating": restaurant.get("rating", None),
                    "ratings_count": restaurant.get("userRatingCount", 0),
                    "price_level": restaurant.get("priceLevel", None),
                    "latitude": location.get("latitude", None),
                    "longitude": location.get("longitude", None),
                })
            except (KeyError, TypeError) as e:
                logger.warning(f"Error transforming restaurant record: {e}")
                continue
        
        if not transformed_data:
            logger.warning(f"No valid restaurants transformed for city '{city_name}'")
            return pl.DataFrame()
        
        df = pl.DataFrame(transformed_data)
        logger.debug(f"Successfully transformed {len(df)} restaurants")
        return df
        
    except Exception as e:
        logger.error(f"Error transforming restaurant data for city '{city_name}': {e}")
        raise


def store_restaurants_to_db(df: pl.DataFrame) -> None:
    """Store transformed restaurant data into SQLite database.
    
    Args:
        df: Polars DataFrame containing restaurant data
    """
    conn = None
    try:
        if df.is_empty():
            logger.warning("No data to store - DataFrame is empty")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        columns = df.columns
        placeholders = ", ".join("?" for _ in columns)
        column_names = ", ".join(columns)
        sql_statement = f"INSERT INTO restaurant ({column_names}) VALUES ({placeholders})"

        rows = list(df.iter_rows())
        cursor.executemany(sql_statement, rows)
        conn.commit()
        logger.info(f"Successfully stored {len(rows)} restaurants in database")

    except Exception as e:
        logger.error(f"Error storing restaurants to database: {e}")
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    try:
        df = collect_restaurants_from_api(city_name="Porto")
        if not df.is_empty():
            print(f"Number of restaurants found and stored: {len(df)}")
            print(f"Columns: {df.columns}")
            print(df.head())
        else:
            print("No restaurants were collected and stored.")
    except Exception as e:
        logger.error(f"Failed to collect restaurants: {e}")
