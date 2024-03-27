import numpy as np
import pyproj

def get_projection(center_lat, center_lon, extent):
    threshold_mercator = 30
    threshold_lambert = 60

    projection_params = {
        'ref_lat': center_lat,
        'ref_lon': center_lon,
        'truelat1': center_lat,
        'truelat2': center_lat,
    }

    if np.abs(center_lat) < threshold_mercator:
        projection_params['type'] = 'mercator'
        # use the mercator projection
        proj_string = '+proj=merc +lat_ts={0:.2f} +ellps=WGS84'.format(center_lat)

    elif np.abs(center_lat) < threshold_lambert:
        projection_params['type'] = 'lambert'

        # the reference latitudes are usually put to +- 2/6 from the center lat
        earth_radius = 6357.0 # Choose the smaller polar radius to be conservative
        lat_extent = np.degrees(extent / earth_radius)
        ref_lat_dist = np.round(lat_extent * 1.0/3.0, 2)

        if center_lat > 0:
            lat1 = center_lat - ref_lat_dist
            lat2 = center_lat + ref_lat_dist
        else:
            lat1 = center_lat + ref_lat_dist
            lat2 = center_lat - ref_lat_dist

        projection_params['truelat1'] = lat1
        projection_params['truelat2'] = lat2

        proj_string = '+proj=lcc +lon_0={0:.2f} +lat_0={1:.2f} +lat_1={2:.2f} +lat_2={3:.2f} +ellps=WGS84'.format(
            center_lon, center_lat, lat1, lat2)

    else:
        projection_params['type'] = 'polar'

        if center_lat > 0.0:
            proj_string = '+proj=stere +lat_0=90 +lat_ts={0:.2f} +ellps=WGS84'.format(center_lat)
        else:
            proj_string = '+proj=stere +lat_0=-90 +lat_ts={0:.2f} +ellps=WGS84'.format(center_lat)

    projection = pyproj.Proj(proj_string)

    return projection, projection_params

def get_extent_limits(center_lat, center_lon, extent, projection):
    center_x, center_y = projection(center_lon, center_lat)
    limits = {
        'lon_min': np.inf,
        'lon_max': -np.inf,
        'lat_min': np.inf,
        'lat_max': -np.inf,
    }

    for offset_x in [-0.5 * extent, 0.0, 0.5 * extent]:
        for offset_y in [-0.5 * extent, 0.0, 0.5 * extent]:
            lon, lat = projection(center_x + offset_x * 1000, center_y + offset_y * 1000, inverse=True)
            limits['lon_min'] = min(limits['lon_min'], lon)
            limits['lat_min'] = min(limits['lat_min'], lat)
            limits['lon_max'] = max(limits['lon_max'], lon)
            limits['lat_max'] = max(limits['lat_max'], lat)

    return limits