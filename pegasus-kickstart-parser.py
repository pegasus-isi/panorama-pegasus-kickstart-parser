#!/usr/bin/env python
#
# Copyright 2018 University of Southern California
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import collections
import json
import logging
import os
import xml.etree.ElementTree
import fnmatch

__author__ = "Rafael Ferreira da Silva"

logger = logging.getLogger(__name__)


def _configure_logging(debug):
    """
    Configure the application's logging.
    :param debug: whether debugging is enabled
    """
    if debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def _parse_job_output(kickstart_file):
    """
    Parse the kickstart job output file (e.g., .out.000).
    :param kickstart_file: path to kickstart output file
    """
    data = collections.OrderedDict()

    runtime = 0
    cores = 0
    total_time = 0
    maxrss = 0
    utime = 0
    stime = 0
    bytes_read = 0
    bytes_written = 0
    rsspeak = 0
    vmpeak = 0
    iowait = 0
    maxthreads = 0
    args = []
    files = []
    machine = {}

    # clean output file from PBS logs
    line_num = 0
    temp_file = None
    with open(kickstart_file) as f:
        for line in f:
            line_num += 1
            if line.startswith('<?xml'):
                if line_num == 1:
                    break
                else:
                    temp_file = open('.pegasus-parser-tmp', 'w')

            if line.startswith('</invocation>'):
                temp_file.write(line)
                kickstart_file = temp_file.name
                temp_file.close()
                break

            if temp_file:
                temp_file.write(line)

    try:
        e = xml.etree.ElementTree.parse(kickstart_file).getroot()
        # main job information
        transformation = e.get('transformation')
        data['transformation'] = transformation
        data['derivation'] = e.get('derivation')
        data['startTime'] = e.get('start')

        if transformation.startswith('pegasus:'):
            # changing the job type of chmod jobs to auxiliary
            data['type'] = 'auxiliary'
        else:
            data['type'] = 'compute'

        for mj in e.findall('{http://pegasus.isi.edu/schema/invocation}mainjob'):
            runtime += float(mj.get('duration'))

            # get average cpu utilization
            for u in mj.findall('{http://pegasus.isi.edu/schema/invocation}usage'):
                utime = float(u.get('utime'))
                stime = float(u.get('stime'))
                total_time += utime + stime
                maxrss = int(u.get('maxrss'))

            # get job arguments
            for av in mj.findall('{http://pegasus.isi.edu/schema/invocation}argument-vector'):
                for a in av.findall('{http://pegasus.isi.edu/schema/invocation}arg'):
                    args.append(a.text)

            # get job I/O information
            for p in mj.findall('{http://pegasus.isi.edu/schema/invocation}proc'):
                rsspeak = max(float(p.get('rsspeak')), rsspeak)
                vmpeak = max(float(p.get('rsspeak')), vmpeak)
                bytes_read += int(p.get('rbytes')) + int(p.get('rchar'))
                bytes_written += int(p.get('wbytes')) + int(p.get('wchar'))
                iowait += float(p.get('iowait'))
                maxthreads = max(int(p.get('maxthreads')), maxthreads)

        # machine
        for m in e.findall('{http://pegasus.isi.edu/schema/invocation}machine'):
            for u in m.findall('{http://pegasus.isi.edu/schema/invocation}uname'):
                machine['system'] = u.get('system')
                machine['architecture'] = u.get('machine')
                machine['release'] = u.get('release')
                machine['nodeName'] = u.get('nodename')
            for u in m.findall('{http://pegasus.isi.edu/schema/invocation}linux'):
                for r in u.findall('{http://pegasus.isi.edu/schema/invocation}ram'):
                    machine['rsspeak'] = int(r.get('total'))
                for c in u.findall('{http://pegasus.isi.edu/schema/invocation}cpu'):
                    machine['cpu'] = {
                        'count': int(c.get('count')),
                        'speed': int(c.get('speed')),
                        'vendor': c.get('vendor')
                    }

        data['runtime'] = runtime
        if total_time > 0:
            data['avgCPU'] = float('%.4f' % (100 * (total_time / runtime)))
        if utime > 0:
            data['utime'] = utime
        if stime > 0:
            data['stime'] = stime
        if maxrss > 0:
            data['maxrss'] = maxrss
        if rsspeak > 0:
            data['rsspeak'] = rsspeak
        if vmpeak > 0:
            data['vmpeak'] = vmpeak
        if bytes_read > 0:
            data['bytesRead'] = bytes_read
        if bytes_written > 0:
            data['bytesWritten'] = bytes_written
        if iowait > 0:
            data['iowait'] = iowait
        if maxthreads > 0:
            data['maxthreads'] = maxthreads
        if len(args) > 0:
            data['arguments'] = args
        if len(files) > 0:
            data['files'] = files
        if len(machine) > 0:
            # referring to the machine by it's nodeName
            data['machine'] = machine

    except xml.etree.ElementTree.ParseError as ex:
        if data['transformation'].startswith('stage_') or data['transformation'].startswith('create_dir'):
            data['type'] = 'auxiliary'
        logger.warning(data['name'] + ': ' + str(ex))

    # cleaning temporary file
    if temp_file:
        os.remove(kickstart_file)

    return data


def main():
    # Application's arguments
    parser = argparse.ArgumentParser(description='Parse Pegasus Kickstart file to generate a JSON file.')
    parser.add_argument('kickstart_file', metavar='KICKSTART_FILE', help='Pegasus kickstart file')
    parser.add_argument('-o', dest='output', action='store', help='Output filename')
    parser.add_argument('-d', '--debug', action='store_true', help='Print debug messages to stderr')
    args = parser.parse_args()

    # Configure logging
    _configure_logging(args.debug)

    # Sanity check
    if not os.path.isfile(args.kickstart_file):
        logger.error('The provided file does not exist or is not a file:\n\t' + args.kickstart_file)
        exit(1)

    # Generates the JSON file for the kickstart file
    data = _parse_job_output(args.kickstart_file)

    if args.output:
        with open(args.output, 'w') as outfile:
            json.dump(data, outfile, indent=2)
            logger.info('JSON file written to "%s".' % args.output)
    else:
        print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main()
