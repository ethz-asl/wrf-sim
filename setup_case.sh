#!/bin/bash
######################################
# Help
######################################

usage()
{
    echo "Script to setup a WRF case"
    echo
    echo "Syntax: setup_case.sh [-h|-v|-y|-d|-t|-o|-a|-n|-l]"
    echo "options:"
    echo "  h     Print this help"
    echo "  v     Enable verbose outputs"
    echo "  y     Path to the yaml config file (required)"
    echo "  d     Start date to simulate (required)"
    echo "  t     Total simulation interval in hours (required)"
    echo "  o     Longitude of the grid center in deg (required)"
    echo "  a     Latitude of the grid center in deg (required)"
    echo "  n     Number of cores used to execute wrf (required)"
    echo "  l     Switching between LES (flag set) and MESO (default) mode"
}

######################################
# Parse a YAML file
######################################
parse_yaml() {
   local prefix=$2
   local s='[[:space:]]*' w='[a-zA-Z0-9_]*' fs=$(echo @|tr @ '\034')
   sed -ne "s|^\($s\):|\1|" \
        -e "s|^\($s\)\($w\)$s:$s[\"']\(.*\)[\"']$s\$|\1$fs\2$fs\3|p" \
        -e "s|^\($s\)\($w\)$s:$s\(.*\)$s\$|\1$fs\2$fs\3|p"  $1 |
   awk -F$fs '{
      indent = length($1)/2;
      vname[indent] = $2;
      for (i in vname) {if (i > indent) {delete vname[i]}}
      if (length($3) > 0) {
         vn=""; for (i=0; i<indent; i++) {vn=(vn)(vname[i])("_")}
         printf("%s%s%s=\"%s\"\n", "'$prefix'",vn, $2, $3);
      }
   }'
}

######################################
# Check convert_geotiff out
######################################
check_convert_geotiff_out() {
    convert_geotiff_success=0

    local num_files=$(ls | wc -l)

    if [ $num_files -gt 0 ]; then
        echo 'Successfully converted the geotiff'
        convert_geotiff_success=1
    fi

    if [ $convert_geotiff_success == 0 ]; then
        echo 'ERROR: Failed to convert the geotiff'
        exit 1
    fi
}

######################################
# Check geogrid out
######################################
check_geogrid_out() {
    local LOG=$(tail $1 -n 3)
    local SUCCESS='Successful completion of geogrid'
    geogrid_success=0
    if [[ $LOG == *$SUCCESS* ]]; then
        geogrid_success=1
    fi

    local geo_files=(`find $2 -maxdepth 1 -name "geo_em*"`)
    if [ ${#geo_files[@]} -gt 0 ]; then
        echo 'Successfully generated geogrid files'
    else
        geogrid_success=0
    fi

    if [ $geogrid_success == 0 ]; then
        echo 'ERROR: Failed to generate geogrid files'
        exit 1
    fi
}

######################################
# Check real.exe out
######################################
check_real_exe_out() {
    local LOG=$(tail $1 -n 20)
    local SUCCESS='SUCCESS COMPLETE REAL_EM INIT'
    real_exe_success=0
    if [[ $LOG == *$SUCCESS* ]]; then
        real_exe_success=1
    fi

    local input_files=(`find $2 -maxdepth 1 -name "wrfinput_d*"`)
    if [ ${#input_files[@]} -eq 0 ]; then
        real_exe_success=0
    fi

    local body_files=(`find $2 -maxdepth 1 -name "wrfbdy_d*"`)
    if [ ${#body_files[@]} -eq 0 ]; then
        real_exe_success=0
    fi

    if [ $real_exe_success == 0 ]; then
        echo 'ERROR: Failed execute real.exe'
        exit 1
    else
        echo 'Successfully executed real.exe'
    fi
}

######################################
# Check success
######################################
check_success() {
    local LOG=$(tail $1 -n 100)
    local SUCCESS='Successful completion of '
    ungrib_success=0
    if [[ $LOG == *$SUCCESS* ]]; then
        ungrib_success=1
        echo 'Successfully executed' $2
    fi

    if [ $ungrib_success == 0 ]; then
        echo 'ERROR: Failed to execute' $2
        exit 1
    fi
}

######################################
# Main
######################################
verbose=false
while getopts "lvy:d:a:o:t:n:h" option; do
    case $option in
        l  ) les=true;;
        v  ) verbose=true;;
        y  ) yaml="$OPTARG";;
        d  ) date="$OPTARG";;
        o  ) lon="$OPTARG";;
        a  ) lat="$OPTARG";;
        t  ) dt="$OPTARG";;
        n  ) n_cores="$OPTARG";;
        h  ) usage; exit;;
        \? ) echo "Unknown option: -$OPTARG" >&2; exit 1;;
        :  ) echo "Missing option argument for -$OPTARG" >&2; exit 1;;
        *  ) echo "Unimplemented option: -$option" >&2; exit 1;;
    esac
