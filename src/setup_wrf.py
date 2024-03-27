import argparse
import datetime
import glob
import os
import shutil
import yaml

parser = argparse.ArgumentParser(description='Setting up the WPS environment')
parser.add_argument('-y', '--yaml-config', required=True, help='YAML config file')
parser.add_argument('-d', '--date', required=True, help='Start date of the simulation')
parser.add_argument('-c', '--configs', required=True, help='Path to the configuration files folder')
parser.add_argument('--lat', type=float, required=True, help='Latitude of the center of the domain')
parser.add_argument('--lon', type=float, required=True, help='Longitude of the center of the domain')
parser.add_argument('--dt', type=int, required=True, help='Simulation interval in hours starting from 0:00 at the start date')
parser.add_argument('--offset', type=int, default=0, help='Simulation start offset in hours')
parser.add_argument('-r', '--run-directory', required=True, help='Directory for the simulation run')
parser.add_argument('--namelist', required=True, help='Input namelist file')
parser.add_argument('--num-metgrid-levels', type=int, required=True, help='Number of metgrid levels')
parser.add_argument('--num-domains', type=int, required=True, help='Number of domains')
args = parser.parse_args()

# load the default configurations
with open(args.yaml_config, 'rt') as fh:
    config = yaml.safe_load(fh)

# generate the output folder structure
for folder in ['WRF', 'DATA', 'OUT', 'TMP']:
    os.makedirs(os.path.join(args.run_directory, folder), exist_ok=True)

# setting up symlinks to WRF files
wrf_dir = os.path.join(args.run_directory, 'WRF')

files_list = ['real.exe', 'wrf.exe',
]
for file in files_list:
    os.symlink(os.path.join(config['WRF']['run_dir_path'], file), os.path.join(wrf_dir, file))

files_list = [
    'LANDUSE.TBL', 'GENPARM.TBL', 'SOILPARM.TBL', 'VEGPARM.TBL', 'MPTABLE.TBL', # Noah Surface Model
    'RRTM_DATA', 'RRTM_DATA_DBL', 'CAMtr_volume_mixing_ratio', # RRTM Radiation
    'ozone*', 'RRTMG*', # wrf.exe
]
for file in files_list:
    if '*' in file:
        for filepath in glob.glob(os.path.join(config['WRF']['run_dir_path'], file)):
            shutil.copyfile(filepath, os.path.join(wrf_dir, os.path.basename(filepath)))
    else:
        shutil.copyfile(os.path.join(config['WRF']['run_dir_path'], file), os.path.join(wrf_dir, file))

# setting up namelists file
f_namelists_default = open(os.path.join(args.configs, args.namelist), 'rt')
f_namelists_out = open(os.path.join(wrf_dir, 'namelist.input'), 'wt')

start_time = datetime.datetime.strptime(args.date, '%Y-%m-%d')
start_time = start_time + datetime.timedelta(hours=args.offset)
end_time = start_time + datetime.timedelta(hours=args.dt - args.offset)

value_dict = {
    'RUN_TIME': str(args.dt),
    'START_YEAR':  str(start_time.year),
    'START_MONTH': str(start_time.month).zfill(2),
    'START_DAY':   str(start_time.day).zfill(2),
    'START_HOUR':  str(start_time.hour).zfill(2),
    'END_YEAR':  str(end_time.year),
    'END_MONTH': str(end_time.month).zfill(2),
    'END_DAY':   str(end_time.day).zfill(2),
    'END_HOUR':  str(end_time.hour).zfill(2),
    'NUM_METGRID_LEVELS': str(args.num_metgrid_levels),
    'NUM_MAX_DOMAIN': str(args.num_domains),
}

for line in f_namelists_default:
    for key in value_dict:
        line = line.replace(key, value_dict[key])
    f_namelists_out.write(line)

f_namelists_default.close()
f_namelists_out.close()
