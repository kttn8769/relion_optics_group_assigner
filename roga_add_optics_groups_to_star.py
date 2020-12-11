'''Add optics groups to particle starfile'''

from __future__ import unicode_literals
from __future__ import print_function, division, absolute_import

import os
import sys
import argparse
from numpy.lib.function_base import append

import progressbar
import numpy as np
import pandas as pd


def read_data_block_as_dataframe(f, block_name):
    if block_name is None:
        # Assumes f is at the block_name line
        pass
    else:
        # Read up to the block_name line
        for line in f:
            line = line.strip()
            if line.startswith(block_name):
                break

    # Read up to loop_
    for line in f:
        if line.startswith('loop_'):
            break

    # Read metadata labels
    metadata_labels = []
    for line in f:
        line = line.strip()
        if line.startswith('_rln'):
            metadata_labels.append(line.split()[0])
        else:
            break

    # Read metadata
    metadata = []
    # The current line is the first metadata record
    words = line.split()
    assert len(metadata_labels) == len(words)
    metadata.append(words)
    for line in f:
        line = line.strip()
        if line == '':
            # Empty line, the end of the metadata block
            break
        words = line.split()
        assert len(metadata_labels) == len(words)
        metadata.append(words)

    # Convert to DataFrame
    metadata_df = pd.DataFrame(metadata, columns=metadata_labels)

    return metadata_df


def read_input_star(input_star):
    assert os.path.exists(input_star)
    with open(input_star, 'r') as f:
        # Determine metadata table version
        for line in f:
            line = line.strip()
            if line == '':
                # Empty line
                continue
            elif line.startswith('# version'):
                # Version string introduced in v3.1
                input_star_version = int(line.split()[-1])
                break
            elif line.startswith('data_'):
                # No version string, thus <= v3.0
                #  Assumes v3.0
                input_star_version = 30000
                break
            else:
                sys.exit('Invalid input star file.')

        if input_star_version > 30000:
            df_optics_in = read_data_block_as_dataframe(f, 'data_optics')
            assert df_optics_in.shape[0] == 1, 'More than two opticsGroups exists in the file.'
            df_particles_in = read_data_block_as_dataframe(f, 'data_particles')
        else:
            df_optics_in = None
            df_particles_in = read_data_block_as_dataframe(f, None)

    return input_star_version, df_particles_in, df_optics_in


def append_optics_groups_to_particle_dataframe(df_in, optics_group_table):
    df_out = df_in.copy(deep=True)
    df_out['_rlnOpticsGroup'] = np.zeros(df_in.shape[0], dtype=int)

    print('Appending _rlnOpticsGroup to each particle....')
    for i in progressbar.progressbar(df_out.index):
        filename = os.path.splitext(os.path.basename(df_in.loc[i, '_rlnMicrographName']))[0]
        match = optics_group_table[optics_group_table.filename == filename]
        assert match.shape[0] == 1
        optics_group = match.iloc[0].optics_group
        df_out.loc[i, '_rlnOpticsGroup'] = optics_group

    # Make sure all the particles are assigned optics group
    assert (df_out._rlnOpticsGroup != 0).all()

    return df_out


