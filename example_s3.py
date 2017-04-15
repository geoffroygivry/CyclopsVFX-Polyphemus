import boto3
from botocore.client import Config

import cyc_config as cfg

data = open('geoffroy.jpg', 'rb')

s3 = boto3.resource(
    's3',
    aws_access_key_id=cfg.ACCESS_KEY_ID,
    aws_secret_access_key=cfg.ACCESS_SECRET_KEY,
    config=Config(signature_version='s3v4')
)
s3.Bucket(cfg.BUCKET_NAME).put_object(Key='geoff.jpg', Body=data)

print "Done"
