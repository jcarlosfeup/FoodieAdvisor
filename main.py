from storage import ReadWriterCSVHandler
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
    print(f"City is {city}")
    
    # TODO check if city already is in DB
    # if not, API needs to be called
    # CHANGE THIS to call API not GCP bucket
    bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                         bucket_name=BUCKET_NAME)

    bucket_writer.read_df_from_bucket()
    print(bucket_writer.df)

    
    filtered_data = bucket_writer.df[bucket_writer.df['city'] == city]

    displayMapWithMarkers(filtered_data)

    

