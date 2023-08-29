import os
import boto3

sts_client = boto3.client('sts')

ORG_ACCOUNT_ID = os.environ['ORG_ACCOUNT_ID']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']


def lambda_handler(data, _context):

    account_id = data['Account']
    region = data['Region']
    log_groups = data['LogGroups']

    if log_groups == []:
        return True

    print(data)

    client = get_appropriate_client('logs', account_id, region,
                                    CROSS_ACCOUNT_ROLE)

    for log_group in log_groups:
        process_log_group(client, log_group)

    return True


def process_log_group(client, log_group):
    if 'retentionInDays' in log_group:
        return
    log_group_name = log_group['logGroupName']
    try:
        client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=14
        )
    except Exception as e:
        print(f"Error in updating log group '{log_group_name}': {e}")
        return
    print(f"Updated log group '{log_group_name}' to retain data for 14 days")


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
