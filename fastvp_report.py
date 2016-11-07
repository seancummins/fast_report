#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fastvp_report.py - Reports per-device Symmetrix FASTVP policies & associations, capacity, and binding information

Requirements:
- Python 3.x
- EMC Solutions Enabler
- SYMCLI bin directory in PATH

"""

import argparse
import subprocess
import sys
from collections import OrderedDict
try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
sys.path.append('/opt/emc/SYMCLI/bin')


def symcli_gentree(command):
    command += ' -output xml_e'
    result = ET.fromstring(subprocess.check_output(command, shell=True))
    return result


def matrix_to_string(matrix, header=None):
    # Stolen from http://mybravenewworld.wordpress.com/2010/09/19/print-tabular-data-nicely-using-python/
    """
    Return a pretty, aligned string representation of a nxm matrix.

    This representation can be used to print any tabular data, such as
    database results. It works by scanning the lengths of each element
    in each column, and determining the format string dynamically.

    @param matrix: Matrix representation (list with n rows of m elements).
    @param header: Optional tuple or list with header elements to be displayed.
    """
    if type(header) is list:
        header = tuple(header)
    lengths = []
    if header:
        for column in header:
            lengths.append(len(column))
    for row in matrix:
        for column in row:
            i = row.index(column)
            column = str(column)
            cl = len(column)
            try:
                ml = lengths[i]
                if cl > ml:
                    lengths[i] = cl
            except IndexError:
                lengths.append(cl)

    lengths = tuple(lengths)
    format_string = ""
    for length in lengths:
        format_string += "%-" + str(length) + "s   "
    format_string += "\n"

    matrix_str = ""
    if header:
        matrix_str += format_string % header
    for row in matrix:
        matrix_str += format_string % tuple(row)

    return matrix_str


### Define and Parse CLI arguments
parser = argparse.ArgumentParser(description='Reports FASTVP information per Symmetrix Device.')
rflags = parser.add_argument_group('Required arguments')
rflags.add_argument('-sid',      required=True, help='Symmetrix serial number')
sflags = parser.add_argument_group('Additional optional arguments')
sflags.add_argument('-showallsgs',         help='Flag; Shows all Storage Groups (not just FASTVP SGs)', action="store_true")
sflags.add_argument('-csv',                help='Flag; Outputs in CSV format', action="store_true")
sflags.add_argument('-quotedcsv',          help='Flag; Outputs in quoted CSV format', action="store_true")
args = parser.parse_args()
if args.csv and args.quotedcsv:
    print('Syntax Error: Flags -csv and -quotedcsv are mutually exlusive; please choose one or the other.')
    exit(1)


### Capture TDEV, FASTVP, and SG information into ET Trees
tdevtree = symcli_gentree('symcfg -sid %s list -tdev -gb -detail' % args.sid)
fasttree = symcli_gentree('symfast -sid %s list -assoc' % args.sid)
fastptree = symcli_gentree('symfast -sid %s list -fp -vp -v' % args.sid)
sgtree = symcli_gentree('symsg -sid %s list -v' % args.sid)
pooltree = symcli_gentree('symcfg -sid %s list -thin -pool -detail -gb' % args.sid)

### Put FASTVP Associations into dictionary
fastAssoc = dict()
fastdata = dict()
for elem in fasttree.iterfind('Symmetrix/Fast_Association/Association_Info'):
    sg_name = elem.find('sg_name').text
    policy_name = elem.find('policy_name').text
    fastAssoc[sg_name] = policy_name

for elem in fastptree.iterfind('Symmetrix/Fast_Policy'):
    policy = 'EFD/FC/SATA'
    policyName = elem.find('Policy_Info/policy_name').text
    for tier in elem.iterfind('Tier'):
        tierTech = tier.find('tier_tech').text
        tierPct = tier.find('tier_max_sg_per').text
        policy = policy.replace(tierTech, tierPct, 1)
    policy = policy.replace("EFD", '0', 1)
    policy = policy.replace("FC", '0', 1)
    policy = policy.replace("SATA", '0', 1)
    fastdata[policyName] = policy

### Put Pool tech type into dictionary
poolTech = dict()
for elem in pooltree.iterfind('Symmetrix/DevicePool'):
    poolName = elem.find('pool_name').text
    techType = elem.find('technology').text
    poolTech[poolName] = techType

# List of all pools
allPools = list()

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

# Iterate through all TDEVs, capturing capacity information
for elem in tdevtree.iterfind('Symmetrix/ThinDevs/Device'):
    dev_name = elem.find('dev_name').text
    totalGB = float(elem.find('total_tracks_gb').text)
#    writtenGB = float(elem.find('written_tracks_gb').text)
    totalAllocGB = float(elem.find('alloc_tracks_gb').text)

    # Create data structure skeleton before we start populating it with values
    if dev_name not in tdevdata:
        tdevdata[dev_name] = dict()
        tdevdata[dev_name]['allocGB'] = dict()
        tdevdata[dev_name]['sgs'] = list()

    tdevdata[dev_name]['totalGB'] = totalGB
#    tdevdata[dev_name]['writtenGB'] = writtenGB
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
                    fastdata["<NotFound>"] = "<NotFound>"
        else:
            # We've encountered a device in an SG that no longer exists; ignore it.
            pass


# Reorder allPools list by techType defined in poolTech
efdPools = list()
fcPools = list()
sataPools = list()
otherPools = list()
for pool in allPools:
    if poolTech[pool] == "EFD":
        efdPools.append(pool)
    elif poolTech[pool] == "FC":
        fcPools.append(pool)
    elif poolTech[pool] == "SATA":
        sataPools.append(pool)
    else:
        otherPools.append(pool)
efdPools.sort()
fcPools.sort()
sataPools.sort()
otherPools.sort()
allPools = efdPools + fcPools + sataPools + otherPools

# Build the report table
report = list()

if args.showallsgs:
    header = ['TDEV', 'TotalGB', 'AllocGB', 'SGs', 'BoundPool', 'FastSG', 'FastPolicy', 'Policy%'] + allPools
else:
    header = ['TDEV', 'TotalGB', 'AllocGB', 'BoundPool', 'FastSG', 'FastPolicy', 'Policy%'] + allPools

for tdev in tdevdata:
    totalGB = tdevdata[tdev]['totalGB']
    allocGB = tdevdata[tdev]['totalAllocGB']

    if 'sgs' in tdevdata[tdev]:
        sgs = " ".join(tdevdata[tdev]['sgs'])
    else:
        sgs = ""

    if 'bound_pool' in tdevdata[tdev]:
        bound_pool = tdevdata[tdev]['bound_pool']
    else:
        bound_pool = ""

    if 'fastsg' in tdevdata[tdev]:
        fastsg = tdevdata[tdev]['fastsg']
    else:
        fastsg = ""

    if 'fastpolicy' in tdevdata[tdev]:
        fastpolicy = tdevdata[tdev]['fastpolicy']
        tierpct = fastdata[fastpolicy]
    else:
        fastpolicy = ""
        tierpct = ""

    allPoolsGB = list()
    for pool in allPools:
        if pool in tdevdata[tdev]['allocGB']:
            poolGB = tdevdata[tdev]['allocGB'][pool]
        else:
            poolGB = 0
        allPoolsGB.append(poolGB)

    row = list()
    if args.showallsgs:
        row = [tdev, totalGB, totalAllocGB, sgs, bound_pool, fastsg, fastpolicy, tierpct] + allPoolsGB
    else:
        row = [tdev, totalGB, totalAllocGB, bound_pool, fastsg, fastpolicy, tierpct] + allPoolsGB

    report.append(row)

if args.csv:
    print(','.join(header))
    for row in report:
        print(','.join(str(x) for x in row))
elif args.quotedcsv:
    print('"' + '","'.join(header) + '"')
    for row in report:
        print('"' + '","'.join(str(x) for x in row) + '"')
else:
    print(matrix_to_string(report, header))
