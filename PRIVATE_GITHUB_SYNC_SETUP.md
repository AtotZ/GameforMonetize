# Private GitHub Data Sync

Use `upload_data_to_private_github.py` when you want Pythonista to push local data files to a private GitHub repo.

## Token

Create a **fine-grained personal access token** scoped to:

- resource owner: your account
- repository access: only the private data repo
- repository permission: `Contents: write`

That is enough for create/update file contents.

Official GitHub docs:

- PATs: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
- Contents API: https://docs.github.com/en/rest/repos/contents#create-or-update-file-contents

## Local config

1. Copy `github_private_sync_config.example.json`
2. Rename the copy to `github_private_sync_config.json`
3. Fill in:
   - `repo`
   - `token`
   - optional `remote_root`

Do not commit the real config file anywhere public.

## Shortcut

Use one action only:

- `Run Pythonista Script`
  - script: `TestSubjext/upload_data_to_private_github.py`

No input files and no arguments are needed.

## What it uploads

Default targets:

- `TestSubjextData/offers/active_offer.json`
- `TestSubjextData/offers/active_offer_history.jsonl`
- `TestSubjextData/offers/TripLog-OnisAI-PostcodeIsolation-latest.json`
- `TestSubjextData/traffic/TrafficBeacon-latest.json`
- `TestSubjextData/traffic/TrafficBeacon-history.json`
- `TestSubjextData/traffic/TrafficBeacon-db.json`
- `TestSubjextData/traffic/TrafficRoute-db.json`

It also writes a remote `sync_manifest.json` file for quick inspection.
