#!/usr/bin/env python -u
# -*- coding: utf-8 -*-
"""
fastvp_report.py - Reports per-device Symmetrix FASTVP policies & associations, capacity, and binding information

Requirements:
- Python 2.7.x (haven't tested in 3.x, but it might work)
- EMC Solutions Enabler
- SYMCLI bin directory in PATH

"""

import argparse
import subprocess
from collections import OrderedDict
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

def symcli_gentree(command):
    command += ' -output xml_e'
    result = ET.fromstring(subprocess.check_output(command, shell=True))
    return result


def format_matrix(my_matrix):
    # Stolen from David Robinson (http://stackoverflow.com/a/8747570)
    """
    Return a pretty, aligned string representation of a matrix
    (i.e. -- a 'square' list of lists)
    """
    import string
    max_lens = [max([len(str(r[i])) for r in my_matrix])
                for i in range(len(my_matrix[0]))]

    return "\n".join(["".join([string.ljust(str(e), l + 2)
                     for e, l in zip(r, max_lens)]) for r in my_matrix])

### Define and Parse CLI arguments
parser = argparse.ArgumentParser(description='Reports FASTVP information per Symmetrix Device.')
rflags = parser.add_argument_group('Required arguments')
rflags.add_argument('-sid',      required=True, help='Symmetrix serial number')
oflags = parser.add_argument_group('Additional optional arguments')
oflags.add_argument('-csv',                help='Flag; Outputs in CSV format', action="store_true")
args = parser.parse_args()

### Capture TDEV, FASTVP, and SG information into ET Trees
tdevtree = symcli_gentree('symcfg -sid %s list -tdev -gb -detail' % args.sid)
fasttree = symcli_gentree('symfast -sid %s list -assoc' % args.sid)
fastptree = symcli_gentree('symfast -sid %s list -fp -vp -v' % args.sid)
sgtree = symcli_gentree('symsg -sid %s list -v' % args.sid)
pooltree = symcli_gentree('symcfg -sid %s list -thin -pool -detail -gb' % args.sid)

### Put FASTVP Associations into dictionary
fastAssoc = dict()
for elem in fasttree.iterfind('Symmetrix/Fast_Association/Association_Info'):
    sg_name = elem.find('sg_name').text
    policy_name = elem.find('policy_name').text
    fastAssoc[sg_name] = policy_name

### Put FASTVP Policy tier percentage information into dictionary
fastPolicyPct = dict()
for elem in fastptree.iterfind('Symmetrix/Fast_Policy'):
    policy = 'EFD/FC/SATA'
    policyName = elem.find('Policy_Info/policy_name').text
    for tier in elem.iterfind('Tier'):
        tierTech = tier.find('tier_tech').text
        tierPct = tier.find('tier_max_sg_per').text
        policy = policy.replace(tierTech, tierPct, 1)
    fastPolicyPct[policyName] = policy

### Put Pool tech type into dictionary
poolTech = dict()
for elem in pooltree.iterfind('Symmetrix/DevicePool'):
    poolName = elem.find('pool_name').text
    techType = elem.find('technology').text
    poolTech[poolName] = techType

### Put TDEV information values into data structure
# tdevdata{ 'tdev1' :
#                     { 'totalGB'     : 1024,
#                       'writtenGB'   : 1024,
#                       'totalAllocGB : 1024,
#                       'allocGB      : { 'pool1' : 256,
#                                         'pool2' : 256,
#                                         'pool3' : 512
#                                       }
#                       'sgs'         : ['sg1', 'sg2', 'sg3']
#                       'fastsg'      : 'fast_sgname'
#                       'fastpolicy'  : 'policy_name'
#                       'bound_pool'  : 'pool_name'
#                     }
#         }
tdevdata = OrderedDict()

# List of all pools
allPools = list()

