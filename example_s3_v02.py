
import boto3
import os

from boto3.s3.transfer import S3Transfer
import cyc_config as cfg

file_path = "static/frontend/assets/images/Cyclops-vfx-suits.jpg"

transfer = S3Transfer(boto3.client('s3', cfg.AWS_REGION, aws_access_key_id=cfg.ACCESS_KEY_ID,
                                   aws_secret_access_key=cfg.ACCESS_SECRET_KEY))

transfer.upload_file(file_path, cfg.BUCKET_NAME, os.path.basename(file_path), extra_args={'ACL': 'public-read'})

print "Done"
