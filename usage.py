import os
import sys
import boto3

REGIONS = ["fra1", "ams3"]
ACCESS_KEY = os.getenv("DO_SPACES_KEY")
SECRET_KEY = os.getenv("DO_SPACES_SECRET")

if not ACCESS_KEY or not SECRET_KEY:
    print("Error: Missing credentials. Please run this script using the 1Password CLI ('op run').", file=sys.stderr)
    sys.exit(1)

def get_spaces_usage(region):
    session = boto3.session.Session()
    client = session.client(
        's3',
        region_name=region,
        endpoint_url=f'https://{region}.digitaloceanspaces.com',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    try:
        response = client.list_buckets()
        spaces = response.get('Buckets', [])

        for space in spaces:
            space_name = space['Name']
            total_size_bytes = 0
            object_count = 0

            paginator = client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=space_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size_bytes += obj['Size']
                        object_count += 1

            size_gb = total_size_bytes / (1024 ** 3)
            if size_gb < 0.1:
                size_str = f"{total_size_bytes / (1024 ** 2):.2f} MB"
            else:
                size_str = f"{size_gb:.2f} GB"

            print(f"| {region:<10} | {space_name:<30} | {size_str:<12} | {object_count:<12} |")

    except Exception as e:
        print(f"| {region:<10} | Error connecting to region: {str(e)[:45]:<30} | {'-':<12} | {'-':<12} |")


if __name__ == "__main__":
    print(f"\n| {'Region':<10} | {'Space Name':<30} | {'Total Size':<12} | {'Object Count':<12} |")
    print("|" + "-" * 75 + "|")

    for region in REGIONS:
        get_spaces_usage(region)
