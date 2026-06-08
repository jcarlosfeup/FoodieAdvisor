import logging
from storage import ReadWriterCSVHandler
from db.helper import is_city_fetched, add_city_to_db, fetch_city_restaurants
from api.connect import collect_restaurants_from_api
from view.visualization import add_background_image, create_headings, create_selectbox_list


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BUCKET_NAME = "foodie-advisor-prod-eu"
FILENAME = "world_cities.csv"
DEFAULT_CITY = "Porto"


def get_cities_df():
    """Fetch cities dataframe from local file and upload to GCS bucket."""
    try:
        bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                             bucket_name=BUCKET_NAME)
        logger.info(f"Uploading {FILENAME} to GCS bucket '{BUCKET_NAME}'")
        bucket_writer.upload_dataframe_to_gcs()
        logger.info(f"Reading {FILENAME} from GCS bucket")
        bucket_writer.read_df_from_bucket()
        logger.info(f"Successfully loaded {len(bucket_writer.df)} cities from {FILENAME}")
        return bucket_writer.df
    except Exception as e:
        logger.error(f"Error loading cities dataframe: {e}")
        raise


if __name__ == "__main__":
    try:
        add_background_image(path="assets/images/background.jpg")
        logger.info("Background image loaded successfully")

        city_list = get_cities_df()['name'].unique()
        logger.debug(f"Total cities available: {len(city_list)}")

        create_headings()
        
        # Set Porto as default city if available
        default_index = 0
        if DEFAULT_CITY in city_list:
            default_index = list(city_list).index(DEFAULT_CITY)
            logger.info(f"Set default city to '{DEFAULT_CITY}'")
        else:
            logger.warning(f"Default city '{DEFAULT_CITY}' not found in city list. Using first available city.")
        
        city = create_selectbox_list(city_list, default=default_index)
        logger.info(f"User selected city: {city}")

        restaurants_df = None
        
        # Check if city already is in DB
        if is_city_fetched(city_name=city):
            logger.info(f"City '{city}' found in database. Fetching restaurants...")
        else:
            logger.info(f"City '{city}' not in database. Calling API to fetch restaurants...")
            try:
                api_result = collect_restaurants_from_api(city)
                logger.info(f"API call completed - {len(api_result)} restaurants collected and stored")
                
                if len(api_result) > 0:
                    add_city_to_db(name=city)
                    logger.info(f"City '{city}' added to database")
                else:
                    logger.warning(f"No restaurants found for '{city}' from API")
            except Exception as e:
                logger.error(f"Failed to collect restaurants from API for '{city}': {e}")
        
        # Fetch restaurants from database (single invocation)
        try:
            restaurants_df = fetch_city_restaurants(city)
            if not restaurants_df.is_empty():
                logger.info(f"Retrieved {len(restaurants_df)} restaurants for '{city}' as Polars DataFrame")
            else:
                logger.warning(f"No restaurants found in database for '{city}'")
        except Exception as e:
            logger.error(f"Failed to fetch restaurants for '{city}': {e}")
            restaurants_df = None

        # TODO transform query result and display on map
        # if restaurants_df is not None and not restaurants_df.is_empty():
        #     displayMapWithMarkers(restaurants_df)
        
    except Exception as e:
        logger.error(f"An error occurred in main execution: {e}", exc_info=True)
        raise
