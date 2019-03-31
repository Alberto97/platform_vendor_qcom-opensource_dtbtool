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

"""Creates a master dtbimage in the QCDT format.

Create header with magic, dtb version and dtb count.
Add chips index
Append dtb images
"""

from argparse import ArgumentParser, FileType
from struct import pack
import os
import re
import subprocess

QCDT_MAGIC = "QCDT"    # Master DTB magic
QCDT_VERSION = 3       # QCDT version

QCDT_DT_TAG = "qcom,msm-id = <"
QCDT_BOARD_TAG = "qcom,board-id = <"
QCDT_PMIC_TAG = "qcom,pmic-id = <"


PAGE_SIZE_DEF = 2048
PAGE_SIZE_MAX = 1024 * 1024

_dt_version = 1
_dtb_list = []
_chip_list = []

class Dtb(object):
    """Used to store dtb infos"""
    def __init__(self, path, size):
        self.path = path
        self.size = size
        self.offset = 0


class Chip(object):
    """Used to store chip infos"""
    def __init__(self, chipset=0, platform=0, subtype=0, rev_num=0,
                 pmic_model0=0, pmic_model1=0, pmic_model2=0, pmic_model3=0):
        self.chipset = chipset
        self.platform = platform
        self.subtype = subtype
        self.rev_num = rev_num
        self.pmic_model0 = pmic_model0
        self.pmic_model1 = pmic_model1
        self.pmic_model2 = pmic_model2
        self.pmic_model3 = pmic_model3
        self.dtb_file = None

    @classmethod
    def create_v1(cls, chipset, platform, rev_num):
        """Create a v1 chip object"""
        return cls(chipset, platform, 0, rev_num)

    @classmethod
    def create_v2(cls, chipset, rev_num, platform, subtype):
        """Create a v2 chip object"""
        return cls(chipset, platform, subtype, rev_num)

    @classmethod
    def create_v3(cls, chipset, rev_num, platform, subtype,
                  pmic_model0, pmic_model1, pmic_model2, pmic_model3):
        """Create a v3 chip object"""
        return cls(chipset, platform, subtype, rev_num,
                   pmic_model0, pmic_model1, pmic_model2, pmic_model3)


def get_dts_data(filename, args):
    """Converts dtb to dts"""
    cmdline = args.dtc_path + 'dtc -I dtb -O dts ' + filename
    return subprocess.check_output(cmdline, shell=True)

def get_version_info(filename, args):
    """Returns QCDT version of the dtb"""
    version = 1
    dts = get_dts_data(filename, args)

    if dts is None:
        print("... skip, fail to decompile dtb")
    elif QCDT_PMIC_TAG in dts:
        version = 3
    elif QCDT_BOARD_TAG in dts:
        version = 2

    print("Version: %s" % version)
    return version

def get_chip_data(line, sublen):
    """Common function chip infos extraction"""
    retlist = []

    str_data = re.search('<(.+?)>', line.strip()).group(1)
    data = str_data.split()

    pos = 0
    item_list = []
    for item in data:
        value = int(item, 16)
        item_list.append(value)
        pos += 1

        if pos == sublen:
            retlist.append(item_list)
            pos = 0
            item_list = []

    return retlist

def get_chip_info(filename, msmversion, args):
    """Extracts chips infos in a sigle dtb image"""
    dts = get_dts_data(filename, args)

    if dts is None:
        return None

    list_chip = []

    cpr_data = []
    cr_data = []
    ps_data = []
    pmic_data = []

    for line in dts.split("\n"):
        if msmversion == 1:
            if args.dt_tag in line:
                cpr_data = get_chip_data(line, 3)
        else:
            if args.dt_tag in line:
                cr_data = get_chip_data(line, 2)

            if QCDT_BOARD_TAG in line:
                ps_data = get_chip_data(line, 2)

            if QCDT_PMIC_TAG in line:
                pmic_data = get_chip_data(line, 4)


    if msmversion == 1:

        if not cpr_data:
            print("... skip, incorrect '%s' format" % args.dt_tag)
            return None

        for cpr in cpr_data:
            chip = Chip.create_v1(cpr[0], cpr[1], cpr[2])
            list_chip.append(chip)

        return list_chip


    if not cr_data:
        print("... skip, incorrect '%s' format" % args.dt_tag)
        return None

    if not ps_data:
        print("... skip, incorrect '%s' format" % QCDT_BOARD_TAG)
        return None

    if not pmic_data and msmversion == 3:
        print("... skip, incorrect '%s' format" % QCDT_PMIC_TAG)
        return None

    for chipset_rev in cr_data:
        for platform_subtype in ps_data:
            if msmversion == 3:
                for pmic in pmic_data:
                    chip = Chip.create_v3(chipset_rev[0], chipset_rev[1],
                                          platform_subtype[0], platform_subtype[1],
                                          pmic[0], pmic[1], pmic[2], pmic[3])
                    list_chip.append(chip)
            else:
                chip = Chip.create_v2(chipset_rev[0], chipset_rev[1],
                                      platform_subtype[0], platform_subtype[1])
                list_chip.append(chip)

    return list_chip

