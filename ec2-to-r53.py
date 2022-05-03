#! /usr/bin/env python3
"""
A script which reads all ec2 names from an account and inserts an IN record with instance name and private IP in a zone
in the same account.
"""

import argparse
import boto3
import pprint
import sys


def get_args():
    """ Parses command line options. """
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("action", action="store", choices=["create", "upsert"], help="Choose one of: create, update.")

    parser.add_argument("--dry-run", action="store_true", help="Dry run. No changes applied.")

    parser.add_argument("--profile", action="store", dest="aws_cli_profile", help="AWS cli profile.",
                        metavar="PROFILE")

    parser.add_argument("--zone", action="store", dest="r53_zone", help="Route 53 zone name or ZoneId", metavar="ZONE",
                        required=True)

    return parser.parse_args()


def get_boto_client(profile, resource_type: str):
    """ Returns boto3 client object. Using default profile or profile set by command line. """
    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()

    return session.client(service_name=resource_type)


def get_ec2(aws_cli_profile, **kargs):
    """ Obtains ec2 info returning a list with name from tag and private ip address. """

    ec2_client = get_boto_client(aws_cli_profile, "ec2")

    # Instance list pagination
    paginator = ec2_client.get_paginator("describe_instances")
    page_iterator = paginator.paginate()

    return_list = []
    for page in page_iterator:
        for instance in [instance['Instances'][0] for instance in page['Reservations']]:
            instance_name = next(item['Value'] for item in instance['Tags'] if item['Key'] == "Name")
            instance_ip = instance['PrivateIpAddress']
            return_list.append({"name": instance_name, "ip": instance_ip})

    return return_list


def r53_check_zone(client, zone):
    """ Checks if zone string is a domain name o a zoneId. Then checks if it exists. """
    # Checking if zone is a domain name or a ZoneId
    if "." in zone:
        response = client.list_hosted_zones_by_name(DNSName=zone, MaxItems="1")
        if ('HostedZones' in response.keys() and len(response['HostedZones']) > 0
                and response['HostedZones'][0]['Name'].startswith(zone)):
            return response['HostedZones'][0]['Id'].split('/')[2]
        else:
            print("Zone {} does not exist".format(zone))
            sys.exit(1)
    else:
        try:
            client.get_hosted_zone(Id=zone)
            return zone
        except client.exceptions.NoSuchHostedZone:
            print("Zone {} does not exist".format(zone))
            sys.exit(1)


def r53_do_action(aws_cli_profile, instance_list, action, dry_run, r53_zone):
    """ Applies R53 operations: create or update records. If dry-runned then only prints out operations, no changes
    applied.
    """

    pp = pprint.PrettyPrinter(indent=2)
    r53_client = get_boto_client(aws_cli_profile, "route53")
    zone_id = r53_check_zone(r53_client, r53_zone)
    changes = [r53_generate_change(r53_action=action, zone=r53_zone, **instance) for instance in instance_list]

    change_batch = {"Comment": "Import from ec2",
                    "Changes": changes}
    if dry_run:
        pp.pprint(change_batch)
    else:
        try:
            r53_client.change_resource_record_sets(HostedZoneId=zone_id, ChangeBatch=change_batch)
        except r53_client.exceptions.NoSuchHostedZone as e:
            print("Problems with zone {}. Check zone name/id.".format(r53_zone))
            pp.pprint(e.response["Error"]["Message"])
            sys.exit(1)
        except r53_client.exceptions.InvalidChangeBatch as e:
            print("Problems with change batch generated. Check it with --dry-run option.")
            pp.pprint(e.response["Error"]["Message"])
            sys.exit(1)
        except Exception as e:
            pp.pprint(e)
            sys.exit(1)
        else:
            print("All records applied.")


def r53_generate_change(r53_action: str, name, ip, zone):
    change = {
        'Action': r53_action.upper(),
        'ResourceRecordSet': {
            'Name': '.'.join([name, zone]) + '.',
            'Type': 'A',
            'TTL': 300,
            'ResourceRecords': [
                {
                    'Value': ip
                }
            ]
        }
    }
    return change


if __name__ == "__main__":
    cmd_args = vars(get_args())

    ec2_list = get_ec2(**cmd_args)

    r53_do_action(instance_list=ec2_list, **cmd_args)
