from __future__ import print_function
import sys
import boto3
import botocore
import hashlib
import datetime
import getpass

from MerkleNode import calculate_dir_cksum

dbClient = boto3.client('dynamodb', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3Client = boto3.client('s3', region_name='us-east-1')
s3 = boto3.resource('s3')

def create_fs(namespace):
    # Create a table for metadata merkle tree
    print("Creating table...")
    table = dbClient.create_table(
        TableName=namespace,
        KeySchema=[
            {
                'AttributeName': 'cksum',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'cksum',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )

    # Initialize table with empty root directory hash
    waiter = dbClient.get_waiter('table_exists')
    waiter.wait(TableName=namespace)

    print("Table successfully created")
    fs_table = dynamodb.Table(namespace)
    response = fs_table.put_item(
        Item={
            'cksum': calculate_dir_cksum(['/']),
            'name': '/',
            'prev_version': None
            'next_version': None
            'is_dir': True,
            'dir_info': ['/'],
            'mod_time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'mod_user': getpass.getuser()
        }
    )

    # Create S3 bucket
    bucket_name = 'git-storage-{}-bucket'.format(namespace.lower())
    print("Creating S3 bucket: {} ...".format(bucket_name))
    try:
        response = s3Client.create_bucket(
            Bucket=bucket_name
        )
        bucket_versioning = s3.BucketVersioning(bucket_name)
        bucket_versioning.enable()
        print("S3 bucket created successfully")
    except:
        print("Failed to create S3 bucket")

    # Add fs to root_pointers table
    print("Updating root_pointers table...")
    response = dbClient.put_item(
        TableName='root_pointers',
        Item={
            'name': {
                'S': namespace
            },
            'cksum': {
                'S': calculate_dir_cksum(['/'])
            },
            'bucket_name': {
                'S': bucket_name
            }
        }
    )
    print("{} set up completed".format(namespace))

if __name__ == "__main__":
    namespace = sys.argv[1]

    create_fs(namespace)
