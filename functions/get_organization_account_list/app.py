import boto3

client = boto3.client('organizations')


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
