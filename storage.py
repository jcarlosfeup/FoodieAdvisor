from google.cloud import storage
from io import StringIO
import pandas as pd


BUCKET_NAME="foodie-advisor-prod-eu"
FILENAME="restaurants.csv"

class ReadWriterCSVHandler:

    def __init__(self, filename, bucket_name=None, df=None):
        self.storageClient = storage.Client()
        self.filename = filename
        self.bucket = bucket_name
        self.df = df

    def write_df_to_csv(self):
        path = self.filename
        self.df.to_csv(path)

    def read_local_csv(self):
        self.df = pd.read_csv(filepath_or_buffer=self.filename)

    def read_df_from_bucket(self):
        bucket = self.storageClient.get_bucket(self.bucket)
        blob = bucket.blob(self.filename)
        content = blob.download_as_text()

        self.df = pd.read_csv(StringIO(content))

    def upload_dataframe_to_gcs(self):
        bucket = self.storageClient.bucket(self.bucket)
        blob = bucket.blob(self.filename)
        blob.upload_from_filename(self.filename)


if __name__ == "__main__":
    bucket_writer = ReadWriterCSVHandler(filename=FILENAME,
                                         bucket_name=BUCKET_NAME)
    #bucket_writer.upload_dataframe_to_gcs()
    bucket_writer.read_df_from_bucket()

    print(bucket_writer.df)
