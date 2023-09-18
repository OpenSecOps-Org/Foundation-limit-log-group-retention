Deploy as a Stack in the Organization account, in the main region.

The template has two parameters:

- <b>OrgAccountId</b> - the account number of the main organisation account
- <b>CrossAccountRole</b> - the role to assume in member accounts. If you're running under AWS Control Tower, use <tt>AWSControlTowerExecution</tt>. If running under AWs Organizations without Control Tower, use <tt>OrganizationAccountAccessRole</tt>.

Logic:

[<img src="docs/flowchart.png">](docs/flowchart.png)

The Step Function state machine is triggered at 00:00 UTC every day. It will retrieve the list of accounts in the organisation, including the root account. Then, it will process each account in parallel, skipping disabled accounts.

For each active account, it will fetch the list of regions to which the account has access (this might vary due to opt-in requirements).

Then, in parallel for each region where opt-in isn't required, it will fetch the list of log groups in that account and region. For each log group without an explicit retention time, it will set retention to 14 days.


## Deployment

First make sure that your SSO setup is configured with a default profile giving you AWSAdministratorAccess
to your AWS Organizations administrative account. This is necessary as the AWS cross-account role used 
during deployment only can be assumed from that account.

```console
aws sso login
```

Then type:

```console
./deploy
```
