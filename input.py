from storage import ReadWriterCSVHandler, BUCKET_NAME


def get_cities_df():
    bucket_writer = ReadWriterCSVHandler(filename="world_cities.csv",
                                         bucket_name=BUCKET_NAME)
    bucket_writer.upload_dataframe_to_gcs()
    bucket_writer.read_df_from_bucket()

    return bucket_writer.df
