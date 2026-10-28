import os
import json
import boto3
from aws_errors import transient_aws_errors

sts_client = boto3.client('sts')

ORG_ACCOUNT_ID = os.environ['ORG_ACCOUNT_ID']
CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']

# The list passes through the state machine, whose state data is limited to 256 KB
PAYLOAD_BUDGET = 200_000


@transient_aws_errors
def lambda_handler(data, _context):

    print(data)

    account_id = data['Account']
    region = data['Region']

    client = get_appropriate_client(
        'logs', account_id, region, CROSS_ACCOUNT_ROLE)

    # Only the log groups without a retention setting, and only their names
    result = []
    size = 2
    for page in client.get_paginator('describe_log_groups').paginate():
        for log_group in page['logGroups']:
            if 'retentionInDays' in log_group:
                continue
            entry = {'logGroupName': log_group['logGroupName']}
            size += len(json.dumps(entry)) + 2
            if size > PAYLOAD_BUDGET:
                print(f"{len(result)} log groups this run; the rest will be processed in the next run")
                return result
            result.append(entry)

    return result


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
