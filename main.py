import logging
from storage import ReadWriterCSVHandler
from db.helper import is_city_fetched, add_city_to_db, fetch_city_restaurants
from api.connect import connect_and_collect
from view.visualization import add_background_image, create_headings, create_selectbox_list


# Configure logging
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

        # Check if city already is in DB
        if is_city_fetched(city_name=city):
            logger.info(f"City '{city}' found in database. Fetching restaurants...")
            restaurants_lst = fetch_city_restaurants(city)
            logger.info(f"Retrieved {len(restaurants_lst)} restaurants for '{city}'")
        else:
            logger.info(f"City '{city}' not in database. Calling API to fetch restaurants...")
            result = connect_and_collect(city)
            logger.info(f"Number of restaurants found: {len(result)}")
            if len(result) > 0:
                add_city_to_db(name=city)
                logger.info(f"City '{city}' added to database")
            else:
                logger.warning(f"No restaurants found for '{city}'")

        # TODO transform query result in dataframe
        # filtered_data = bucket_writer.df[bucket_writer.df['city'] == city]
        # displayMapWithMarkers(filtered_data)
        
    except Exception as e:
        logger.error(f"An error occurred in main execution: {e}", exc_info=True)
        raise
