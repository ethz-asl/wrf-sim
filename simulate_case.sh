#!/bin/bash
######################################
# Help
######################################

usage()
{
    echo "Script to setup and simulate a WRF case"
    echo
    echo "Syntax: simulate_case.sh [-h|-v|-y|-d|-t|-o|-a|-n|-l]"
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

if [ "$les" = "true" ]; then
    les_string="-l"
else
    les_string=""
fi

if [ "$verbose" = "true" ]; then
    verbose_string="-v"
else
    verbose_string=""
fi

options_string="-y $yaml -d $date -o $lon -a $lat -t $dt -n $n_cores $les_string $verbose_string"

current_directory=$(pwd)
bash setup_case.sh $options_string

cd $current_directory
bash exec_wrf.sh $options_string