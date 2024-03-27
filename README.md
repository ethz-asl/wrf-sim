
# WRF-Sim
This repository contains code to run nested WRF-ARW simulations in two stages and postprocessing the WRF output.

In the first stage a PBL model is used according to the configuration model and then in the second stage no PBL will be used. The postprocessing computes the 5 minute averages of the simulation output and stores it in a single NetCDF file.

The output of the simulation can be visualized using the [wrf-viewer](https://github.com/ethz-asl/wrf-viewer).

## Installation

#### General
Download the mandatory high-resolution geographic information from [UCAR](https://www2.mmm.ucar.edu/wrf/src/wps_files/geog_high_res_mandatory.tar.gz).

The ERA5 data for the boundary conditions is downloaded using the [CDS API](https://cds.climate.copernicus.eu/api-how-to) this requires the installation of the client and the appropriate setup.

To build a high-resolution elevation dataset for WPS first download the 30m resolution tiff from the Ensemble DTM on [zenodo](https://zenodo.org/records/7634679). Then with `gdal_translate` create a lower 450m resolution tiff to speed up the processing of the lower resolution nests (both tiffs are required).  The [convert_geotiff](https://github.com/openwfm/convert_geotiff) package needs then to be installed the geotiffs can be converted into the format that WPS can handle.

#### Custom computer
On a custom computer install WRF-ARW version 4.4.2 and [UPP](https://github.com/NOAA-EMC/UPP) according to the instructions. For the WRF-ARW installation there are good installation scripts on [github](https://github.com/bakamotokatas/WRF-Install-Script).

#### Euler
On Euler first load the necessary models using `EULER_setup_environment.sh`, then install WRF-ARW using `EULER_install_WRF.bash` and UPP using `EULER_install_UPP.sh`. The paths in the the installation and setup scripts need to be adjusted to the install location of the different packages.


## Execution
In any case modify the `default.yaml` or a copy of it by setting the correct paths to the different WRF/WPS/UPP executables. The default configuration is to run the the first step with 3 nests (9km, 3km, 1km) and then in the second stage with two nests (333m and 111m).

#### General
Run the first stage of the simulation by executing `exec_wrf.sh`. For example for a run over 51 hours on 2018-02-24 centered in Zurich (latitude: 47.376, longitude: 8.541) execute the following command:
```
bash simulate_case.sh -y default_files/default.yaml -d 2018-02-24 -o 8.541 -a 47.376 -t 51 -n -1 -v
```
This first configures WPS and WRF according to the settings specified in `default.yaml` and the other config files in the `default_files` folder. Modify any of the provided namelist files to configure the simulation differently. This script also automatically downloads the ERA5 data for the run, executes geogrid, metgrid, and finally WRF using all the available cores.

After a successful run of this first stage execute the same command but added with the `-l` flag to run the second stage simulation:
```
bash simulate_case.sh -y default_files/default.yaml -d 2018-02-24 -o 8.541 -a 47.376 -t 51 -n -1 -v -l
```
This will process the output of the first stage simulation with UPP such that it can be processed by WPS and then runs WRF. The output can be finally post-processed by executing:
```
bash run_postprocessing.sh -y default_files/default.yaml -d 2018-02-24 -o 8.541 -a 47.376 -t 51 -n -1 -l -v -e
```
This post processing will store the input ERA5 data if the `-e` flag is present and store the 5-minute averaged data of certain WRF output fields into a single netcdf file.

#### Euler
First load the required modules by running the setup script:  `source EULER_setup_environment.sh`.
Then to execute the first stage of the simulation with the same settings as in the previous case using 20 cores execute:
```
bash EULER_submit_case.sh -r 120 -y default_files/default.yaml -d 2018-02-24 -t 51 -a 47.376 -o 8.541 -n 20 -v
```
After a successful run of the first stage execute the second stage with e.g. 64 cores execute:
```
bash EULER_submit_case.sh -r 120 -y default_files/default.yaml -d 2018-02-24 -t 51 -a 47.376 -o 8.541 -n 64 -v -l
```
Finally, run the postprocessing with:
```
sbatch -n 1 --cpus-per-task=1 --time=48:00:00 --mem-per-cpu=12800 --wrap="bash run_postprocessing.sh -y default_files/data_gen.yaml -d 2018-02-24 -a 47.376 -o 8.541 -t 51 -n -1 -l -v -e"
```