done

# Check if mandatory fields are set
if [ ! "$yaml" ] || [ ! "$date" ] || [ ! "$lon" ] || [ ! "$lat" ] || [ ! "$dt" ] || [ ! "$n_cores" ]; then
  echo "arguments -y, -o, -a, -t, -n, and -d must be provided"
  echo "$usage" >&2; exit 1
fi

# Parsing the yaml file
eval $(parse_yaml $yaml)

# Define a (hopefully) unique case name
case_name="$date-lat$lat-lon$lon"
current_directory=$(pwd)
case_directory="$out_out_directory/$case_name"

# Setting up variables depending on the mode
if [ "$les" = "true" ]; then
    num_domains=$LES_num_domains
    namelist_wps="namelist_les.wps"
    namelist_input="namelist_les.input"
    run_directory="$case_directory/LES"
    time_offset=$LES_time_offset_h
else
    num_domains=$MESO_num_domains
    namelist_wps="namelist_meso.wps"
    namelist_input="namelist_meso.input"
    run_directory="$case_directory/MESO"
    time_offset=0
fi

# grid extents in km
grid_extent=1800
grid_extent_hr=120

###########
# Setup GEO DATA
###########
if [ "$verbose" = "true" ]; then
    echo "Start setting up GEO DATA ..."
    start=`date +%s`
fi

# generate the local folder and create a symlink to all the local data
if [[ -z "${TMPDIR}" ]]; then
  geo_data_location="${WPS_out_geog_data_path}/${case_name}"
else
  geo_data_location="${TMPDIR}/${case_name}"
fi

mkdir -p $geo_data_location

