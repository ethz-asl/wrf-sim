#!/bin/bash
######################################
# Help
######################################

usage()
{
    echo "Execute wrf for an already set up case"
    echo
    echo "Syntax: exec_wrf.sh [-h|-v|-y|-d|-t|-o|-a|-n|-l]"
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
# Check wrf.exe out
######################################
check_wrf_exe_out() {
    wrf_exe_success=1
    local SUCCESS='SUCCESS COMPLETE WRF'
    for file in $1; do
        local LOG=$(tail $file -n 20)
        if [[ $LOG != *$SUCCESS* ]]; then
            echo 'WARNING: $file, success message not found'
            wrf_exe_success=0
        fi

        local cfl_errors=$(grep cfl $file)
        if [[ ! -z "$cfl_errors" ]]; then
            echo "WARNING: CFL errors detected in file $file"
            wrf_exe_success=0
        fi
    done;

    local input_files=(`find $2 -maxdepth 1 -name "wrfout*"`)
    if [ ${#input_files[@]} -eq 0 ]; then
        echo 'WARNING: Did not find any wrfout files in folder: $2'
        wrf_exe_success=0
    fi

    if [ $wrf_exe_success == 0 ]; then
        echo 'ERROR: Failed execute wrf.exe'
        exit 1
    else
        echo 'Successfully executed wrf.exe'
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
    run_directory="$case_directory/LES"
else
    run_directory="$case_directory/MESO"
fi

###########
# Running wrf.exe
###########
cd $run_directory/WRF

if [ "$verbose" = "true" ]; then
    start=`date +%s`
fi

if [ "$n_cores" -gt 0 ]; then
  mpirun -np $n_cores ./wrf.exe
else
  mpirun ./wrf.exe
fi

for file in rsl.*; do
    cp "${file}" "../OUT/wrf_${file}"
done;

# move output files to the OUT directory
mv wrfout_* ../OUT

check_wrf_exe_out "rsl.error.*" ../OUT

if [ "$verbose" = "true" ]; then
    end=`date +%s`
    echo "done in `expr $end - $start` seconds"
fi
