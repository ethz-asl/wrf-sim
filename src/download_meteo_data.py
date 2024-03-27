import argparse
import datetime
import numpy as np
import os
from projection import get_projection, get_extent_limits
import shutil
import wget
import yaml


parser = argparse.ArgumentParser(description='Downloading meteo data')
parser.add_argument('-y', '--yaml-config', required=True, help='YAML config file')
parser.add_argument('-d', '--date', required=True, help='Start date of the simulation')
parser.add_argument('-c', '--configs', required=True, help='Path to the configuration files folder')
parser.add_argument('--lat', type=float, required=True, help='Latitude of the center of the domain [deg]')
parser.add_argument('--lon', type=float, required=True, help='Longitude of the center of the domain [deg]')
parser.add_argument('--extent', type=float, required=True, help='Extent of the grid [km]')
parser.add_argument('--dt', type=int, required=True, help='Simulation interval in hours')
parser.add_argument('-r', '--run-directory', required=True, help='Directory for the simulation run')
args = parser.parse_args()

# load the default configurations
with open(args.yaml_config, 'rt') as fh:
    config = yaml.safe_load(fh)

# generate the output folder structure
data_path = os.path.join(args.run_directory, 'DATA')
os.makedirs(data_path, exist_ok=True)
wps_dir = os.path.join(args.run_directory, 'WPS')

if config['WPS']['use_era5_data']:
    # get the latitude and longitude extent based on the carthesian extent
    projection, projection_params = get_projection(args.lat, args.lon, args.extent)

    limits = get_extent_limits(args.lat, args.lon, args.extent, projection)

    import cdsapi
    c = cdsapi.Client()

    start_time = datetime.datetime.strptime(args.date, '%Y-%m-%d')


    years = []
    months = []
    days = []
    times = []
    for i in range(args.dt + 1):
        request_time = start_time + datetime.timedelta(hours=i)
        years.append(request_time.strftime('%Y'))
        months.append(request_time.strftime('%m'))
        days.append(request_time.strftime('%d'))
        times.append(request_time.strftime('%H:00'))


    params_common = {
        'product_type': 'reanalysis',
        'year': years,
        'month': months,
        'day': days,
        'time': times,
        'format': 'grid',
        'area': [
            limits['lat_max'],  # North
            limits['lon_min'],  # West
            limits['lat_min'],  # South
            limits['lon_max']], # East
    }


    params_pressure_levels = {
        **params_common,
        'variable': [
            'geopotential', 'relative_humidity', 'temperature',
            'u_component_of_wind', 'v_component_of_wind'
        ],
        'pressure_level': [
            '1', '2', '3',
            '5', '7', '10',
            '20', '30', '50',
            '70', '100', '125',
            '150', '175', '200',
            '225', '250', '300',
            '350', '400', '450',
            '500', '550', '600',
            '650', '700', '750',
            '775', '800', '825',
            '850', '875', '900',
            '925', '950', '975',
            '1000',
        ],
    }

    params_single_levels = {
        **params_common,
        'variable': [
            '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_dewpoint_temperature',
            '2m_temperature', 'land_sea_mask', 'mean_sea_level_pressure',
            'sea_ice_cover', 'sea_surface_temperature', 'skin_temperature', 'snow_depth',
            'soil_temperature_level_1', 'soil_temperature_level_2', 'soil_temperature_level_3',
            'soil_temperature_level_4', 'surface_pressure', 'volumetric_soil_water_layer_1',
            'volumetric_soil_water_layer_2', 'volumetric_soil_water_layer_3', 'volumetric_soil_water_layer_4',
        ],
    }

    import pdb
    pdb.set_trace()

    base_name = args.date
    try:
        c.retrieve(
            'reanalysis-era5-pressure-levels',
            params_pressure_levels,
            os.path.join(data_path, base_name + '_pressure_levels.grib'))

        c.retrieve(
            'reanalysis-era5-single-levels',
            params_single_levels,
            os.path.join(data_path, base_name + '_single_levels.grib'))
    except Exception as e:
        print('ERROR: Failed to download the file')
        print(str(e))
        exit(1)
    import pdb
    pdb.set_trace()





    for i in range(args.dt + 1):
        request_time = start_time + datetime.timedelta(hours=i)
        params_common = {
            'product_type': 'reanalysis',
            'year': request_time.strftime('%Y'),
            'month': request_time.strftime('%m'),
            'day': request_time.strftime('%d'),
            'time': request_time.strftime('%H:00'),
            'format': 'grid',
            'area': [
                limits['lat_max'],  # North
                limits['lon_min'],  # West
                limits['lat_min'],  # South
                limits['lon_max']], # East
        }

        params_pressure_levels = {
            **params_common,
            'variable': [
                'geopotential', 'relative_humidity', 'temperature',
                'u_component_of_wind', 'v_component_of_wind'
            ],
            'pressure_level': [
                '1', '2', '3',
                '5', '7', '10',
                '20', '30', '50',
                '70', '100', '125',
                '150', '175', '200',
                '225', '250', '300',
                '350', '400', '450',
                '500', '550', '600',
                '650', '700', '750',
                '775', '800', '825',
                '850', '875', '900',
                '925', '950', '975',
                '1000',
            ],
        }

        params_single_levels = {
            **params_common,
            'variable': [
                '10m_u_component_of_wind', '10m_v_component_of_wind', '2m_dewpoint_temperature',
                '2m_temperature', 'land_sea_mask', 'mean_sea_level_pressure',
                'sea_ice_cover', 'sea_surface_temperature', 'skin_temperature', 'snow_depth',
                'soil_temperature_level_1', 'soil_temperature_level_2', 'soil_temperature_level_3',
                'soil_temperature_level_4', 'surface_pressure', 'volumetric_soil_water_layer_1',
                'volumetric_soil_water_layer_2', 'volumetric_soil_water_layer_3', 'volumetric_soil_water_layer_4',
            ],
        }

        base_name = request_time.strftime('%Y-%m-%d-%H')
        try:
            c.retrieve(
                'reanalysis-era5-pressure-levels',
                params_pressure_levels,
                os.path.join(data_path, base_name + '_pressure_levels.grib'))

            c.retrieve(
                'reanalysis-era5-single-levels',
                params_single_levels,
                os.path.join(data_path, base_name + '_single_levels.grib'))

        except Exception as e:
            print('ERROR: Failed to download the file')
            print(str(e))
            exit(1)

    # link the correct Vtable
    shutil.copyfile(os.path.join(args.configs, 'Vtable.ERA5'), os.path.join(wps_dir, 'Vtable'))

else:
    date = args.date.replace('-','')
    base_url = 'https://ftp.ncep.noaa.gov/data/nccf/com/gfs/prod/gfs.' + date + '/00/atmos/gfs.t00z.pgrb2.0p25.f'
    base_filename = date + '_gfs.t00z.pgrb2.0p25.f'

    for i in range(args.dt+1):
        url = base_url + str(i).zfill(3)
        filename = base_filename + str(i).zfill(3)
        try:
            response = wget.download(url, os.path.join(data_path, filename))
        except Exception as e:
            print('ERROR: Failed to download the file')
            print(str(e))
            exit(1)

        if not os.path.isfile(response):
            print('ERROR: Failed to download meteo data')
            exit(1)

    # link the correct Vtable
    shutil.copyfile(os.path.join(args.configs, 'Vtable.GFS'), os.path.join(wps_dir, 'Vtable'))

exit(0)