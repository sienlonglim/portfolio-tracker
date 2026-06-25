import datetime
from io import BytesIO
from typing import Any

import pandas as pd
from dagster import get_dagster_logger
from dagster_aws.s3 import S3Resource


def upload_bytes_to_s3(
    *,
    s3: S3Resource,
    bucket: str,
    key: str,
    body: bytes,
    content_type: str = "application/octet-stream",
    **put_object_kwargs: Any,
) -> None:
    """
    Upload bytes to S3.
    Args:
        s3 (S3Resource): The S3 resource to use for uploading.
        bucket (str): The name of the S3 bucket.
        key (str): The S3 key (path) where the object will be stored.
        body (bytes): The bytes to upload.
        content_type (str): The content type of the object (default: 'application/octet-stream').
        **put_object_kwargs: Additional keyword arguments to pass to the S3 put_object method.
    Returns:
        None"""
    s3.get_client().put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
        **put_object_kwargs,
    )


def upload_parquet_to_s3(
    *,
    s3: S3Resource,
    df: pd.DataFrame,
    bucket: str,
    key: str,
    compression: str = "snappy",
    index: bool = False,
    **put_object_kwargs: Any,
) -> None:
    """
    Upload a Pandas DataFrame to S3 in Parquet format.
    Args:
        s3 (S3Resource): The S3 resource to use for uploading.
        df (pd.DataFrame): The DataFrame to upload.
        bucket (str): The name of the S3 bucket.
        key (str): The S3 key (path) where the Parquet file will be stored.
        compression (str): The compression algorithm to use for Parquet (default: 'snappy').
        index (bool): Whether to include the DataFrame index in the Parquet file (default: False).
        **put_object_kwargs: Additional keyword arguments to pass to the S3 put_object method.
    Returns:
        None
    """
    logger = get_dagster_logger()
    logger.info(f"Uploading parquet file to s3://{bucket}/{key}.")
    buffer = BytesIO()
    df.to_parquet(buffer, index=index, compression=compression)
    buffer.seek(0)

    upload_bytes_to_s3(
        s3=s3,
        bucket=bucket,
        key=key,
        body=buffer.getvalue(),
        content_type="application/octet-stream",
        **put_object_kwargs,
    )


def create_s3_date_directory():
    """
    Create a directory in S3 with the current date as the name.
    Returns:
        str: The S3 path for the current date directory in the format 'year=YYYY/month=MM/day=DD'.
    """
    current_date = datetime.datetime.now(datetime.UTC)
    s3_date_path = f'year={current_date.strftime("%Y")}/month={current_date.strftime("%m")}/day={current_date.strftime("%d")}'
    return s3_date_path
