# aws-scripts

## About

Only a bunch of useful scripts to ease my daily aws tasks. Wrote in python in order to maintain and improve python
skills.

## ec2-to-r53

For importing all ec2 instance name (from name tag) as r53 record.

```
usage: ec2-to-r53.py [-h] [--dry-run] [--profile PROFILE] --zone ZONE {create,upsert}

A script which reads all ec2 names from an account and inserts an IN record with instance name and private IP in a zone in the same account.

positional arguments:
  {create,upsert}    Choose one of: create, update.

optional arguments:
  -h, --help         show this help message and exit
  --dry-run          Dry run. No changes applied.
  --profile PROFILE  AWS cli profile.
  --zone ZONE        Route 53 zone name or ZoneId
```