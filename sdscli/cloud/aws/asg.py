from future import standard_library
standard_library.install_aliases()
import os
import re
import json
import base64
import boto3
from pprint import pformat
from collections import OrderedDict
from operator import itemgetter

from prompt_toolkit.shortcuts import prompt, print_tokens
from prompt_toolkit.styles import style_from_dict
from prompt_toolkit.validation import Validator, ValidationError
from pygments.token import Token

from sdscli.log_utils import logger
from sdscli.conf_utils import get_user_config_path, get_user_files_path, SettingsConf
from sdscli.os_utils import validate_dir
from sdscli.prompt_utils import (YesNoValidator, SelectionValidator,
                                 MultipleSelectionValidator, Ec2InstanceTypeValidator, PriceValidator, highlight,
                                 print_component_header)
from .utils import *


prompt_style = style_from_dict({
    Token.Alert: 'bg:#D8060C',
    Token.Username: '#D8060C',
    Token.Param: '#3CFF33',
})


@cloud_config_check
def ls(args, conf):
    """List all Autoscaling groups."""

    for asg in get_asgs():
        print(asg['AutoScalingGroupName'])


def prompt_image(images):
    """Prompt for image to use."""

    ids = list(images.keys())
    pt = [(Token, "Current verdi AMIs are:\n\n")]
    for i, x in enumerate(ids):
        pt.append((Token.Param, f"{i}"))
        pt.append(
            (Token, ". {} - {} ({})\n".format(images[x]['Name'], x, images[x]['CreationDate'])))
    pt.append((Token, "\nSelect verdi AMI to use for launch configurations: "))
    while True:
        sel = int(prompt(get_prompt_tokens=lambda x: pt, style=prompt_style,
                         validator=SelectionValidator()).strip())
        try:
            return ids[sel]
        except IndexError:
            print(f"Invalid selection: {sel}")


def prompt_keypair(keypairs):
    """Prompt for key pair to use."""

    ids = list(keypairs.keys())
    pt = [(Token, "Current key pairs are:\n\n")]
    for i, x in enumerate(ids):
        pt.append((Token.Param, f"{i}"))
        pt.append((Token, f". {x}\n"))
    pt.append((Token, "\nSelect key pair to use for launch configurations: "))
    while True:
        sel = int(prompt(get_prompt_tokens=lambda x: pt, style=prompt_style,
                         validator=SelectionValidator()).strip())
        try:
            return ids[sel]
        except IndexError:
            print(f"Invalid selection: {sel}")


def prompt_roles(roles):
    """Prompt for role to use."""

    ids = list(roles.keys())
    pt = [(Token, "Current roles are:\n\n")]
    for i, x in enumerate(ids):
        pt.append((Token.Param, f"{i}"))
        pt.append((Token, f". {x}\n"))
    pt.append((Token, "\nSelect role to use for launch configurations: "))
    while True:
        sel = int(prompt(get_prompt_tokens=lambda x: pt, style=prompt_style,
                         validator=SelectionValidator()).strip())
        try:
            return ids[sel]
        except IndexError:
            print(f"Invalid selection: {sel}")


def prompt_secgroup(sgs, desc=None):
    """Prompt for security groups to use."""

    if desc is None:
        desc = "\nSelect security groups to use for launch configurations (space between each selected): "
    ids = list(sgs.keys())
    pt = [(Token, "Current security groups are:\n\n")]
    for i, x in enumerate(ids):
        pt.append((Token.Param, f"{i}"))
        pt.append(
            (Token, ". {} - {} - {}\n".format(sgs[x]['VpcId'], sgs[x]['GroupName'], x)))
    pt.append((Token, desc))
    while True:
        sels = list(map(int, [i.strip() for i in prompt(get_prompt_tokens=lambda x: pt, style=prompt_style,
                                                        validator=MultipleSelectionValidator()).split()]))
        sgs_ids = set()
        vpc_ids = set()
        invalid = False
        for sel in sels:
            try:
                sgs_ids.add(ids[sel])
                vpc_ids.add(sgs[ids[sel]]['VpcId'])
            except IndexError:
                print(f"Invalid selection: {sel}")
                invalid = True
                break
        if invalid:
            continue
        if len(vpc_ids) > 1:
            print("Invalid selections. Security groups from multiple VPC IDs selected: {}".format(
                list(vpc_ids)))
            continue
        return list(sgs_ids), list(vpc_ids)[0]


