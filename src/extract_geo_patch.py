import argparse
import numpy as np
import os
from projection import get_projection, get_extent_limits

parser = argparse.ArgumentParser(description='Extract the terrain patch to the settings')
parser.add_argument('--lat', type=float, required=True, help='Latitude of the center of the domain [deg]')
parser.add_argument('--lon', type=float, required=True, help='Longitude of the center of the domain [deg]')
parser.add_argument('--extent', type=float, required=True, help='Extent of the grid [km]')
parser.add_argument('-o', '--output', required=True, help='Path to the output geotiff file')
parser.add_argument('-t', '--geotiff', required=True, help='Path to the input geotiff')
args = parser.parse_args()

# get the projection
projection, projection_params = get_projection(args.lat, args.lon, args.extent)

# check if the pole is contained within the extent as it is currently not supported
center_x, center_y = projection(args.lon, args.lat)
if args.lat > 0:
    pos_pole = projection(args.lon, 90)
else:
    pos_pole = projection(args.lon, -90)
dist_pole_km = np.sqrt((center_x - pos_pole[0])**2 + (center_y - pos_pole[1])**2) / 1000

if dist_pole_km < 0.5 * args.extent:
    raise('WARNING: The poles are contained within the domain, which is currently not supported')

# determine the min/max lat/lon of the requested domain
limits = get_extent_limits(args.lat, args.lon, args.extent, projection)

# extract the requested domain from the full geotiff
# The -unscale option is important as the convert_geotiff can not handle scaled geotiff values
command_string = 'gdal_translate -unscale  -a_nodata 0.0 -projwin {0:.2f} {1:.2f} {2:.2f} {3:.2f} {4:} {5:}'.format(
    limits['lon_min'], limits['lat_max'], limits['lon_max'], limits['lat_min'],
    args.geotiff, args.output)
os.system(command_string)
