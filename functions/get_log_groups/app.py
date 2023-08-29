import os
import boto3

sts_client = boto3.client('sts')

ORG_ACCOUNT_ID = os.environ['ORG_ACCOUNT_ID']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']


def lambda_handler(data, _context):

    print(data)

    account_id = data['Account']
    region = data['Region']

    client = get_appropriate_client(
        'logs', account_id, region, CROSS_ACCOUNT_ROLE)

    response = client.describe_log_groups()

    return response['logGroups']


def get_appropriate_client(client_type, account_id, region, role=CROSS_ACCOUNT_ROLE):
    if account_id == ORG_ACCOUNT_ID:
        return boto3.client(client_type, region_name=region)
    return get_client(client_type, account_id, region, role)


def get_client(client_type, account_id, region, role=CROSS_ACCOUNT_ROLE):
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"cross_acct_lambda_session_{account_id}"
    )
    access_key = other_session['Credentials']['AccessKeyId']
    secret_key = other_session['Credentials']['SecretAccessKey']
    session_token = other_session['Credentials']['SessionToken']
    return boto3.client(
        client_type,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name=region
    )
