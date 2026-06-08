from google.cloud import storage
from io import StringIO
import pandas as pd
import logging


logger = logging.getLogger(__name__)


class ReadWriterCSVHandler:
    """Handler for reading and writing CSV files from/to Google Cloud Storage."""

    def __init__(self, filename, bucket_name=None, df=None):
        """Initialize the CSV handler.
        
        Args:
            filename: Name of the CSV file
            bucket_name: GCS bucket name (optional)
            df: Pandas DataFrame (optional)
        """
        self.storageClient = storage.Client()
        self.filename = filename
        self.bucket = bucket_name
        self.df = df

    def write_df_to_csv(self):
        """Write dataframe to local CSV file."""
        try:
            path = self.filename
            self.df.to_csv(path)
            logger.info(f"DataFrame written to local file: {path}")
        except Exception as e:
            logger.error(f"Error writing DataFrame to CSV file '{self.filename}': {e}")
            raise

    def read_local_csv(self):
        """Read local CSV file into dataframe."""
        try:
            self.df = pd.read_csv(filepath_or_buffer=self.filename)
            logger.info(f"Local CSV file '{self.filename}' read successfully ({len(self.df)} rows)")
        except FileNotFoundError:
            logger.error(f"Local CSV file '{self.filename}' not found")
            raise
        except Exception as e:
            logger.error(f"Error reading local CSV file '{self.filename}': {e}")
            raise

    def read_df_from_bucket(self):
        """Read CSV file from GCS bucket into dataframe."""
        try:
            bucket = self.storageClient.get_bucket(self.bucket)
            blob = bucket.blob(self.filename)
            content = blob.download_as_text()
            self.df = pd.read_csv(StringIO(content))
            logger.info(f"File '{self.filename}' read from GCS bucket '{self.bucket}' ({len(self.df)} rows)")
        except Exception as e:
            logger.error(f"Error reading file '{self.filename}' from GCS bucket '{self.bucket}': {e}")
            raise

    def upload_dataframe_to_gcs(self):
        """Upload local CSV file to GCS bucket."""
        try:
            bucket = self.storageClient.bucket(self.bucket)
            blob = bucket.blob(self.filename)
            blob.upload_from_filename(self.filename)
            logger.info(f"File '{self.filename}' uploaded to GCS bucket '{self.bucket}'")
        except FileNotFoundError:
            logger.error(f"Local file '{self.filename}' not found for upload")
            raise
        except Exception as e:
            logger.error(f"Error uploading file '{self.filename}' to GCS bucket '{self.bucket}': {e}")
            raise
