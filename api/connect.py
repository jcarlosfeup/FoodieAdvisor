import logging
import polars as pl
from api.places_client import GooglePlacesClient
from api.transformer import transform_places
from config import settings
from db.repositories import create_repository
from services.collection import RestaurantCollectionService


logger = logging.getLogger(__name__)

def collect_restaurants_from_api(city_name: str, country_name: str | None = None) -> pl.DataFrame:
    """Collect restaurant data from Google Places API, transform, and store in database.
    
    Args:
        city_name: Name of the city to search
        country_name: Optional country name to improve the search location
        
    Returns:
        Polars DataFrame containing transformed restaurant data
    """
    try:
        client = GooglePlacesClient(settings)
        service = RestaurantCollectionService(client, create_repository(settings.database_url))
        return pl.DataFrame(service.collect(city_name, country_name))
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
        
        transformed_data = transform_places(data, city_name)
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
    """Store transformed restaurant data in the configured PostgreSQL database.
    
    Args:
        df: Polars DataFrame containing restaurant data
    """
    try:
        if df.is_empty():
            logger.warning("No data to store - DataFrame is empty")
            return

        rows = df.to_dicts()
        count = create_repository(settings.database_url).save_restaurants(rows)
        logger.info(f"Successfully stored {count} restaurants in database")

    except Exception as e:
        logger.error(f"Error storing restaurants to database: {e}")
        raise


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
