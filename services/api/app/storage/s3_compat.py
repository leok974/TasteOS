import io
from dataclasses import dataclass
from typing import Optional

import boto3

from ..settings import settings


@dataclass
class PutResult:
    key: str
    public_url: str


class S3CompatStore:
    def __init__(
        self,
        endpoint_url: str,
        region_name: str,
        access_key_id: str,
        secret_access_key: str,
        bucket: str,
        public_base_url: str,
    ):
        self.bucket = bucket
        self.public_base_url = public_base_url.rstrip("/")
        self.s3 = boto3.client(
            service_name="s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )

    def put_bytes(self, *, key: str, content_type: str, data: bytes) -> PutResult:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=io.BytesIO(data), ContentType=content_type)
        return PutResult(key=key, public_url=f"{self.public_base_url}/{key}")

    def healthcheck(self) -> bool:
        # lightweight call; will raise if creds/endpoint wrong
        self.s3.list_objects_v2(Bucket=self.bucket, MaxKeys=1)
        return True


def get_store() -> S3CompatStore:
    return S3CompatStore(
        endpoint_url=settings.object_store_endpoint,
        region_name=settings.object_store_region,
        access_key_id=settings.object_store_access_key_id,
        secret_access_key=settings.object_store_secret_access_key,
        bucket=settings.object_store_bucket,
        public_base_url=settings.object_public_base_url,
    )