@cloud_config_check
def create(args, conf):
    """Create Autoscaling group."""

    # get autoscaling conf
    asg_cfg = conf._cfg.get('ASG', {})

    # get clients
    c = boto3.client('autoscaling')
    ec2 = boto3.client('ec2')

    # get current autoscaling groups
    cur_asgs = {i['AutoScalingGroupName']: i for i in get_asgs(c)}
    logger.debug(f"cur_asgs: {pformat(cur_asgs)}")

    # get current key pairs
    cur_keypairs = {i['KeyName']: i for i in get_keypairs(ec2)}
    logger.debug(f"cur_keypairs: {pformat(cur_keypairs)}")

    # get roles
    cur_roles = {i['RoleName']: i for i in get_roles()}
    logger.debug(f"cur_roles: {pformat(cur_roles)}")

    # get current AMIs
    verdi_re = re.compile(r'(?:verdi|autoscale)', re.IGNORECASE)
    cur_images = OrderedDict([(i['ImageId'], i) for i in
                              [x for x in sorted(get_images(c=ec2, Filters=[{'Name': 'is-public', 'Values': ['false']}]),
                                                 key=itemgetter('CreationDate')) if verdi_re.search(x['Name'])]
                              ])
    logger.debug(f"cur_images: {json.dumps(cur_images, indent=2)}")
    logger.debug(f"cur_images.keys(): {list(cur_images.keys())}")

    # get current security groups
    cur_sgs = {i['GroupId']: i for i in get_sgs(ec2)}
    logger.debug(f"cur_sgs: {pformat(cur_sgs)}")

    # prompt for verdi AMI
    if 'AMI' in asg_cfg:
        ami = asg_cfg['AMI']
    else:
        ami = prompt_image(cur_images)
    logger.debug(f"AMI ID: {ami}")

    # prompt for key pair
    if 'KEYPAIR' in asg_cfg:
        keypair = asg_cfg['KEYPAIR']
    else:
        keypair = prompt_keypair(cur_keypairs)
    logger.debug(f"key pair: {keypair}")

    # prompt for roles
    use_role = False
    if 'USE_ROLE' in asg_cfg:
        use_role = asg_cfg['USE_ROLE']
    else:
        use_role = prompt(get_prompt_tokens=lambda x: [(Token, "Do you want to use instance roles [y/n]: ")],
                          validator=YesNoValidator(), style=prompt_style).strip() == 'y'
    logger.debug(f"use_role: {use_role} {type(use_role)}")
    if use_role:
        if 'ROLE' in asg_cfg:
            role = asg_cfg['ROLE']
        else:
            role = prompt_roles(cur_roles)
        logger.debug(f"role: {role}")

    # prompt for security groups
    if 'SECURITY_GROUPS' in asg_cfg and 'VPC' in asg_cfg:
        sgs = asg_cfg.get('SECURITY_GROUPS', [])
        vpc_id = asg_cfg.get('VPC', None)
    else:
        sgs, vpc_id = prompt_secgroup(cur_sgs)
    logger.debug(f"security groups: {sgs}")
    logger.debug(f"VPC ID: {vpc_id}")

    # get current AZs
    cur_azs = {i['ZoneName']: i for i in get_azs(ec2)}
    logger.debug(f"cur_azs: {pformat(cur_azs)}")

    # get subnet IDs and corresponding AZs for VPC
    subnets = []
    azs = set()
    for sn in get_subnets_by_vpc(vpc_id):
        sn_id = sn.subnet_id
        sn_az = sn.availability_zone
        if cur_azs[sn_az]['State'] == 'available':
            subnets.append(sn_id)
            azs.add(sn_az)
    azs = list(azs)
    logger.debug(f"subnets: {pformat(subnets)}")
    logger.debug(f"azs: {pformat(azs)}")


    # check asgs that need to be configured
    queues = conf._cfg.get('QUEUES', [])
    if len(queues) == 0:
        queue_names = prompt(
            'Please enter queue names, separate by space, for example: [job_worker-small job_worker-large]: ',
            default='job_worker-small job_worker-large')
        q_list = queue_names.split()
        for i in range(len(q_list)):
            inst = prompt('Please enter instance names, separate by space, for ' + q_list[
                i] + ', for example: [t2.medium t3.medium t3a.medium]: ', default='t2.medium t3.medium t3a.medium')
            i_list = inst.split()
            d = {'QUEUE_NAME': q_list[i], 'INSTANCE_TYPES': i_list}
            use_job_total = prompt(get_prompt_tokens=lambda x: [(Token, "Do you want to scale up based on total jobs to workers? (default is number of waiting jobs to workers) [y/n]: ")],
                          validator=YesNoValidator(), style=prompt_style).strip() == 'y'
            if use_job_total:
                d['TOTAL_JOBS_METRIC'] = True
            queues.append(d)
            logger.debug(str(queues))
    for i, q in enumerate(queues):
        queue = q['QUEUE_NAME']
        ins_type = q['INSTANCE_TYPES']
        total_jobs_metric = q.get('TOTAL_JOBS_METRIC', False)
        inst_type_arr = []
        for j in range(len(ins_type)):
            inst_type_arr.append({'InstanceType':ins_type[j]})
        #used as parameter in Overrides
        overrides = inst_type_arr

        asg = "{}-{}".format(conf.get('VENUE'), queue)
        if asg in cur_asgs:
            print(f"ASG {asg} already exists. Skipping.")
            continue

        print_component_header(
            f"Configuring autoscaling group:\n{asg}")

        # get user data
        user_data = "BUNDLE_URL=s3://{}/{}-{}.tbz2".format(conf.get('CODE_BUCKET'),
                                                           queue, conf.get('VENUE'))

        # get block device mappings and remove encrypteed flag for spot to fire up
        bd_maps = cur_images[ami]['BlockDeviceMappings']
        for bd_map in bd_maps:
            if 'Ebs' in bd_map and 'Encrypted' in bd_map['Ebs']:
                del bd_map['Ebs']['Encrypted']

        # get launch template
        lt_args = {
            'LaunchTemplateData': {
                'ImageId': ami,
                'KeyName': keypair,
                'SecurityGroupIds': sgs,
                'UserData': base64.b64encode(user_data.encode()).decode(),
                'BlockDeviceMappings': bd_maps,
            }
        }
        if use_role:
            lt_args['LaunchTemplateData']['IamInstanceProfile'] = { 'Name': role }

        lt = f"{asg}-launch-template"
        lt_args['LaunchTemplateName'] = lt
        lt_info = create_lt(ec2, **lt_args)
        logger.debug("Launch template {}: {}".format(
            lt, pformat(lt_info)))
        print(f"Created launch template {lt}.")

        # get autoscaling group config
        asg_args = {
            'AutoScalingGroupName': asg,
            'MixedInstancesPolicy': {
                'LaunchTemplate': {
                    'LaunchTemplateSpecification': {
                        'LaunchTemplateName': lt,
                        'Version': '$Latest'
                    },
                    'Overrides': overrides
             },
                'InstancesDistribution': {
                    'OnDemandAllocationStrategy': 'prioritized',
                    'OnDemandBaseCapacity': 0,
                    'OnDemandPercentageAboveBaseCapacity': 0,
                    'SpotAllocationStrategy': 'lowest-price',
                    'SpotInstancePools': len(ins_type),
                    'SpotMaxPrice': ''
                }
            },
            'MinSize': 0,
            'MaxSize': 0,
            'DefaultCooldown': 60,
            'DesiredCapacity': 0,
            'HealthCheckType': 'EC2',
            'HealthCheckGracePeriod': 300,
            'NewInstancesProtectedFromScaleIn': False,
            'AvailabilityZones': azs,
            'VPCZoneIdentifier': ",".join(subnets),
            'Tags': [
                {
                    'Key': 'Name',
                    'Value': f'{asg}-worker',
                    'PropagateAtLaunch': True,
                },
                {
                    'Key': 'Venue',
                    'Value': conf.get('VENUE'),
                    'PropagateAtLaunch': True,
                },
                {
                    'Key': 'Queue',
                    'Value': queue,
                    'PropagateAtLaunch': True,
                },
                {
                    'Key': 'Bravo',
                    'Value': 'pcm',
                    'PropagateAtLaunch': True,
                },
            ],
        }
        logger.debug(f"asg_args: {pformat(asg_args)}")
        asg_info = create_asg(c, **asg_args)
        logger.debug(f"Autoscaling group {asg}: {pformat(asg_info)}")
        print(f"Created autoscaling group {asg}")

        # add target tracking scaling policy
        policy_name = f"{asg}-target-tracking"
        if total_jobs_metric:
            metric_name = f"JobsPerInstance-{asg}"
        else:
            metric_name = f"JobsWaitingPerInstance-{asg}"
        ttsp_args = {
            'AutoScalingGroupName': asg,
            'PolicyName': policy_name,
            'PolicyType': 'TargetTrackingScaling',
            'TargetTrackingConfiguration': {
                'CustomizedMetricSpecification': {
                    'MetricName': metric_name,
                    'Namespace': 'HySDS',
                    'Dimensions': [
                        {
                            'Name': 'AutoScalingGroupName',
                            'Value': asg,
                        },
                        {
                            'Name': 'Queue',
                            'Value': queue,
                        }
                    ],
                    'Statistic': 'Maximum'
                },
                'TargetValue': 1.0,
                'DisableScaleIn': True
            },
        }
        logger.debug(f"ttsp_args: {pformat(ttsp_args)}")
        ttsp_info = c.put_scaling_policy(**ttsp_args)
        logger.debug("Target tracking scaling policy {}: {}".format(
            policy_name, pformat(ttsp_info)))
        print(f"Added target tracking scaling policy {policy_name} to {asg}")
