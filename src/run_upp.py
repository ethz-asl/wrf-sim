import argparse
import datetime
import glob
import os
import shutil
import yaml

parser = argparse.ArgumentParser(description='Run UPP to convert the wrfout to grib files')
parser.add_argument('-y', '--yaml-config', required=True, help='YAML config file')
parser.add_argument('-d', '--date', required=True, help='Start date of the simulation')
parser.add_argument('-c', '--configs', required=True, help='Path to the configuration files folder')
parser.add_argument('-r', '--run-directory', required=True, help='Directory for the simulation run')
parser.add_argument('--domain', type=str, default='d03', help='Domain indentifier that is processed')
parser.add_argument('--dt', type=int, required=True, help='Simulation interval in hours')
parser.add_argument('--offset', type=int, default=0, help='Simulation start offset in hours')
parser.add_argument('-i', '--increment', type=int, required=True, help='Increment between wrfout in minutes')
args = parser.parse_args()

# load the default configurations
with open(args.yaml_config, 'rt') as fh:
    config = yaml.safe_load(fh)

# generate the output folder structure
for folder in ['UPP', 'DATA', 'TMP']:
    os.makedirs(os.path.join(args.run_directory, folder), exist_ok=True)

# setting up symlinks to the UPP files
upp_dir = os.path.join(args.run_directory, 'UPP')
os.symlink(config['UPP']['exe_path'], os.path.join(upp_dir, 'upp.x'))
shutil.copyfile(os.path.join(args.configs, 'wrf_cntrl.parm'), os.path.join(upp_dir, 'postxconfig-NT.txt'))

base_dir_upp = config['UPP']['base_dir']
files_list = ['post_avblflds.xml', 'params_grib2_tbl_new', 'nam_micro_lookup.dat', 'hires_micro_lookup.dat']
for file in files_list:
    os.symlink(os.path.join(base_dir_upp, 'parm', file), os.path.join(upp_dir, file))

# link coefficients for crtm2 (simulated synthetic satellites), not sure if they are really required
crtm_dir = os.path.join(base_dir_upp, 'crtm', 'fix')
files_dict = {
    'Nalli.IRwater.EmisCoeff.bin': os.path.join('EmisCoeff', 'IR_Water', 'Big_Endian'),
    'FASTEM4.MWwater.EmisCoeff.bin': os.path.join('EmisCoeff', 'MW_Water', 'Big_Endian'),
    'FASTEM5.MWwater.EmisCoeff.bin': os.path.join('EmisCoeff', 'MW_Water', 'Big_Endian'),
    'FASTEM6.MWwater.EmisCoeff.bin': os.path.join('EmisCoeff', 'MW_Water', 'Big_Endian'),
    'NPOESS.IRland.EmisCoeff.bin': os.path.join('EmisCoeff', 'IR_Land', 'SEcategory', 'Big_Endian'),
    'NPOESS.IRsnow.EmisCoeff.bin': os.path.join('EmisCoeff', 'IR_Snow', 'SEcategory', 'Big_Endian'),
    'NPOESS.IRice.EmisCoeff.bin': os.path.join('EmisCoeff', 'IR_Ice', 'SEcategory', 'Big_Endian'),
    'AerosolCoeff.bin': os.path.join('AerosolCoeff', 'Big_Endian'),
    'CloudCoeff.bin': os.path.join('CloudCoeff', 'Big_Endian'),
}
for file in files_dict.keys():
    os.symlink(os.path.join(crtm_dir, files_dict[file], file), os.path.join(upp_dir, file))

files_list = [
    'imgr_g11', 'imgr_g12', 'imgr_g13', 'imgr_g15',
    'imgr_mt1r', 'imgr_mt2', 'imgr_insat3d', 'amsre_aqua',
    'tmi_trmm', 'ssmi_f13', 'ssmi_f14', 'ssmi_f15',
    'ssmis_f16', 'ssmis_f17', 'ssmis_f18', 'ssmis_f19',
    'ssmis_f20', 'seviri_m10', 'abi_gr', 'ahi_himawari8',
]
for coeff, odps in zip(['TauCoeff', 'SpcCoeff'], [True, False]):
    for file in files_list:
        filename = file + '.' + coeff + '.bin'
        if odps:
            os.symlink(os.path.join(crtm_dir, coeff, 'ODPS', 'Big_Endian', filename), os.path.join(upp_dir, filename))
        else:
            os.symlink(os.path.join(crtm_dir, coeff, 'Big_Endian', filename), os.path.join(upp_dir, filename))

time = datetime.datetime.strptime(args.date, '%Y-%m-%d')
time = time + datetime.timedelta(hours=args.offset)
end_time = time + datetime.timedelta(hours=args.dt-args.offset)

current_directory = os.getcwd()
os.chdir(upp_dir)
tmp_dir = os.path.join(args.run_directory, 'TMP')
data_dir = os.path.join(args.run_directory, 'DATA')

while time <= end_time:
    # fill in the itag file
    filename = 'wrfout_' + args.domain + '_' + time.strftime("%Y-%m-%d_%H:%M:%S")
    f_itag = open(os.path.join(upp_dir, 'itag'), 'wt')
    f_itag.write("&model_inputs\n")
    f_itag.write("fileName='" + os.path.join(tmp_dir, filename) + "'\n")
    f_itag.write("IOFORM='netcdf'\n")
    f_itag.write("grib='grib2'\n")
    f_itag.write("DateStr='" + time.strftime("%Y-%m-%d_%H:%M:%S") + "'\n")
    f_itag.write("MODELNAME='NCAR'\n")
    f_itag.write("fileNameFlat='postxconfig-NT.txt'\n")
    f_itag.write("/\n")
    f_itag.write("&nampgb\n")
    f_itag.write("numx=1\n")
    f_itag.write("/\n")
    f_itag.close()

    # run UPP
    try:
        command_string = './upp.x > upp.' + time.strftime("%Y-%m-%d_%H:%M:%S") + '.out 2>&1'
        os.system(command_string)

        # move output files to the DATA folder
        upp_out_file = glob.glob(os.path.join(upp_dir, 'WRFPRS.GrbF*'))[0]
        shutil.move(upp_out_file, os.path.join(data_dir, 'WRF_' + time.strftime("%Y-%m-%d_%H:%M:%S") + '.grb'))
    except:
        exit(1)

    time += datetime.timedelta(minutes=5)

os.chdir(current_directory)

# link the correct Vtable
wps_dir = os.path.join(args.run_directory, 'WPS')
shutil.copyfile(os.path.join(args.configs, 'Vtable.WRF'), os.path.join(wps_dir, 'Vtable'))

exit(0)