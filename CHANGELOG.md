# Change Log

## v1.1.0
    * Converted to OpenSecOps supply-chain framework: hash-pinned dependencies, signed releases, daily CVE scan, Scorecard. See `SECURITY.md`.
    * `boto3` pinned to `1.42.94` (was `1.28.33`) per project-wide pin policy.

## v1.0.11
    * Updated GitHub remote references in publish.zsh script to use only OpenSecOps-Org, removed Delegat-AB

## v1.0.10
    * Updated GitHub organization name from CloudSecOps-Org to OpenSecOps-Org.
    * Updated references to CloudSecOps-Installer to Installer.

## v1.0.9
    * File paths corrected for the new name of the installer.

## v1.0.8
    * Updated LICENSE file to MPL 2.0.

## v1.0.7
    * Updated publish.zsh to support dual-remote publishing to CloudSecOps-Org repositories.

## v1.0.6
    * Upgraded to Python 3.12.
    * Added `.python-version` file for pyenv.

## v1.0.5
    * Corrected the alarm logical name.

## v1.0.4
    * Added SOAR monitoring of the state machine.

## v1.0.3
    * Refreshed deployment scripts.

## v1.0.2
    * Open-source credits and URLs
    * Fixed installer initial stackset creation.

## v1.0.1
    * `--dry-run` and `--verbose` added to `deploy`.

## v1.0.0
    * Initial release.
