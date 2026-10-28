"""
The four Lambdas: throttling and other transient AWS errors leave them as AWSTransientError, which the state
machine retries. Other errors keep their own name and are not retried, except in process_log_groups, where
a log group that cannot be updated for another reason is logged and the others are still processed.
"""

import json
from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from aws_errors import AWSTransientError
from functions.get_log_groups import app as get_log_groups
from functions.get_organization_account_list import app as get_organization_account_list
from functions.get_regions import app as get_regions
from functions.process_log_groups import app as process_log_groups

MEMBER = '222222222222'


def client_error(code, status=400):
    return botocore.exceptions.ClientError(
        {'Error': {'Code': code, 'Message': code}, 'ResponseMetadata': {'HTTPStatusCode': status}}, 'op')


THROTTLE = client_error('ThrottlingException')
DENIED = client_error('AccessDeniedException', 403)


def sts():
    s = MagicMock()
    s.assume_role.return_value = {'Credentials': {'AccessKeyId': 'a', 'SecretAccessKey': 'b', 'SessionToken': 'c'}}
    return s


def run(module, data, client):
    with patch.object(module, 'sts_client', sts()), patch.object(module.boto3, 'client', return_value=client):
        return module.lambda_handler(data, None)


# ---------------------------------------------------------------------------

def org_client(error=None):
    client = MagicMock()
    pages = client.get_paginator.return_value.paginate
    if error:
        pages.side_effect = error
    else:
        pages.return_value = [{'Accounts': [{'Id': MEMBER, 'Status': 'ACTIVE', 'JoinedTimestamp': 'x'}]}]
    return client


def test_lists_the_accounts():
    with patch.object(get_organization_account_list, 'client', org_client()):
        assert get_organization_account_list.lambda_handler({}, None) == [{'Id': MEMBER, 'Status': 'ACTIVE'}]


def test_a_throttled_account_listing_is_retried():
    with patch.object(get_organization_account_list, 'client', org_client(client_error('TooManyRequestsException'))):
        with pytest.raises(AWSTransientError):
            get_organization_account_list.lambda_handler({}, None)


def test_a_refused_account_listing_keeps_its_own_name():
    with patch.object(get_organization_account_list, 'client', org_client(DENIED)):
        with pytest.raises(botocore.exceptions.ClientError) as raised:
            get_organization_account_list.lambda_handler({}, None)
    assert not isinstance(raised.value, AWSTransientError)


# ---------------------------------------------------------------------------

@pytest.mark.parametrize('error, expected', [(THROTTLE, AWSTransientError),
                                             (DENIED, botocore.exceptions.ClientError)])
def test_get_regions_errors(error, expected):
    ec2 = MagicMock()
    ec2.describe_regions.side_effect = error
    with pytest.raises(expected) as raised:
        run(get_regions, {'Account': {'Id': MEMBER}}, ec2)
    assert isinstance(raised.value, AWSTransientError) == (expected is AWSTransientError)


def log_groups_client(*pages):
    logs = MagicMock()
    logs.get_paginator.return_value.paginate.return_value = [{'logGroups': page} for page in pages]
    return logs


def test_get_log_groups_reads_every_page_and_returns_the_names_without_retention():
    logs = log_groups_client([{'logGroupName': 'a', 'storedBytes': 1}, {'logGroupName': 'b', 'retentionInDays': 30}],
                             [{'logGroupName': 'c', 'arn': 'arn:c'}])
    assert run(get_log_groups, {'Account': MEMBER, 'Region': 'eu-north-1'}, logs) == [
        {'logGroupName': 'a'}, {'logGroupName': 'c'}]
    logs.get_paginator.assert_called_once_with('describe_log_groups')


def test_get_log_groups_stays_within_the_state_machine_payload_limit(capsys):
    """Long names: the rest is picked up by the next daily run."""
    names = [f'{i:04d}' + 'x' * 500 for i in range(1000)]
    logs = log_groups_client([{'logGroupName': name} for name in names])
    result = run(get_log_groups, {'Account': MEMBER, 'Region': 'eu-north-1'}, logs)
    assert len(json.dumps(result)) <= get_log_groups.PAYLOAD_BUDGET
    assert 0 < len(result) < len(names)
    assert result == [{'logGroupName': name} for name in names[:len(result)]]
    assert 'next run' in capsys.readouterr().out


@pytest.mark.parametrize('error, expected', [(THROTTLE, AWSTransientError),
                                             (DENIED, botocore.exceptions.ClientError)])
def test_get_log_groups_errors(error, expected):
    logs = MagicMock()
    logs.get_paginator.return_value.paginate.side_effect = error
    with pytest.raises(expected) as raised:
        run(get_log_groups, {'Account': MEMBER, 'Region': 'eu-north-1'}, logs)
    assert isinstance(raised.value, AWSTransientError) == (expected is AWSTransientError)


def test_a_throttled_role_assumption_is_retried():
    throttled = MagicMock()
    throttled.assume_role.side_effect = client_error('Throttling')
    with patch.object(get_log_groups, 'sts_client', throttled):
        with pytest.raises(AWSTransientError):
            get_log_groups.lambda_handler({'Account': MEMBER, 'Region': 'eu-north-1'}, None)


# ---------------------------------------------------------------------------

LOG_GROUPS = [{'logGroupName': 'a'}, {'logGroupName': 'b', 'retentionInDays': 30}, {'logGroupName': 'c'}]


def process(logs):
    return run(process_log_groups, {'Account': MEMBER, 'Region': 'eu-north-1', 'LogGroups': LOG_GROUPS}, logs)


def test_sets_14_days_on_log_groups_without_retention():
    logs = MagicMock()
    assert process(logs) is True
    assert [c.kwargs for c in logs.put_retention_policy.call_args_list] == [
        {'logGroupName': 'a', 'retentionInDays': 14}, {'logGroupName': 'c', 'retentionInDays': 14}]


@pytest.mark.parametrize('error', [THROTTLE, client_error('ServiceUnavailableException', 503)])
def test_a_throttled_update_is_retried(error):
    logs = MagicMock()
    logs.put_retention_policy.side_effect = error
    with pytest.raises(AWSTransientError):
        process(logs)


def test_a_log_group_refused_for_another_reason_is_logged_and_the_others_processed(capsys):
    logs = MagicMock()
    logs.put_retention_policy.side_effect = [client_error('OperationAbortedException'), None]
    assert process(logs) is True
    assert logs.put_retention_policy.call_count == 2
    assert 'OperationAbortedException' in capsys.readouterr().out