# Iterate through all TDEVs, capturing capacity information
for elem in tdevtree.iterfind('Symmetrix/ThinDevs/Device'):
    dev_name = elem.find('dev_name').text
    totalGB = float(elem.find('total_tracks_gb').text)
    writtenGB = float(elem.find('written_tracks_gb').text)
    totalAllocGB = float(elem.find('alloc_tracks_gb').text)

    # Create data structure skeleton before we start populating it with values
    if dev_name not in tdevdata:
        tdevdata[dev_name] = dict()
        tdevdata[dev_name]['allocGB'] = dict()
        tdevdata[dev_name]['sgs'] = list()

    tdevdata[dev_name]['totalGB'] = totalGB
    tdevdata[dev_name]['writtenGB'] = writtenGB
    tdevdata[dev_name]['totalAllocGB'] = totalAllocGB

    # Get per-pool allocation information and place into data structure
    for elempool in elem.iterfind('pool'):
        pool_name = elempool.find('pool_name').text
        if pool_name not in allPools and pool_name != "N/A":
            allPools.append(pool_name)
        pool_allocGB = float(elempool.find('alloc_tracks_gb').text)
        tdevdata[dev_name]['allocGB'][pool_name] = pool_allocGB
        if elempool.find('tdev_status').text == "Bound":
            tdevdata[dev_name]['bound_pool'] = pool_name

# Iterate through all Storage Groups, capturing membership information and adding SG names to tdevdata
for elem in sgtree.iterfind('SG'):
    sg_name = elem.find('SG_Info/name').text
    for member in elem.iterfind('DEVS_List/Device'):
        dev_name = member.find('dev_name').text
        if dev_name in tdevdata:
            tdevdata[dev_name]['sgs'].append(sg_name)
            if elem.find('SG_Info/FAST_Policy').text == "Yes":
                tdevdata[dev_name]['fastsg'] = sg_name
                try:
                    tdevdata[dev_name]['fastpolicy'] = fastAssoc[sg_name]
                except KeyError:
                    # This seems to be related to SYMAPIDB inconsistencies
                    tdevdata[dev_name]['fastpolicy'] = "<NotFound>"
        else:
            # We've encountered a device in an SG that no longer exists; ignore it.
            pass


# Reorder allPools list by techType defined in poolTech
efdPools, fcPools, sataPools, otherPools = list(), list(), list(), list()
for pool in allPools:
    if poolTech[pool] == "EFD":
        efdPools.append(pool)
    elif poolTech[pool] == "FC":
        fcPools.append(pool)
    elif poolTech[pool] == "SATA":
        sataPools.append(pool)
    else:
        otherPools.append(pool)
# Sort pool lists
for poolList in [efdPools, fcPools, sataPools, otherPools]:
    poolList.sort()
allPools = efdPools + fcPools + sataPools + otherPools

# Build the report table (a 'list of lists' matrix)
report = list()
header = ['TDEV', 'TotalGB', 'WrittenGB', 'BoundPool', 'FastSG', 'FastPolicy', 'Policy%'] + allPools
report.append(header)

for tdev in tdevdata:
    totalGB = tdevdata[tdev]['totalGB']
    writtenGB = tdevdata[tdev]['writtenGB']

    # Reset all values to defaults
    sgs, bound_pool, fastsg, fastpolicy, tierpct = ("",)*5
    poolGB = 0.0
    allPoolsGB = list()

    if 'sgs' in tdevdata[tdev]:
        sgs = " ".join(tdevdata[tdev]['sgs'])
    if 'bound_pool' in tdevdata[tdev]:
        bound_pool = tdevdata[tdev]['bound_pool']
    if 'fastsg' in tdevdata[tdev]:
        fastsg = tdevdata[tdev]['fastsg']
    if 'fastpolicy' in tdevdata[tdev]:
        fastpolicy = tdevdata[tdev]['fastpolicy']
        tierpct = fastPolicyPct[fastpolicy]

    for pool in allPools:
        if pool in tdevdata[tdev]['allocGB']:
            poolGB = tdevdata[tdev]['allocGB'][pool]
        allPoolsGB.append(poolGB)
        poolGB = 0.0

    report.append([tdev, totalGB, writtenGB, bound_pool, fastsg, fastpolicy, tierpct] + allPoolsGB)

if args.csv:
    for row in report:
        print(','.join(str(x) for x in row))
else:
    print(format_matrix(report))