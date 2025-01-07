from google.cloud import storage


BUCKET_NAME="foodie-advisor-prod-eu"
FILENAME="restaurants.csv"


def write_df_to_csv(df, filename):
    path=f"{filename}.csv"
    df.to_csv(path)


def upload_dataframe_to_gcs():
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    blob = bucket.blob(FILENAME)
    blob.upload_from_filename(FILENAME)


upload_dataframe_to_gcs()
