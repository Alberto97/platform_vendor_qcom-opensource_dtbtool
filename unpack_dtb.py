#!/usr/bin/env python
# Copyright 2019, Alberto Pedron
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

from argparse import ArgumentParser, FileType
from struct import unpack
import os

def create_out_dir(dir_path):
    """creates a directory 'dir_path' if it does not exist"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def extract_image(offset, size, dtbimage, extracted_image_name):
    """extracts an image from the dtbimage"""
    dtbimage.seek(offset)
    with open(extracted_image_name, 'wb') as file_out:
        file_out.write(dtbimage.read(size))

def add_unique_dtb(dtb_list, dtb):
    if dtb_list:
        exists = any(item["offset"] == dtb["offset"] for item in dtb_list)
        if exists:
            return False

    dtb_list.append(dtb)
    return True

def unpack_dtb(args):
    qcdt_magic = unpack('4s', args.dtb.read(4))
    print('QCDT magic: %s' % qcdt_magic)

    header = unpack('2I', args.dtb.read(2 * 4))
    version = header[0]
    dtb_count = header[1]

    print('version: %s' % version)
    print('dtb_count: %s' % dtb_count)

    dtb_list = []
    for i in range(dtb_count):
        print('')
        print('Chip %d:' % (i+1))

        chipset = unpack('I', args.dtb.read(4))
        platform = unpack('I', args.dtb.read(4))

        if version >= 2:
            subtype = unpack('I', args.dtb.read(4))

        revNum = unpack('I', args.dtb.read(4))

        if version >= 2:
            print(' chipset: %s platform: %s subtype: %s revNum: %s' % (chipset[0], platform[0], subtype[0], revNum[0]))
        else:
            print(' chipset: %s platform: %s revNum: %s' % (chipset[0], platform[0], revNum[0]))

        if version >= 3:
            pmic = unpack('4I', args.dtb.read(4 * 4))
            print(' pmic0: %s pmic1: %s pmic2: %s pmic3: %s' % (pmic[0], pmic[1], pmic[2], pmic[3]))

        dtbOffset = unpack('I', args.dtb.read(4))
        dtbSize = unpack('I', args.dtb.read(4))
        print(' dtb offset: %s dtb size: %s' % (dtbOffset[0], dtbSize[0]))

        if not args.print_only:
            name_suff = len(dtb_list) + 1
            dtb = {"size": dtbSize[0], "offset": dtbOffset[0], "name": "dtb_%d.dtb" % name_suff}
            add_unique_dtb(dtb_list, dtb)

    if args.print_only:
        return

    print("")
    for dtb in dtb_list:
        print("Extracting %s..." % dtb["name"])
        extract_image(dtb["offset"], dtb["size"], args.dtb,
                      os.path.join(args.out, dtb["name"]))


def parse_cmdline():
    parser = ArgumentParser(description='Unpacks QCDT format dtb')
    parser.add_argument("--dtb", type=FileType('rb'), required=True,
                        help="Input dtb")
    parser.add_argument("-p",'--print-only', action='store_true',
                        help='Only print the structure without extracting dtbs')
    parser.add_argument("-o",'--out', help='path to out dtbs', default='out')
    return parser.parse_args()

def main():
    args = parse_cmdline()

    if not args.print_only:
        create_out_dir(args.out)

    unpack_dtb(args)

if __name__ == '__main__':
    main()