def chip_add(chip):
    """Adds a new chip to the list if does not exist already"""
    global _chip_list

    if _chip_list:
        exists = any(chip.chipset == item.chipset and
                     chip.platform == item.platform and
                     chip.subtype == item.subtype and
                     chip.rev_num == item.rev_num and
                     chip.pmic_model0 == item.pmic_model0 and
                     chip.pmic_model1 == item.pmic_model1 and
                     chip.pmic_model2 == item.pmic_model2 and
                     chip.pmic_model3 == item.pmic_model3 for item in _chip_list)

        if exists:
            # Duplicated
            return False

    _chip_list.append(chip)
    return True

def find_dtb(path, args):
    """Search for dtbs in the provided folder and subfolders and returns count(chips)"""
    dtb_count = 0

    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            print("Searching subdir: %s ..." % entry_path)
            dtb_count += find_dtb(entry_path, args)
        else:
            ext = os.path.splitext(entry)
            if ext[1] == ".dtb":
                print("Found file: %s ..." % entry)
                dtb_count += process_dtb(entry_path, entry, args)

    return dtb_count

def process_dtb(entry_path, filename, args):
    """Collects chips infos in a sigle dtb and returns count(chips)"""
    global _dt_version
    global _dtb_list

    dtb_count = 0

    # Identify the version number
    msmversion = get_version_info(entry_path, args)
    if _dt_version < msmversion:
        _dt_version = msmversion

    chiplist = get_chip_info(entry_path, msmversion, args)

    if msmversion == 1:
        if not chiplist:
            print("skip, failed to scan for %s tag" % args.dt_tag)
            return
    if msmversion == 2:
        if not chiplist:
            print("skip, failed to scan for %s or %s tag" % (args.dt_tag, QCDT_BOARD_TAG))
            return
    if msmversion == 3:
        if not chiplist:
            print("skip, failed to scan for %s, %s or %s tag" %
                  (args.dt_tag, QCDT_BOARD_TAG, QCDT_PMIC_TAG))
            return

    size = os.stat(entry_path).st_size
    if size == 0:
        print("skip, failed to get DTB size")
        return

    # Store every DTB size and path to _dtb_list
    dtb_size = size + (args.page_size - (size % args.page_size))

    dtb = Dtb(entry_path, dtb_size)
    _dtb_list.append(dtb)

    for chip in chiplist:
        print("chipset: %u, rev: %u, platform: %u, subtype: %u, pmic0: %u, pmic1: %u, pmic2: %u, pmic3: %u" %
              (chip.chipset, chip.rev_num, chip.platform, chip.subtype,
               chip.pmic_model0, chip.pmic_model1, chip.pmic_model2, chip.pmic_model3))

        # Add a reference to the DTB
        chip.dtb_file = filename

        rc = chip_add(chip)
        if not rc:
            print("... duplicate info, skipped")
            return

        dtb_count += 1

    return dtb_count

def parse_cmdline():
    """parse command line arguments"""
    parser = ArgumentParser(
        description="dtbTool version " + str(QCDT_VERSION))
    parser.add_argument("input_dir",
                        help="Input directory")
    parser.add_argument("-o", "--output-file", type=FileType('wb'), required=True,
                        help="Output file")
    parser.add_argument("-p", "--dtc-path", default="",
                        help="path to dtc")
    parser.add_argument("-s", "--page-size", default=PAGE_SIZE_DEF, type=int,
                        help="page size in bytes")
    parser.add_argument("-d", "--dt-tag", default=QCDT_DT_TAG,
                        help="alternate QCDT_DT_TAG")
    parser.add_argument("-2", "--force-v2", action="store_true",
                        help="output dtb v2 format")
    parser.add_argument("-3", "--force-v3", action="store_true",
                        help="output dtb v3 format")
    return parser.parse_args()

def validate_args(args):
    """validate command line arguments"""
    if args.page_size <= 0 or args.page_size > PAGE_SIZE_MAX:
        raise ValueError("Invalid page size (must be > 0 and <=1MB")

    if args.force_v2 and args.force_v3:
        raise ValueError("A version output argument may only be passed once")

def override_dt_version(args, dt_version):
    """Overrides dt version if requested"""
    if args.force_v2:
        return 2
    elif args.force_v3:
        return 3
    else:
        return dt_version

def get_entry_size(dt_version):
    """Returns the entry size according to the dt version"""
    if dt_version == 1:
        return 20
    elif dt_version == 2:
        return 24
    else:
        return 40