def create_output_dataframes(input_star_version, df_particles_out, df_optics_in, optics_group_table, image_size):
    # Check the number of particles in each optics group
    optics_groups, counts = np.unique(df_particles_out._rlnOpticsGroup, return_counts=True)
    for i in range(optics_group_table.optics_group.min(), optics_group_table.optics_group.max() + 1):
        if i in optics_groups:
            num_particles = counts[np.where(optics_groups == i)[0]]
        else:
            num_particles = 0
        print('OpticsGroup %3d : %7d particles' % (i, num_particles))

    # Create metadata labels for output data_optics
    metadata_labels_optics_out = [
        '_rlnOpticsGroupName',
        '_rlnOpticsGroup',
        '_rlnVoltage',
        '_rlnSphericalAberration',
        '_rlnAmplitudeContrast',
        '_rlnImagePixelSize',
        '_rlnImageSize',
        '_rlnImageDimensionality'
    ]
    if 'mtf_file' in optics_group_table.columns:
        metadata_labels_optics_out = metadata_labels_optics_out[:2] + ['_rlnMtfFileName','_rlnMicrographOriginalPixelSize'] + metadata_labels_optics_out[2:]

    # Create output data_optics dataframe
    df_optics_out = pd.DataFrame(columns=metadata_labels_optics_out)
    if input_star_version < 30001:
        for optics_group in optics_groups:
            dict_optics_out_group = {}
            # Extract data of each optics group
            df_tmp = df_particles_out.loc[
                df_particles_out._rlnOpticsGroup == optics_group,
                [
                    '_rlnMagnification',
                    '_rlnDetectorPixelSize',
                    '_rlnAmplitudeContrast',
                    '_rlnSphericalAberration',
                    '_rlnVoltage'
                ]
            ]
            # These values should be same for all records in a group
            for label in df_tmp.columns:
                is_all_same = (df_tmp[label].iloc[0] == df_tmp[label].values).all()
                assert is_all_same, '%s of group %d is inconsistent' % (label, optics_group)

            dict_optics_out_group['_rlnOpticsGroupName'] = 'opticsGroup%d' % (optics_group)
            dict_optics_out_group['_rlnOpticsGroup'] = '%d' % optics_group

            dict_optics_out_group['_rlnVoltage'] = df_tmp.iloc[0]['_rlnVoltage']
            dict_optics_out_group['_rlnSphericalAberration'] = df_tmp.iloc[0]['_rlnSphericalAberration']
            dict_optics_out_group['_rlnAmplitudeContrast'] = df_tmp.iloc[0]['_rlnAmplitudeContrast']
            mag =  float(df_tmp.iloc[0]['_rlnMagnification'])
            detector_pixelsize_micron = float(df_tmp.iloc[0]['_rlnDetectorPixelSize'])
            image_pixelsize_angstrom = detector_pixelsize_micron / mag * 10000
            dict_optics_out_group['_rlnImagePixelSize'] = '%.6f' % image_pixelsize_angstrom
            dict_optics_out_group['_rlnImageSize'] = '%d' % (image_size)
            dict_optics_out_group['_rlnImageDimensionality'] = '2'
            if 'mtf_file' in optics_group_table.columns:
                dict_optics_out_group['_rlnMtfFileName'] = optics_group_table[optics_group_table.optics_group == optics_group].iloc[0].mtf_file
                dict_optics_out_group['_rlnMicrographOriginalPixelSize'] = '%.6f' % optics_group_table[optics_group_table.optics_group == optics_group].iloc[0].orig_angpix
            df_optics_out = df_optics_out.append(dict_optics_out_group, ignore_index=True)
    else:
        assert df_optics_in.shape[0] > 0
        for optics_group in optics_groups:
            dict_optics_out_group = df_optics_in.iloc[0].to_dict()
            dict_optics_out_group['_rlnOpticsGroup'] = '%d' % optics_group
            dict_optics_out_group['_rlnOpticsGroupName'] = 'opticsGroup%d' % optics_group
            if 'mtf_file' in optics_group_table.columns:
                dict_optics_out_group['_rlnMtfFileName'] = optics_group_table[optics_group_table.optics_group == optics_group].iloc[0].mtf_file
                dict_optics_out_group['_rlnMicrographOriginalPixelSize'] = '%.6f' % optics_group_table[optics_group_table.optics_group == optics_group].iloc[0].orig_angpix
            df_optics_out = df_optics_out.append(dict_optics_out_group, ignore_index=True)

    # Create output data_particles dataframe
    if input_star_version < 30001:
        image_angpix = df_particles_out._rlnDetectorPixelSize.astype(float) / df_particles_out._rlnMagnification.astype(float) * 10000
        # Delete old columns (Not needed in v3.1)
        df_particles_out.drop([
            '_rlnMagnification',
            '_rlnDetectorPixelSize',
            '_rlnAmplitudeContrast',
            '_rlnSphericalAberration',
            '_rlnVoltage'
        ], axis=1, inplace=True)
        # Convert _rlnOrigin{X,Y} (pixel) to _rlnOrigin{X,Y}Angst (angstrom/pixel)
        originx_ang = df_particles_out._rlnOriginX.astype(float) * image_angpix
        originy_ang = df_particles_out._rlnOriginY.astype(float) * image_angpix
        df_particles_out['_rlnOriginXAngst'] = originx_ang.map(lambda x: '%.6f'%x)
        df_particles_out['_rlnOriginYAngst'] = originy_ang.map(lambda x: '%.6f'%x)
        df_particles_out.drop(['_rlnOriginX', '_rlnOriginY'], axis=1, inplace=True)
    else:
        # Nothing to do.
        pass

    return df_optics_out, df_particles_out


def write_dataframe_as_star_block(f, df, block_name):
    f.write('\n')
    f.write('# version 30001\n')
    f.write('\n')
    f.write(block_name + '\n\n')
    f.write('loop_\n')
    for i, label in enumerate(df.columns):
        f.write('%s #%d\n' % (label, i+1))
    print('Writing %s ...'%block_name)
    for i in progressbar.progressbar(range(df.shape[0])):
        output = []
        for label in df.columns:
            val = str(df.iloc[i][label])
            if len(val) < 12:
                val = '%12s' % val
            output.append(val)
        output = ' '.join(output) + '\n'
        f.write(output)
    f.write('\n')


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=__doc__
    )
    parser.add_argument('--input_star', required=True, help='Input particle starfile.')
    parser.add_argument('--output_star', required=True, help='Output particle starfile.')
    parser.add_argument('--optics_group_csv', required=True, help='CSV file generated by roga_find_optics_groups.py')
    parser.add_argument('--image_size', default=None, type=int, help='Particle image size in pixels. Required if input_star versions is <= v3.0')
    args = parser.parse_args()

    print('##### Command #####\n\t' + ' '.join(sys.argv))
    args_print_str = '##### Input parameters #####\n'
    for opt, val in vars(args).items():
        args_print_str += '\t{} : {}\n'.format(opt, val)
    print(args_print_str)
    return args


if __name__ == '__main__':
    args = parse_args()

    #assert not os.path.exists(args.output_star), '--output_star %s already exists.' % args.output_star

    input_star_version, df_particles_in, df_optics_in = read_input_star(args.input_star)

    if input_star_version < 30001:
        assert args.image_size is not None, 'Please specify --image_size'

    optics_group_table = pd.read_csv(args.optics_group_csv)

    df_particles_out = append_optics_groups_to_particle_dataframe(df_particles_in, optics_group_table)

    df_optics_out, df_particles_out = create_output_dataframes(input_star_version, df_particles_out, df_optics_in,
                                                               optics_group_table, args.image_size)

    with open(args.output_star, 'w') as f:
        write_dataframe_as_star_block(f, df_optics_out, 'data_optics')
        write_dataframe_as_star_block(f, df_particles_out, 'data_particles')
