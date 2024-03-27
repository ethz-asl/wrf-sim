#!/bin/bash
######################################
# Help
######################################

usage()
{
    echo "Run the postprocessing with downscaling the ERA5 data and converting it"
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
    echo "  e     If set the ERA5 data is downscaled and converted as well"
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
while getopts "levy:d:a:o:t:n:h" option; do
    case $option in
        l  ) les=true;;
        e  ) era5=true;;
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
    run_directory_wrf="$case_directory/LES"
    time_offset=$LES_time_offset_h
else
    num_domains=$MESO_num_domains
    namelist_wps="namelist_meso.wps"
    run_directory_wrf="$case_directory/MESO"
    time_offset=0
fi

era5_arg=""
if [ "$era5" = "true" ]; then
    if [[ -z "${TMPDIR}" ]]; then
        geo_data_location="${WPS_out_geog_data_path}/${case_name}"
    else
        geo_data_location="${TMPDIR}/${case_name}"
    fi
    grid_extent=1800

    run_directory_post="$case_directory/POST"

    ###########
    # Setup WPS
    ###########
    if [ "$verbose" = "true" ]; then
        echo "Start generating the downscaled meteo data ..."
        start=`date +%s`
    fi

    python3 $current_directory/src/setup_wps.py -y $current_directory/$yaml -d $date --lat $lat --lon $lon \
        -c "default_files" --dt $dt -r $run_directory_post -g $geo_data_location --extent $grid_extent \
        --namelist $namelist_wps --num-domains $num_domains --offset $time_offset --post

    ###########
    # Create symbolic links to the existing data
    ###########
    # create symlinks to the geo_em files that should be processed
    ln -s $run_directory_wrf/TMP/geo_em* $run_directory_post/TMP

    # create symlinks to the meso ungribbed files (contain the downloaded and processed era5 data)
    ln -s $case_directory/MESO/WPS/FILE:* $run_directory_post/WPS

    ###########
    # Building the metgrid
    ###########
    cd $run_directory_post/WPS

    ./metgrid.exe >& log.metgrid

    cp log.metgrid ../OUT/

    check_success log.metgrid metgrid

    era5_arg="-e $run_directory_post/TMP/"

    if [ "$verbose" = "true" ]; then
        end=`date +%s`
        echo "done in `expr $end - $start` seconds"
    fi
fi

###########
# Converting the wrfoutput and the met_em files to a single output file
###########

if [ "$verbose" = "true" ]; then
    echo "Start conversion ..."
    start=`date +%s`
fi

averaging_dt=5
outfile="$case_directory/$case_name.nc"

era5_fields="-pm PRES GHT SEAICE SKINTEMP LANDSEA RH UU VV TT SNOALB LAI12M GREENFRAC ALBEDO12M SCB_DOM SOILCTOP HGT_M LU_INDEX LANDUSEF LANDMASK"
wrf_fields="-pw U V W T P CLDFRA CLOUDFRAC RH QCLOUD QRAIN QICE QSNOW QGRAUP QVAPOR HGT"
namelist_args="-ni $run_directory_wrf/WRF/namelist.input -nw $run_directory_wrf/WPS/namelist.wps"

conversion_args="-w $run_directory_wrf/OUT $era5_arg $era5_fields $wrf_fields -n $case_name -o $outfile -d d0$num_domains -dt $averaging_dt $namelist_args -to 1 --lbc_offset 6"
python3 $current_directory/src/convert_wrfout.py $conversion_args -c 6

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
fi
echo "==============================================="
echo "Finished converting wrf output"
echo "==============================================="
