from google.cloud import storage
from io import StringIO
import pandas as pd


class ReadWriterCSVHandler:

    def __init__(self, filename, bucket_name=None, df=None):
        self.storageClient = storage.Client()
        self.filename = filename
        self.bucket = bucket_name
        self.df = df

    def write_df_to_csv(self):
        path = self.filename
        self.df.to_csv(path)

    def read_df_from_bucket(self):
        bucket = self.storageClient.get_bucket(self.bucket)
        blob = bucket.blob(self.filename)
        content = blob.download_as_text()

        self.df = pd.read_csv(StringIO(content))


    def upload_dataframe_to_gcs(self):
        bucket = self.storageClient.bucket(self.bucket_name)
        blob = bucket.blob(self.filename)
        blob.upload_from_filename(self.filename)


bucket_writer = ReadWriterCSVHandler(filename="restaurants.csv",bucket_name="foodie-advisor-prod-eu")
#bucket_writer.upload_dataframe_to_gcs()
bucket_writer.read_df_from_bucket()

bucket_writer.df.show(2)