# Chip index table:
# +-----------------+
# | chipset         |
# +-----------------+
# | platform        |
# +-----------------+
# | subtype         | v2/v3 only
# +-----------------+
# | soc rev         |
# +-----------------+
# | pmic model0     | v3 only
# +-----------------+
# | pmic model1     | v3 only
# +-----------------+
# | pmic model2     | v3 only
# +-----------------+
# | pmic model3     | v3 only
# +-----------------+
# | dtb offset      |
# +-----------------+
# | dtb size        |
# +-----------------+
#
def write_index_table(args, chip_list, dt_version, next_dtb_offset):
    """For each chip write its index table"""
    global _dtb_list
    dtb_ordered_list = []

    for chip in chip_list:
        args.output_file.write(pack('I', chip.chipset))
        args.output_file.write(pack('I', chip.platform))

        if dt_version >= 2:
            args.output_file.write(pack('I', chip.subtype))

        args.output_file.write(pack('I', chip.rev_num))

        if dt_version >= 3:
            args.output_file.write(pack('4I',
                                        chip.pmic_model0,
                                        chip.pmic_model1,
                                        chip.pmic_model2,
                                        chip.pmic_model3))

        indexed_dtb = next((item for item in dtb_ordered_list if chip.dtb_file in item.path), None)
        if not indexed_dtb:
            dtb = next((item for item in _dtb_list if chip.dtb_file in item.path), None)
            if not dtb:
                raise ValueError("DTB not found")

            args.output_file.write(pack('I', next_dtb_offset))
            args.output_file.write(pack('I', dtb.size))

            dtb.offset = next_dtb_offset
            next_dtb_offset += dtb.size

            dtb_ordered_list.append(dtb)
        else:
            args.output_file.write(pack('I', indexed_dtb.offset))
            args.output_file.write(pack('I', indexed_dtb.size))

    return dtb_ordered_list


def write_dtb_data(args, dtb_ordered_list):
    """Write dtb data"""
    for dtb in dtb_ordered_list:
        # Read DTB
        with open(dtb.path, "rb") as dtblob:
            content = dtblob.read()

        # Append DTB content
        args.output_file.write(content)

        # Calculate padding
        padding = args.page_size - (len(content) % args.page_size)

        # Previously calculated size (dtb.size) must match with DTB content + padding
        size = len(content) + padding
        if size != dtb.size:
            raise ValueError("DTB size mismatch, please re-run: expected %d vs actual %d (%s)" %
                             (dtb.size, size, dtb.path))
        # Write padding
        write_padding(args, padding)

def write_padding(args, padding):
    """Write variable length for next DTB to start on page boundary"""
    if padding > 0:
        args.output_file.write(pack('%dx' % padding))

def write_data(args, dtb_count):
    """Write header + chip index table + dtb with relative paddings"""
    global _chip_list
    global _dt_version

    # Override DT version if requested
    dt_version = override_dt_version(args, _dt_version)

    # Get entry size
    entry_size = get_entry_size(dt_version)

    # Calculate offset of first DTB block
    # header size + DTB table entries + end of table indicator
    dtb_offset = 12 + (entry_size * dtb_count) + 4

    # Round up to page size
    padding = args.page_size - (dtb_offset % args.page_size)
    dtb_offset += padding

    print(" Writing header...")

    # Write the header
    args.output_file.write(pack('4s', QCDT_MAGIC.encode()))
    args.output_file.write(pack('I', dt_version))
    args.output_file.write(pack('I', dtb_count))

    # Order chip list by chipset -> platform -> subtype -> rev_num
    chip_list = sorted(_chip_list, key=lambda item:
                       (item.chipset, item.platform, item.subtype, item.rev_num))

    print(" Writing chip index table...")

    # Write chip index table
    dtb_ordered_list = write_index_table(args, chip_list, dt_version, dtb_offset)

    # end of table indicator
    args.output_file.write(pack('I', 0))

    print(" Appending DTB images...")

    # Write padding for the first DTB
    write_padding(args, padding)

    # Write DTBs
    write_dtb_data(args, dtb_ordered_list)

#
# Extract 'qcom,msm-id' 'qcom,board-id' parameter from DTB
#     v1 format:
#         qcom,msm-id = <x y z> [, <x2 y2 z2> ...];
#     v2 format:
#         qcom,msm-id = <x z> [, <x2 z2> ...;
#         qcom,board-id = <y y'> [, <y2 y2'> ...;
#     Fields:
#         x  = chipset
#         y  = platform
#         y' = subtype
#         z  = soc rev
#
def main():
    args = parse_cmdline()
    validate_args(args)

    print("DTB combiner:")

    print("  Input directory: %s" % args.input_dir)
    print("  Output file: %s" % os.path.realpath(args.output_file.name))

    dtb_count = find_dtb(args.input_dir, args)

    print("=> Found %d unique DTB(s)" % dtb_count)

    if dtb_count is None or dtb_count == 0:
        return

    print("Generating master DTB... ")

    write_data(args, dtb_count)

    print("Done")

if __name__ == '__main__':
    main()
