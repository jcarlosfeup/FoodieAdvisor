from storage import ReadWriterCSVHandler
from db.helper import is_city_fetched, add_city_to_db, fetch_city_restaurants
from api.connect import connect_and_collect
from view.visualization import add_background_image, create_headings, create_selectbox_list, displayMapWithMarkers


BUCKET_NAME="foodie-advisor-prod-eu"
FILENAME="world_cities.csv"


def get_cities_df():
    bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                         bucket_name=BUCKET_NAME)
    bucket_writer.upload_dataframe_to_gcs()
    bucket_writer.read_df_from_bucket()

    return bucket_writer.df


if __name__ == "__main__":
    add_background_image(path="assets/images/background.jpg")

    city_list = get_cities_df()['name'].unique()
    #city_list = list(filter(lambda k: 'Porto' in k and len(k) == 5, city_list))

    create_headings()
    city = create_selectbox_list(city_list)

    # TODO check if city already is in DB
    if is_city_fetched(city_name=city):
        # TODO query all restaurants to specific city
        restaurants_lst = fetch_city_restaurants(city)
        print(restaurants_lst)
    else:
        # TODO call API
        result = connect_and_collect(city)
        print(f"Number of restaurants found: {len(result)}")
        if len(result) > 0:
            add_city_to_db(name=city)

    """ bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                         bucket_name=BUCKET_NAME)

    bucket_writer.read_df_from_bucket()
    print(bucket_writer.df) """
    
    # TODO transform query result in dataframe
    #filtered_data = bucket_writer.df[bucket_writer.df['city'] == city]
    #displayMapWithMarkers(filtered_data)
