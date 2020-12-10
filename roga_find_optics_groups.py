'''A script to find RELION optics groups from EPU movie filename lists'''

from __future__ import unicode_literals
from __future__ import print_function, division, absolute_import

import argparse
import sys
import os

import numpy as np
import pandas as pd


def parse_mtf_info_file(mtf_info_file):
    assert os.path.exists(mtf_info_file)
    mtf_file_list = []
    original_angpix_list = []
    for line in open(mtf_info_file):
        line = line.strip()
        words = line.split()
        if len(words) == 2:
            mtf_file_list.append(words[0])
            original_angpix_list.append(words[1])
    assert len(mtf_file_list) > 0
    return mtf_file_list, original_angpix_list


def find_optics_groups(infiles, print_group_info=True,
                       mtf_file_list=None, original_angpix_list=None):
    if mtf_file_list is not None and original_angpix_list is not None:
        assert len(infiles) == len(mtf_file_list) == len(original_angpix_list)

    data = []
    for i, infile in enumerate(infiles):
        assert os.path.exists(infile)
        with open(infile) as f:
            mics = [os.path.splitext(os.path.basename(x.strip()))[0]
                    for x in f.readlines()]

        for mic in mics:
            words = mic.split('_')
            data_mic = [
                mic,
                i,
                int(words[1]),
                int(words[3]),
                int(words[4]),
                int(words[5]),
                words[6]
            ]
            if mtf_file_list is not None and original_angpix_list is not None:
                data_mic += [mtf_file_list[i], original_angpix_list[i]]
            data.append(data_mic)

    columns = ['filename', 'filelist_group', 'foilhole', 'shift_x', 'shift_y', 'date', 'time']
    if mtf_file_list is not None and original_angpix_list is not None:
        columns += ['mtf_file', 'orig_angpix']

    df = pd.DataFrame(data, columns=columns)

    df_gr = df.groupby(by=['filelist_group', 'shift_x', 'shift_y'])
    optics_group_list = np.zeros(len(df), dtype=int)
    for i, (group_id, mic_idxs) in enumerate(df_gr.indices.items()):
        if print_group_info:
            #print(f'Group No.{i + 1:3d}, (filelist id, shift_x, shift_y) = ({group_id[0]:2d}, {group_id[1]}, {group_id[2]}), {len(mic_idxs):5d} images.')
            print('Group No. %3d, (filelist_id, shift_x, shift_y) = (%2d, %d, %d), %5d images.'
                  % (i + 1, group_id[0], group_id[1], group_id[2], len(mic_idxs)))
        optics_group_list[mic_idxs] = i + 1
    df['optics_group'] = optics_group_list

    return df


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument('--infiles', nargs='+', required=True, help='Input filename lists.')
    parser.add_argument('--mtf_info_file', help='Write a MTF filename (with its FULL-PATH! or a relative path which is accessible from RELION project directory) and the original pixel size(angpix) for each filelist')
    parser.add_argument('--outfile', required=True, help='Output csv file.')
    args = parser.parse_args()

    print('##### Command #####\n\t' + ' '.join(sys.argv))
    args_print_str = '##### Input parameters #####\n'
    for opt, val in vars(args).items():
        args_print_str += '\t{} : {}\n'.format(opt, val)
    print(args_print_str)
    return args


if __name__ == '__main__':
    args = parse_args()

    if args.mtf_info_file is not None:
        mtf_file_list, original_angpix_list = parse_mtf_info_file(args.mtf_info_file)

    df = find_optics_groups(args.infiles, mtf_file_list=mtf_file_list, original_angpix_list=original_angpix_list)

    df.to_csv(args.outfile, index=False)