for geo_dir in ${WPS_geog_data_path}/*/ ; do
    ln -s $geo_dir $geo_data_location
done

path_extracted_terrain_patch_hr="$geo_data_location/extracted_patch_hr.tif"
path_extracted_terrain_patch_lr="$geo_data_location/extracted_patch_lr.tif"

# extract a subregion from the geotiff
python3 $current_directory/src/extract_geo_patch.py --lat $lat --lon $lon --extent $grid_extent -o $path_extracted_terrain_patch_lr -t $WPS_low_res_topo_file
python3 $current_directory/src/extract_geo_patch.py --lat $lat --lon $lon --extent $grid_extent_hr -o $path_extracted_terrain_patch_hr -t $WPS_high_res_topo_file

# convert the geotiff to the binary format and fix the index file (occasionally the convert file reads a resolution of 0...)
cd $geo_data_location
mkdir topo_ensembledtm_1s
cd topo_ensembledtm_1s
convert_geotiff -b 30 -t 1500 -s 1.0 -m 0.0 -u "meter MSL" -d "Ensemble DTM 1-arc-second topography height" $path_extracted_terrain_patch_hr
python3 $current_directory/src/fix_resolution_index_file.py -i "index" -r 0.000277777777777
rm $path_extracted_terrain_patch_hr

cd $geo_data_location
mkdir topo_ensembledtm_15s
cd topo_ensembledtm_15s
convert_geotiff -b 10 -t 1500 -s 1.0 -m 0.0 -u "meter MSL" -d "Ensemble DTM 15-arc-second topography height" $path_extracted_terrain_patch_lr
python3 $current_directory/src/fix_resolution_index_file.py -i "index" -r 0.004166666666654
rm $path_extracted_terrain_patch_lr

check_convert_geotiff_out

cd $current_directory

###########
# Setup WRS
###########
if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
    echo "Start setting up WPS ..."
    start=`date +%s`
fi

python3 $current_directory/src/setup_wps.py -y $current_directory/$yaml -d $date --lat $lat --lon $lon \
    -c "default_files" --dt $dt -r $run_directory -g $geo_data_location --extent $grid_extent \
    --namelist $namelist_wps --num-domains $num_domains --offset $time_offset

###########
# Generating the geogrid
###########
if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
    echo "Building Geogrid ..."
    start=`date +%s`
fi

cd $run_directory/WPS
./geogrid.exe >> log.geogrid

cp log.geogrid ../OUT/

check_geogrid_out log.geogrid ../TMP/

# check if the mapfrac is close to 1.0
python3 $current_directory/src/check_mapfac.py -i "../TMP/"
mapfac_error=$?
if [ "${mapfac_error}" -ne 0 ]; then
    echo "MAPFAC deviation from 1.0 too large"
    exit 1
fi

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
fi

###########
# Preparing the meteo data
###########
if [ "$les" = "true" ]; then
    if [ "$verbose" = "true" ]; then
        echo "Start converting the wrfout with upp ..."
        start=`date +%s`
    fi
    ln -s $case_directory/MESO/OUT/wrfout*  $run_directory/TMP/

    python3 $current_directory/src/run_upp.py -y $current_directory/$yaml -d $date \
        -c "$current_directory/default_files" --dt $dt -r $run_directory -i 5  --offset $time_offset

    if [ $? -ne 0 ]; then
        echo "Failed to run UPP"
        exit $?
    fi

    num_metgrid_levels=60
else
    # Downloading the data for the mesoscale simulation
    if [ "$verbose" = "true" ]; then
        echo "Start downloading data ..."
        start=`date +%s`
    fi
    python3 $current_directory/src/download_meteo_data.py -y $current_directory/$yaml -d $date --lat $lat --lon $lon \
        -c $current_directory/default_files --dt $dt -r $run_directory --extent $grid_extent

    if [ $? -ne 0 ]; then
        exit $?
    fi

    if [ "$WPS_use_era5_data" = "True" ] || [ "$WPS_use_era5_data" = "true" ]; then
        num_metgrid_levels=38
    else
        num_metgrid_levels=34
    fi
fi

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
    echo "Start ungribbing the meteo data ..."
    start=`date +%s`
fi

###########
# Ungribbing the data
###########
cd $run_directory/WPS
./link_grib.csh ../DATA/

./ungrib.exe >> log.ungrib

cp log.ungrib ../OUT/

check_success log.ungrib ungrib

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
    echo "Start building the metgrid ..."
    start=`date +%s`
fi

###########
# Building the metgrid
###########
./metgrid.exe >& log.metgrid

cp log.metgrid ../OUT/

check_success log.metgrid metgrid

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
    echo "Start setting up WRF ..."
    start=`date +%s`
fi

###########
# Setting up WRF
###########
python3 $current_directory/src/setup_wrf.py -y $current_directory/$yaml -d $date --lat $lat --lon $lon \
        -c $current_directory/default_files --dt $dt -r $run_directory --namelist $namelist_input \
        --num-metgrid-levels $num_metgrid_levels --num-domains $num_domains --offset $time_offset

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
    echo "Running real.exe ..."
    start=`date +%s`
fi

###########
# Running real.exe
###########
cd $run_directory/WRF

ln -sf $run_directory/TMP/met_em* .

mpirun -np 1 ./real.exe

cp rsl.error.0000 ../OUT/real_rsl.error.0000
cp rsl.out.0000 ../OUT/real_rsl.out.0000

check_real_exe_out rsl.error.0000 .

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
fi

echo "==============================================="
echo "Finished setting up case"
echo "==============================================="

