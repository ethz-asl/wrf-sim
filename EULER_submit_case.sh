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
    echo "  r     Requested run time in hours (required)"
    echo "  l     Switching between LES (flag set) and MESO (default) mode"
}

######################################
# Main
######################################
verbose=false
while getopts "lvy:d:a:o:t:n:r:h" option; do
    case $option in
        l  ) les=true;;
        v  ) verbose=true;;
        y  ) yaml="$OPTARG";;
        d  ) date="$OPTARG";;
        o  ) lon="$OPTARG";;
        a  ) lat="$OPTARG";;
        t  ) dt="$OPTARG";;
        n  ) n_cores="$OPTARG";;
        r  ) runtime="$OPTARG";;
        h  ) usage; exit;;
        \? ) echo "Unknown option: -$OPTARG" >&2; exit 1;;
        :  ) echo "Missing option argument for -$OPTARG" >&2; exit 1;;
        *  ) echo "Unimplemented option: -$option" >&2; exit 1;;
    esac
done


# Check if mandatory fields are set
if [ ! "$yaml" ] || [ ! "$date" ] || [ ! "$lon" ] || [ ! "$lat" ] || [ ! "$dt" ] || [ ! "$n_cores" ] || [ ! "$runtime" ]; then
  echo "arguments -y, -o, -a, -t, -n, -r, and -d must be provided"
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

options_string="-y $yaml -d $date -o $lon -a $lat -t $dt -n -1 $les_string $verbose_string"

# Have to write the command to a separate file as otherwise slurm will complain that: Script arguments not permitted with --wrap option
case_name="$date-lat$lat-lon$lon"
file="$case_name.sh"
echo "Case: $case_name, for $dt hours, les option: $les_string, number of cores: $n_cores, with runtime: $runtime"

# submit the job for setting up the case and get the jobid
echo "Submitting setup_case.sh"
echo sbatch -n 1 --cpus-per-task=1 --time=24:00:00 --mem-per-cpu=8192 --wrap=\"bash setup_case.sh $options_string\" > $file
submit_out=$(sh $file)
jobid=$(echo $submit_out | sed 's/[^0-9]*//g')
echo $submit_out

# submit the job for running WRF and set up the dependency to the previous job
echo "Submitting exec_wrf.sh"
echo sbatch -d afterok:$jobid -n $n_cores --cpus-per-task=1 --time=$runtime:00:00 --mem-per-cpu=4096 --wrap=\"bash exec_wrf.sh $options_string\" > $file
cat $file
sh $file
rm $file
