import argparse
import numpy as np
import os
import xarray as xr

parser = argparse.ArgumentParser(description='Check the mapfac of the generated geogrid files')
parser.add_argument('--limit', type=float, default=0.01, help='Maximum allowed deviation of the mapfrac from 1.0')
parser.add_argument('-i', '--input-folder', required=True, help='Path to the folder with geo_em files')
args = parser.parse_args()

all_files = os.listdir(args.input_folder)

max_difference = 0.0
for file in all_files:
    if "geo_em.d" in file:
        dataset = xr.open_dataset(os.path.join(args.input_folder, file))
        for suffix in ['_M', '_MX', '_MY', '_U', '_UX', '_UY', '_V', '_VX', '_VY']:
            data = getattr(dataset, 'MAPFAC' + suffix).isel(Time=0)

            max_difference_file = np.max(np.abs(data.values - 1.0))
            max_difference = max(max_difference, max_difference_file)

print("Maximum MAPFAC deviation from 1.0: {:5f}".format(max_difference))

if max_difference < args.limit:
    exit(0)
else:
    exit(1)
