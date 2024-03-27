import argparse
from datetime import datetime, timedelta
import h5py
from netCDF4 import Dataset
import numpy as np
import os
import calendar
from tqdm import tqdm
from wrf import getvar, destagger
import sys

def destagger_data(variable_data):
    # destagger the data that is available on a different grid
    if variable_data.attrs['stagger'] == 'X':
        data = destagger(variable_data, -1)
    elif variable_data.attrs['stagger'] == 'Y':
        data = destagger(variable_data, -2)
    elif variable_data.attrs['stagger'] == 'Z':
        data = destagger(variable_data, -3)
    elif variable_data.attrs['stagger'] == 'U':
        data = destagger(variable_data, -1)
    elif variable_data.attrs['stagger'] == 'V':
        data = destagger(variable_data, -2)
    elif variable_data.attrs['stagger'] == 'W':
        data = destagger(variable_data, -3)
    else:
        data = variable_data.data
    return data

def get_files_dict_and_times(folder, domain, searchstring):
    files = [os.path.join(folder, f) for f in os.listdir(folder) if (os.path.isfile(os.path.join(folder, f))  and domain in f and searchstring in f)]
    files.sort()

    if len(files) == 0:
        print('No ' + searchstring + '* files found')
        sys.exit()

    out_dict = {}
    out_times = []

    for file in files:
        try:
            # wrfout files
            t_file = datetime.strptime(os.path.basename(file).split(domain)[-1], "_%Y-%m-%d_%H:%M:%S")
        except:
            # metem files
            t_file = datetime.strptime(os.path.basename(file).split(domain)[-1], ".%Y-%m-%d_%H:%M:%S.nc")
        out_dict[t_file.strftime("%Y-%m-%d_%H:%M:%S")] = file
        out_times.append(t_file)
    out_times = np.array(out_times)

    return out_dict, out_times

def get_samples_list(wrfout_times, met_em_dict, t_start, t_end, window_dt):
    if not (60 % window_dt == 0):
        print('Window dt must divide an hour without any remainder')
        exit(1)

    num_time_windows = int(60 / window_dt)

    samples_list = []
    dt_hour = timedelta(hours=1)
    dt_window = timedelta(minutes=window_dt)
    while t_start < t_end:
        sample = {
            'timestamp': t_start
        }

        if has_met_em_files:
            sample['met_em_file'] = met_em_dict[t_start.strftime("%Y-%m-%d_%H:%M:%S")]

        idx_select = np.logical_and(wrfout_times <= t_start + dt_hour, wrfout_times > t_start)
        sample['wrf_windows'] = []
        times_sample = wrfout_times[idx_select]

        t_window_start = t_start
        t_window_end = t_start + dt_window
        for i in range(num_time_windows):
            idx_select = np.logical_and(times_sample > t_window_start, times_sample <= t_window_end)
            window = {
                'times': times_sample[idx_select],
                't_end': t_window_end,
                'period': t_window_start.strftime("%Y-%m-%d_%H:%M:%S") + 'to' + t_window_end.strftime("%Y-%m-%d_%H:%M:%S")
            }
            sample['wrf_windows'].append(window)
            t_window_start = t_window_end
            t_window_end = t_window_start + dt_window

        samples_list.append(sample)
        t_start = t_start + dt_hour

    return samples_list

