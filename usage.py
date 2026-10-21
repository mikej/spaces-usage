import os
import sys
import boto3

BASE_LIMIT_GB = 250.0
OVERAGE_COST_PER_GB = 0.02

REGIONS = ["fra1", "ams3"]
ACCESS_KEY = os.getenv("DO_SPACES_KEY")
SECRET_KEY = os.getenv("DO_SPACES_SECRET")

if not ACCESS_KEY or not SECRET_KEY:
    print("Error: Missing credentials. Please run this script using the 1Password CLI ('op run').", file=sys.stderr)
    sys.exit(1)

# Global trackers for account-wide metrics
account_total_bytes = 0
account_total_objects = 0

def get_spaces_usage(region):
    global account_total_bytes, account_total_objects

    session = boto3.session.Session()
    client = session.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://{region}.digitaloceanspaces.com",
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )

    try:
        response = client.list_buckets()
        spaces = response.get("Buckets", [])

        for space in spaces:
            space_name = space["Name"]
            total_size_bytes = 0
            object_count = 0

            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=space_name):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        total_size_bytes += obj["Size"]
                        object_count += 1

            # Add to aggregate to account totals
            account_total_bytes += total_size_bytes
            account_total_objects += object_count

            size_gb = total_size_bytes / (1024 ** 3)
            if size_gb < 0.1:
                size_str = f"{total_size_bytes / (1024 ** 2):.2f} MB"
            else:
                size_str = f"{size_gb:.2f} GB"

            print(f"| {region:<10} | {space_name:<30} | {size_str:<12} | {object_count:<12} |")

    except Exception as e:
        print(f"| {region:<10} | Error connecting to region: {str(e)[:45]:<30} | {"-":<12} | {"-":<12} |")


if __name__ == "__main__":
    print(f"\n| {"Region":<10} | {"Space Name":<30} | {"Total Size":<12} | {"Object Count":<12} |")
    print("|" + "-" * 75 + "|")

    for region in REGIONS:
        get_spaces_usage(region)

    print("|" + "-" * 75 + "|")

    # Calculate account-wide metrics
    grand_total_gb = account_total_bytes / (1024 ** 3)

    # Format the grand total display string
    if grand_total_gb < 0.1:
        grand_total_str = f"{account_total_bytes / (1024 ** 2):.2f} MB"
    else:
        grand_total_str = f"{grand_total_gb:.2f} GB"

    print(f"| {"ACCOUNT TOTAL":<43} | {grand_total_str:<12} | {account_total_objects:<12} |")
    print("|" + "-" * 75 + "|")

    # Summary
    print(f"\nDigitalOcean Account Summary:")
    print(f" -> Base Storage Limit: {BASE_LIMIT_GB} GB")

    remaining_gb = max(0.0, BASE_LIMIT_GB - grand_total_gb)

    if grand_total_gb > BASE_LIMIT_GB:
        overage_gb = grand_total_gb - BASE_LIMIT_GB
        estimated_overage_cost = overage_gb * OVERAGE_COST_PER_GB
        print(f" -> STATUS: OVER LIMIT (Exceeded by {overage_gb:.2f} GB)")
        print(f" -> Remaining Free Base Capacity: {remaining_gb:.2f} GB")  # Caps at 0.00 GB
        print(f" -> Estimated Storage Overage Cost: ${estimated_overage_cost:.2f}/month (at $0.02/GB)")
    else:
        percent_used = (grand_total_gb / BASE_LIMIT_GB) * 100 if BASE_LIMIT_GB > 0 else 0
        print(f" -> STATUS: WITHIN LIMIT ({percent_used:.1f}% of base allowance used)")
        print(f" -> Remaining Free Base Capacity: {remaining_gb:.2f} GB")  # Shows actual space left
