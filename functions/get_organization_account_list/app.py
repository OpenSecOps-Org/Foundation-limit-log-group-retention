import boto3
from aws_errors import transient_aws_errors

client = boto3.client('organizations')


@transient_aws_errors
def lambda_handler(_data, _context):

    paginator = client.get_paginator('list_accounts')
    account_iterator = paginator.paginate()

    result = []
    for accounts in account_iterator:
        for account in accounts['Accounts']:
            tidied = account.copy()
            tidied.pop('JoinedTimestamp')
            result.append(tidied)

    return result