def setup_wrf_vars(out_case_group, wrfout_dict, properties_wrf, property_map_wrf, compression, complevel, lbc_offset):
    out_wrf_group = out_case_group.createGroup('wrf')
    ncfile = Dataset(wrfout_dict[list(wrfout_dict.keys())[0]])
    lat_dim_size = ncfile.dimensions['south_north'].size - 2 * lbc_offset
    lon_dim_size = ncfile.dimensions['west_east'].size - 2 * lbc_offset
    out_wrf_group.createDimension('lat', lat_dim_size)
    out_wrf_group.createDimension('lon', lon_dim_size)
    out_wrf_group.createDimension('z', ncfile.dimensions['bottom_top'].size)
    out_wrf_group.createDimension('z_cloud', 3)
    out_wrf_group.createDimension('time', None)

    out_ncfile_wrf_lat = out_wrf_group.createVariable('lat', np.float32, ('lat', 'lon'))
    out_ncfile_wrf_lat.units = 'degree_north'
    out_ncfile_wrf_lat.long_name = 'latitude, south is negative'
    lat = getvar(ncfile, 'lat', meta=False)
    if lbc_offset > 0:
        lat = lat[lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
    out_ncfile_wrf_lat[:] = lat

    out_ncfile_wrf_lon = out_wrf_group.createVariable('lon', np.float32, ('lat', 'lon'))
    out_ncfile_wrf_lon.units = 'degree_east'
    out_ncfile_wrf_lon.long_name = 'longitude, west is negative'
    lon = getvar(ncfile, 'lon', meta=False)
    if lbc_offset > 0:
        lon = lon[lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
    out_ncfile_wrf_lon[:] = lon

    out_ncfile_wrf_z = out_wrf_group.createVariable('z', np.float32, ('z', 'lat', 'lon'))
    out_ncfile_wrf_z.units = 'm'
    out_ncfile_wrf_z.long_name = 'model height - [MSL] (mass grid)'
    alt = getvar(ncfile, 'z', meta=False)
    if lbc_offset > 0:
        alt = alt[:, lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
    out_ncfile_wrf_z[:] = alt

    out_ncfile_wrf_time = out_wrf_group.createVariable('time', np.uint, ('time'))
    out_ncfile_wrf_time.units = 's'
    out_ncfile_wrf_time.long_name = 'UTC time'

    if 'CLOUDFRAC' in properties_wrf:
        var = getvar(ncfile, property_map_wrf['CLOUDFRAC']['name'], meta=True)
        out_ncfile_wrf_z_cloud = out_wrf_group.createVariable('z_cloud', str, ('z_cloud'))
        out_ncfile_wrf_z_cloud.long_name = 'low, mid, high cloud levels'
        out_ncfile_wrf_z_cloud.low_thresh = var.low_thresh
        out_ncfile_wrf_z_cloud.mid_thresh = var.mid_thresh
        out_ncfile_wrf_z_cloud.high_thresh = var.high_thresh
        out_ncfile_wrf_z_cloud[:] = np.array([var.low_thresh, var.mid_thresh, var.high_thresh])

    # initialize the wrf variables
    for property in properties_wrf:
        variable_data = getvar(ncfile, property_map_wrf[property]['name'], meta=True)
        # destagger the data that is potentially available on a different grid
        data = destagger_data(variable_data)

        if property_map_wrf[property]['static']:
            if len(data.shape) == 2:
                chunksizes = (lat_dim_size,lon_dim_size)
            elif len(data.shape) == 3:
                chunksizes = (1, lat_dim_size,lon_dim_size)
            else:
                print('Unsupported dimension for static data')

            var = out_wrf_group.createVariable(
                property,
                property_map_wrf[property]['type'],
                property_map_wrf[property]['dim'],
                chunksizes=chunksizes,
                compression=compression,
                complevel=complevel)

            var.units = property_map_wrf[property]['unit']
            var.long_name = property_map_wrf[property]['description']
            try:
                var.projection = data.projection.proj4()
            except:
                pass

            # directly fill the static data
            if lbc_offset > 0:
                if len(data.shape) == 2:
                    data = data[lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
                elif len(data.shape) == 3:
                    data = data[:, lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
            var[:] = data

        else:
            for mode in property_map_wrf[property]['modes']:
                postfix = ''
                if mode == 'avg':
                    postfix = ''
                elif mode == 'max':
                    postfix = '_max'

                var = out_wrf_group.createVariable(
                    property + postfix,
                    property_map_wrf[property]['type'],
                    property_map_wrf[property]['dim'],
                    chunksizes=(1,1,lat_dim_size,lon_dim_size),
                    compression=compression,
                    complevel=complevel)
                var.units = property_map_wrf[property]['unit']
                var.long_name = property_map_wrf[property]['description']
                try:
                    var.projection = variable_data.projection.proj4()
                except:
                    pass
    return out_ncfile_wrf_time

def setup_era5_vars(out_case_group, met_em_dict, properties_met_em, property_map_met_em, compression, complevel, lbc_offset):
    out_era5_group = out_case_group.createGroup('era5')
    ncfile = Dataset(met_em_dict[list(met_em_dict.keys())[0]])
    lat_dim_size = ncfile.dimensions['south_north'].size - 2 * lbc_offset
    lon_dim_size = ncfile.dimensions['west_east'].size - 2 * lbc_offset

    # check consistency of the dimension with the wrf files
    if 'wrf' in out_case_group.groups.keys():
        error = False
        if out_case_group['wrf'].dimensions['lat'].size != lat_dim_size:
            print('Latitude size of era5 data does not match the wrf size:', out_case_group['wrf'].dimensions['lat'].size, 'vs', lat_dim_size)
            error = True
        if out_case_group['wrf'].dimensions['lon'].size != lon_dim_size:
            print('Longitude size of era5 data does not match the wrf size:', out_case_group['wrf'].dimensions['lon'].size, 'vs', lon_dim_size)
            error = True
        if error:
            sys.exit()

    out_era5_group.createDimension('lat', lat_dim_size)
    out_era5_group.createDimension('lon', lon_dim_size)
    out_era5_group.createDimension('z', ncfile.dimensions['num_metgrid_levels'].size)
    out_era5_group.createDimension('time', None)
    out_era5_group.createDimension('month', 12)
    out_era5_group.createDimension('category16', 16)
    out_era5_group.createDimension('category21', 21)

    out_ncfile_era5_lat = out_era5_group.createVariable('lat', np.float32, ('lat', 'lon'))
    out_ncfile_era5_lat.units = 'degree_north'
    out_ncfile_era5_lat.long_name = 'latitude, south is negative'
    lat = getvar(ncfile, 'lat', meta=False)
    if lbc_offset > 0:
        lat = lat[lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
    out_ncfile_era5_lat[:] = lat

    out_ncfile_era5_lon = out_era5_group.createVariable('lon', np.float32, ('lat', 'lon'))
    out_ncfile_era5_lon.units = 'degree_east'
    out_ncfile_era5_lon.long_name = 'longitude, west is negative'
    lon = getvar(ncfile, 'lon', meta=False)
    if lbc_offset > 0:
        lon = lon[lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
    out_ncfile_era5_lon[:] = lon

    out_ncfile_era5_z = out_era5_group.createVariable('z', np.float32, ('z', 'lat', 'lon'))
    out_ncfile_era5_z.units = 'm'
    out_ncfile_era5_z.long_name = 'model height - [MSL] (mass grid)'
    alt = getvar(ncfile, 'z', meta=False)
    if lbc_offset > 0:
        alt = alt[:, lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
    out_ncfile_era5_z[:] = alt

    out_ncfile_era5_time = out_era5_group.createVariable('time', np.uint, ('time'))
    out_ncfile_era5_time.units = 's'
    out_ncfile_era5_time.long_name = 'UTC time'

    # initialize the era5 variables
    for property in properties_met_em:
        variable_data = getvar(ncfile, property, meta=True)
        # destagger the data that is potentially available on a different grid
        data = destagger_data(variable_data)

        if len(property_map_met_em[property]['dim']) == 2:
            chunksizes = (9, 9)
        elif len(property_map_met_em[property]['dim']) == 3:
            chunksizes = (9, 9, 9)
        elif len(property_map_met_em[property]['dim']) == 4:
            chunksizes = (1, 9, 9, 9)
        else:
            print('Unsupported dimension for static data')

        var = out_era5_group.createVariable(
            property,
            property_map_met_em[property]['type'],
            property_map_met_em[property]['dim'],
            chunksizes=chunksizes,
            compression=compression,
            complevel=complevel)

        var.units = property_map_met_em[property]['unit']
        var.long_name = property_map_met_em[property]['description']
        try:
            var.projection = data.projection.proj4()
        except:
            pass

        if property_map_met_em[property]['static']:
            if lbc_offset > 0:
                if len(data.shape) == 2:
                    data = data[lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
                elif len(data.shape) == 3:
                    data = data[:, lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
                elif len(data.shape) == 4:
                    data = data[:, :, lbc_offset:-lbc_offset, lbc_offset:-lbc_offset]
            # directly fill the static data
            var[:] = data.data

    return out_ncfile_era5_time

parser = argparse.ArgumentParser(description='Converting the wrf')
parser.add_argument('-w', '--wrfout_folder', type=str, required=True, help='Folder with the wrfout files')
parser.add_argument('-e', '--met_em_folder', type=str, help='Folder with the met_em files')
parser.add_argument('-c', '--compress', type=int, default=0, help='Compression level for the gzip compression, if set to 0 no compression is performed')
parser.add_argument('-l', '--max_layers', type=int, default=0, help='Maximum number of layers for 3D data, if 0 all layers are converted')
parser.add_argument('-dt', '--window_dt', type=int, default=5, help='Window size where the wrf outputs are averaged in minutes')
parser.add_argument('-n', '--case_name', type=str, required=True, help='Case name')
parser.add_argument('-o', '--output_file', type=str, required=True, help='Output filename')
parser.add_argument('-d', '--domain', type=str, default='d01', help='Domain identifier of the domain that should be used to get the data')
parser.add_argument('-pw', '--properties_wrf', type=str, nargs='+', default=['U', 'V', 'W'], help='Properties to save for the wrfout files')
parser.add_argument('-pm', '--properties_met_em', type=str, nargs='+', default=['PRES', 'UU', 'VV', 'TT', 'RH', 'LANDMASK'], help='Properties to save for the met_em files')
parser.add_argument('-ni', '--namelist_input', type=str, help='Path to namelist.input file')
parser.add_argument('-nw', '--namelist_wps', type=str, help='Path to namelist.wps file')
parser.add_argument('-to', '--time_offset', type=int, default=1, help='Conversion start time offset in hours')
parser.add_argument('--lbc_offset', type=int, default=6, help='Conversion start time offset in hours')
args = parser.parse_args()

property_map_wrf = {
    'T': {'name': 'tk', 'static': False, 'modes': ['avg'], 'unit': 'K', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Temperature', 'type': np.float32},
    'P': {'name': 'pressure', 'static': False, 'modes': ['avg'], 'unit': 'hPa', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Pressure', 'type': np.float32},
    'U': {'name': 'ua', 'static': False, 'modes': ['avg', 'max'], 'unit': 'm s-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'U-wind component', 'type': np.float32},
    'V': {'name': 'va', 'static': False, 'modes': ['avg', 'max'], 'unit': 'm s-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'V-wind component', 'type': np.float32},
    'W': {'name': 'wa', 'static': False, 'modes': ['avg', 'max'], 'unit': 'm s-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'W-wind component', 'type': np.float32},
    'RH': {'name': 'rh', 'static': False, 'modes': ['avg'], 'unit': '%', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Relative humidity', 'type': np.float32},
    'PW': {'name': 'pw', 'static': False, 'modes': ['avg'], 'unit': 'kg m-2', 'dim': ('time', 'lat', 'lon'), 'description': 'Precipitable water', 'type': np.float32},
    'ZREL': {'name': 'height_agl', 'static': True, 'unit': 'm', 'dim': ('lat', 'lon'), 'description': 'Model height - [AGL] (mass grid)', 'type': np.float32},
    'HGT': {'name': 'ter', 'static': True, 'unit': 'm', 'dim': ('lat', 'lon'), 'description': 'Terrain height', 'type': np.float32},
    'CLOUDFRAC': {'name': 'cloudfrac', 'static': False, 'modes': ['avg'], 'unit': '%', 'dim': ('time', 'z_cloud', 'lat', 'lon'), 'description': 'Low, mid, high clouds', 'type': np.float32},
    'CLDFRA': {'name': 'CLDFRA', 'static': False, 'modes': ['avg'], 'unit': '%', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Cloud fraction at model levels', 'type': np.float32},
    'QCLOUD': {'name': 'QCLOUD', 'static': False, 'modes': ['avg'], 'unit': 'kg kg-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Cloud water mixing ratio', 'type': np.float32},
    'QRAIN': {'name': 'QRAIN', 'static': False, 'modes': ['avg'], 'unit': 'kg kg-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Rain water mixing ratio', 'type': np.float32},
    'QICE': {'name': 'QICE', 'static': False, 'modes': ['avg'], 'unit': 'kg kg-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Ice mixing ratio', 'type': np.float32},
    'QSNOW': {'name': 'QSNOW', 'static': False, 'modes': ['avg'], 'unit': 'kg kg-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Snow mixing ratio', 'type': np.float32},
    'QGRAUP': {'name': 'QGRAUP', 'static': False, 'modes': ['avg'], 'unit': 'kg kg-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Graupel mixing ratio', 'type': np.float32},
    'QVAPOR': {'name': 'QVAPOR', 'static': False, 'modes': ['avg'], 'unit': 'kg kg-1', 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Water vapor mixing ratio', 'type': np.float32},
}

property_map_met_em = {
    'PRES': {'static': False, 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Pressure', 'type': np.float32, 'unit': 'Pa'},
    'GHT': {'static': True, 'dim': ('z', 'lat', 'lon'), 'description': 'Height', 'type': np.float32, 'unit': 'm'},
    'SM100289': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil moisture of 100-289 cm ground layer', 'type': np.float32, 'unit': 'm3 m-3'},
    'SM028100': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil moisture of 28-100 cm ground layer', 'type': np.float32, 'unit': 'm3 m-3'},
    'SM007028': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil moisture of 7-28 cm ground layer', 'type': np.float32, 'unit': 'm3 m-3'},
    'SM000007': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil moisture of 0-7 cm ground layer', 'type': np.float32, 'unit': 'm3 m-3'},
    'ST100289': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil temperature of 100-289 cm ground layer', 'type': np.float32, 'unit': 'K'},
    'ST028100': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil temperature of 28-100 cm ground layer', 'type': np.float32, 'unit': 'K'},
    'ST007028': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil temperature of 7-28 cm ground layer', 'type': np.float32, 'unit': 'K'},
    'ST000007': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Soil temperature of 0-7 cm ground layer', 'type': np.float32, 'unit': 'K'},
    'SNOW': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Water Equivalent of Accumulated Snow Depth', 'type': np.float32, 'unit': 'kg m-2'},
    'SST': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Sea-Surface Temperature', 'type': np.float32, 'unit': 'K'},
    'SEAICE': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Sea-Ice-Flag', 'type': np.uint8, 'unit': '0/1 Flag'},
    'SKINTEMP': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Sea-Surface Temperature', 'type': np.float32, 'unit': 'K'},
    'PMSL': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Sea-level Pressure', 'type': np.float32, 'unit': 'Pa'},
    'PSFC': {'static': False, 'dim': ('time', 'lat', 'lon'), 'description': 'Surface Pressure', 'type': np.float32, 'unit': 'Pa'},
    'LANDSEA': {'static': True, 'dim': ('lat', 'lon'), 'description': 'Land/Sea flag', 'type': np.uint8, 'unit': '0/1 Flag'},
    'RH': {'static': False, 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Relative Humidity', 'type': np.float32, 'unit': '%'},
    'UU': {'static': False, 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'U-wind component', 'type': np.float32, 'unit': 'm s-1'},
    'VV': {'static': False, 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'V-wind component', 'type': np.float32, 'unit': 'm s-1'},
    'TT': {'static': False, 'dim': ('time', 'z', 'lat', 'lon'), 'description': 'Temperature', 'type': np.float32, 'unit': 'K'},
    'SNOALB': {'static': True, 'dim': ('lat', 'lon'), 'description': 'MODIS maximum snow albedo', 'type': np.float32, 'unit': '%'},
    'LAI12M': {'static': True, 'dim': ('month', 'lat', 'lon'), 'description': 'MODIS LAI', 'type': np.float32, 'unit': 'm^2/m^2'},
    'GREENFRAC': {'static': True, 'dim': ('month', 'lat', 'lon'), 'description': 'MODIS FPAR', 'type': np.float32, 'unit': '%'},
    'ALBEDO12M': {'static': True, 'dim': ('month', 'lat', 'lon'), 'description': 'Monthly MODIS surface albedo', 'type': np.float32, 'unit': '%'},
    'SCB_DOM': {'static': True, 'dim': ('lat', 'lon'), 'description': 'Dominant soil category bottom', 'type': np.uint8, 'unit': 'category'},
    'SOILCBOT': {'static': True, 'dim': ('category16', 'lat', 'lon'), 'description': '16-category bottom-layer soil type', 'type': np.uint8, 'unit': 'category'},
    'SCT_DOM': {'static': True, 'dim': ('lat', 'lon'), 'description': 'Dominant soil category top', 'type': np.uint8, 'unit': 'category'},
    'SOILCTOP': {'static': True, 'dim': ('category16', 'lat', 'lon'), 'description': '16-category top-layer soil type', 'type': np.uint8, 'unit': 'category'},
    'HGT_M': {'static': True, 'dim': ('lat', 'lon'), 'description': 'Ensemble DTM 1-arc-second topography height', 'type': np.float32, 'unit': 'meter MSL'},
    'LU_INDEX': {'static': True, 'dim': ('lat', 'lon'), 'description': 'Dominant category', 'type': np.uint8, 'unit': 'category'},
    'LANDUSEF': {'static': True, 'dim': ('category21', 'lat', 'lon'), 'description': 'Noah-modified 21-category IGBP-MODIS landuse', 'type': np.uint8, 'unit': 'category'},
    'LANDMASK': {'static': True, 'dim': ('lat', 'lon'), 'description': 'Landmask : 1=land, 0=water', 'type': np.uint8, 'unit': '0/1 Flag'},
}

not_supported = []
for property in args.properties_wrf:
    if not property in property_map_wrf.keys():
        not_supported.append(property)

if len(not_supported) > 0:
    print('WRF property not supported:', not_supported)
    exit(1)

not_supported = []
for property in args.properties_met_em:
    if not property in property_map_met_em.keys():
        not_supported.append(property)

if len(not_supported) > 0:
    print('MET_EM property not supported:', not_supported)
    exit(1)

if args.compress > 0:
    compression = 'zlib'
    complevel = args.compress
else:
    compression = None
    complevel = 4

# get the wrf files
wrfout_dict, wrfout_times = get_files_dict_and_times(args.wrfout_folder, args.domain, 'wrfout')

t_start = min(wrfout_times)
t_end = max(wrfout_times)

# get the met_em files if set
met_em_dict = {}
has_met_em_files = False
if not (args.met_em_folder is None):
    met_em_dict, met_em_times = get_files_dict_and_times(args.met_em_folder, args.domain, 'met_em')

    t_start = max([t_start, min(met_em_times)])
    t_end = min([t_end, max(met_em_times)])
    has_met_em_files = True

# make sure that we only process data that is available for a full hour
t_end = t_end.replace(minute=0, second=0, microsecond=0)

if args.time_offset > 0:
    t_start += timedelta(hours=args.time_offset)

# group the input files into the samples
samples_list = get_samples_list(wrfout_times, met_em_dict, t_start, t_end, args.window_dt)

# fix the file name appendix
if not args.output_file.endswith('.nc'):
    outfile = args.output_file + '.nc'
else:
    outfile = args.output_file

# create the output dataset file
out_ncfile = Dataset(outfile, mode='w', format='NETCDF4')
out_case_group = out_ncfile.createGroup(args.case_name)
out_case_group.createDimension('str_dim', 1)

# create the dimensions and variables for the WRF data
var_time_wrf = setup_wrf_vars(out_case_group, wrfout_dict, args.properties_wrf, property_map_wrf, compression, complevel, args.lbc_offset)

# create the dimensions for the ERA5 data
if has_met_em_files:
    var_time_era5 = setup_era5_vars(out_case_group, met_em_dict, args.properties_met_em, property_map_met_em, compression, complevel, args.lbc_offset)

# store some metadata for the case as string variables
var = out_case_group.createVariable('domain', str, ('str_dim',))
var.long_name = 'domain of the WRF run'
var[:] = np.array([args.domain], dtype='object')

if args.namelist_input:
    with open(args.namelist_input,'r') as namelist_file:
        var = out_case_group.createVariable('namelist.input', str, ('str_dim',))
        var.long_name = 'namelist.input file for the WRF run'
        var[:] = np.array([namelist_file.read()], dtype='object')

if args.namelist_wps:
    with open(args.namelist_wps,'r') as namelist_file:
        var = out_case_group.createVariable('namelist.wps', str, ('str_dim',))
        var.long_name = 'namelist.wps file for the WPS run'
        var[:] = np.array([namelist_file.read()])

# start converting and filling the data group
wrf_write_index = 0
era5_write_index = 0
with tqdm(total=len(samples_list)) as pbar:
    for i_sample, sample in enumerate(samples_list):
        # process the met_em file
        if 'met_em_file' in sample.keys():
            ncfile = Dataset(sample['met_em_file'])

            for property in args.properties_met_em:
                variable_data = getvar(ncfile, property, meta=True)

                # destagger the data that is available on a different grid
                data = destagger_data(variable_data)

                if not property_map_met_em[property]['static']:
                    if args.lbc_offset > 0:
                        if len(data.shape) == 2:
                            data = data[args.lbc_offset:-args.lbc_offset, args.lbc_offset:-args.lbc_offset]
                        elif len(data.shape) == 3:
                            data = data[:, args.lbc_offset:-args.lbc_offset, args.lbc_offset:-args.lbc_offset]
                        elif len(data.shape) == 4:
                            data = data[:, :, args.lbc_offset:-args.lbc_offset, args.lbc_offset:-args.lbc_offset]
                    out_case_group['era5'][property][era5_write_index] = data

            var_time_era5[era5_write_index] = calendar.timegm(sample['timestamp'].utctimetuple())
            era5_write_index += 1

        # process the wrfout files
        for i_window, window in enumerate(sample['wrf_windows']):
            nc_files = []
            for time in window['times']:
                nc_files.append(Dataset(wrfout_dict[time.strftime("%Y-%m-%d_%H:%M:%S")]))

            for property in args.properties_wrf:
                property_nc = property_map_wrf[property]['name']

                if not property_map_wrf[property]['static']:
                    # dynamic field, get all the data and then process it
                    all_data = []
                    for file in nc_files:
                        variable_data = getvar(file, property_nc, meta=True)

                        # destagger the data that is available on a different grid
                        data = destagger_data(variable_data)

                        all_data.append(data)

                    for mode in property_map_wrf[property]['modes']:
                        postfix = ''
                        if mode == 'avg':
                            postfix = ''
                        elif mode == 'max':
                            postfix = '_max'

                        if len(all_data) > 1:
                            if mode == 'avg':
                                processed_data = np.mean(np.stack(all_data, axis=0), axis=0)
                            elif mode == 'max':
                                stacked_data = np.stack(all_data, axis=0)
                                max_val = np.max(stacked_data, axis=0)
                                min_val = np.min(stacked_data, axis=0)
                                processed_data = np.where(np.abs(max_val) > np.abs(min_val), max_val, min_val)
                            else:
                                print("Unknown data aggregation mode")
                                sys.exit(1)
                        else:
                            processed_data = all_data[0]

                        if args.max_layers > 0 and len(data.shape) == 3:
                            processed_data = processed_data[:args.max_layers]

                        if args.lbc_offset > 0:
                            if len(processed_data.shape) == 2:
                                processed_data = processed_data[args.lbc_offset:-args.lbc_offset, args.lbc_offset:-args.lbc_offset]
                            elif len(processed_data.shape) == 3:
                                processed_data = processed_data[:, args.lbc_offset:-args.lbc_offset, args.lbc_offset:-args.lbc_offset]
                            elif len(processed_data.shape) == 4:
                                processed_data = processed_data[:, :, args.lbc_offset:-args.lbc_offset, args.lbc_offset:-args.lbc_offset]

                        out_case_group['wrf'][property + postfix][wrf_write_index] = processed_data

            var_time_wrf[wrf_write_index] = calendar.timegm(window['t_end'].utctimetuple())
            wrf_write_index += 1
        pbar.update(1)

out_ncfile.close()