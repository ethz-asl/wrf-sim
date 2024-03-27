import argparse
import datetime
import os
from projection import get_projection
import shutil
import yaml

parser = argparse.ArgumentParser(description='Setting up the WPS environment')
parser.add_argument('-y', '--yaml-config', required=True, help='YAML config file')
parser.add_argument('-d', '--date', required=True, help='Start date of the simulation')
parser.add_argument('-c', '--configs', required=True, help='Path to the configuration files folder')
parser.add_argument('--lat', type=float, required=True, help='Latitude of the center of the domain')
parser.add_argument('--lon', type=float, required=True, help='Longitude of the center of the domain')
parser.add_argument('--extent', type=float, required=True, help='Extent of the grid [km]')
parser.add_argument('--dt', type=int, required=True, help='Simulation interval in hours from 0:00 at the start date')
parser.add_argument('--offset', type=int, default=0, help='Simulation start offset in hours')
parser.add_argument('-r', '--run-directory', required=True, help='Directory for the simulation run')
parser.add_argument('-g', '--geo-data-location', required=True, help='Path to the folder with the geo data')
parser.add_argument('--namelist', required=True, help='Input namelist file')
parser.add_argument('--num-domains', type=int, required=True, help='Number of domains')
parser.add_argument('--post', action='store_true', help='Configure WPS for the postprocessing')

args = parser.parse_args()

# load the default configurations
with open(args.yaml_config, 'rt') as fh:
    config = yaml.safe_load(fh)

# generate the output folder structure
os.makedirs(args.run_directory, exist_ok=False)
for folder in ['WPS', 'DATA', 'OUT', 'TMP']:
    os.makedirs(os.path.join(args.run_directory, folder), exist_ok=True)

# setting up symlinks to WPS files
wps_dir = os.path.join(args.run_directory, 'WPS')
files_list = ['ungrib.exe', 'geogrid.exe', 'metgrid.exe', 'link_grib.csh']
for file in files_list:
    os.symlink(os.path.join(config['WPS']['path'], file), os.path.join(wps_dir, file))

shutil.copyfile(os.path.join(args.configs, 'GEOGRID.TBL'), os.path.join(wps_dir, 'GEOGRID.TBL'))
shutil.copyfile(os.path.join(args.configs, 'METGRID.TBL'), os.path.join(wps_dir, 'METGRID.TBL'))

# setting up namelists file
f_namelists_default = open(os.path.join(args.configs, args.namelist), 'rt')
f_namelists_out = open(os.path.join(wps_dir, 'namelist.wps'), 'wt')

start_time = datetime.datetime.strptime(args.date, '%Y-%m-%d')
start_time = start_time + datetime.timedelta(hours=args.offset)
end_time = start_time + datetime.timedelta(hours=args.dt - args.offset)

if args.post:
    end_time_nests = end_time
else:
    end_time_nests = start_time


projection, projection_params = get_projection(args.lat, args.lon, args.extent)

value_dict = {
    'START_DATE': start_time.strftime('%Y-%m-%d_%H:%M:%S'),
    'ENDDATE_NESTS': end_time_nests.strftime('%Y-%m-%d_%H:%M:%S'),
    'CENTER_LAT': str(args.lat),
    'CENTER_LON': str(args.lon),
    'TRUELAT1': str(projection_params['truelat1']),
    'TRUELAT2': str(projection_params['truelat2']),
    'GEOG_PATH': args.geo_data_location,
    'SIMULATION_INTERVAL': str((args.dt - args.offset) * 3600),
    'METGRID_TBL_PATH': str(wps_dir),
    'NUM_MAX_DOMAIN': str(args.num_domains),
    'END_DATE': end_time.strftime('%Y-%m-%d_%H:%M:%S'),
}

if args.post:
    value_dict['interval_seconds = 300'] = 'interval_seconds = 3600'

for line in f_namelists_default:
    for key in value_dict:
        line = line.replace(key, value_dict[key])
    f_namelists_out.write(line)

f_namelists_default.close()
f_namelists_out.close()
