#!/bin/bash
#########################################################
# WRF ARW Install Script                      
# This Script was written by Umur Dinç and adjusted by Florian Achermann   	
# To execute this script "bash EULER_install_WRF.bash INSTALL_LOCATION"
#########################################################
WRFversion="4.4.2"
type="ARW"

#########################################################
#   Installing neccessary packages                       #
#########################################################

cd $1
mkdir Build_WRF
cd Build_WRF
mkdir LIBRARIES
cd LIBRARIES

DIR=$(pwd)
echo $DIR

export CC=gcc
export CXX=g++
export FC=gfortran
export FCFLAGS=-m64
export F77=gfortran
export FFLAGS=-m64

export NETCDF=$DIR/netcdf
export HDF5=/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/lib
export LDFLAGS="-L/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/lib -I$DIR/grib2/include -L${NETCDF}/lib"
export CPPFLAGS="-I/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/include -I${NETCDF}/include"
export PATH=SET_PATH/convert_geotiff:$DIR/netcdf/bin:$PATH

##########################################
#	NetCDF Installation		  #
#########################################

wget https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compile_tutorial/tar_files/netcdf-c-4.7.2.tar.gz -O netcdf-c-4.7.2.tar.gz
tar -zxvf netcdf-c-4.7.2.tar.gz
rm netcdf-c-4.7.2.tar.gz
cd netcdf-c-4.7.2
./configure --prefix=$DIR/netcdf --disable-dap --disable-netcdf-4 --disable-shared
make
make install
make check
cd ..
rm -r netcdf-c-4.7.2

wget https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compile_tutorial/tar_files/netcdf-fortran-4.5.2.tar.gz -O netcdf-fortran-4.5.2.tar.gz
export LIBS="-lnetcdf -lz"
tar xzvf netcdf-fortran-4.5.2.tar.gz
rm netcdf-fortran-4.5.2.tar.gz
cd netcdf-fortran-4.5.2
./configure --prefix=$DIR/netcdf --disable-dap  --disable-netcdf-4 --disable-shared
make
make install
make check
cd ..
rm -r netcdf-fortran-4.5.2

#########################################
#	Jasper Installation		#
#########################################
[ -d "jasper-1.900.1" ] && mv jasper-1.900.1 jasper-1.900.1-old
[ -f "jasper-1.900.1.tar.gz" ] && mv jasper-1.900.1.tar.gz jasper-1.900.1.tar.gz-old
wget https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compile_tutorial/tar_files/jasper-1.900.1.tar.gz -O jasper-1.900.1.tar.gz
tar -zxvf jasper-1.900.1.tar.gz
rm jasper-1.900.1.tar.gz
cd jasper-1.900.1/
./configure --prefix=$DIR/grib2
make
make install
#echo "export JASPERLIB=$DIR/grib2/lib" >> ~/.bashrc TODO, maybe add to source script
#echo "export JASPERINC=$DIR/grib2/include" >> ~/.bashrc
export JASPERLIB=$DIR/grib2/lib
export JASPERINC=$DIR/grib2/include
cd ..
rm -r jasper-1.900.1/

#########################################
#	WRF Installation		#
#########################################
cd ..
[ -d "WRF" ] && mv WRF WRF-old
[ -d "WRFV${WRFversion}" ] && mv WRFV${WRFversion} WRFV${WRFversion}-old
[ -f "v${WRFversion}.tar.gz" ] && mv v${WRFversion}.tar.gz v${WRFversion}.tar.gz-old
wget https://github.com/wrf-model/WRF/releases/download/v${WRFversion}/v${WRFversion}.tar.gz -O WRFV${WRFversion}.tar.gz
tar -zxvf WRFV${WRFversion}.tar.gz && mv WRF WRFV${WRFversion}
rm WRFV4.4.2.tar.gz
cd WRFV${WRFversion}

cd arch
cp Config.pl Config.pl_backup
sed -i '428s/.*/  $response = 34 ;/' Config.pl
sed -i '869s/.*/  $response = 1 ;/' Config.pl
cd ..
logsave configure.log ./configure

gfortversion=$(gfortran -dumpversion | cut -c1)
if [ "$gfortversion" -lt 8 ] && [ "$gfortversion" -ge 6 ]; then
sed -i '/-DBUILD_RRTMG_FAST=1/d' configure.wrf
fi
logsave compile.log ./compile em_real
cd arch
cp Config.pl_backup Config.pl
cd ..
if [ -n "$(grep "Problems building executables, look for errors in the build log" compile.log)" ]; then
        echo "Sorry, There were some errors while installing WRF."
        echo "Please create new issue for the problem, https://github.com/bakamotokatas/WRF-Install-Script/issues"
        exit
fi
cd ..
[ -d "WRF-${WRFversion}-${type}" ] && mv WRF-${WRFversion}-${type} WRF-${WRFversion}-${type}-old
mv WRFV${WRFversion} WRF-${WRFversion}-${type}


#########################################
#	WPS Installation		#
#########################################
WPSversion="4.4"
[ -d "WPS-${WPSversion}" ] && mv WPS-${WPSversion} WPS-${WPSversion}-old
[ -f "v${WPSversion}.tar.gz" ] && mv v${WPSversion}.tar.gz v${WPSversion}.tar.gz-old
wget https://github.com/wrf-model/WPS/archive/v${WPSversion}.tar.gz -O WPSV${WPSversion}.TAR.gz
tar -zxvf WPSV${WPSversion}.TAR.gz
cd WPS-${WPSversion}
cd arch
cp Config.pl Config.pl_backup
sed -i '154s/.*/  $response = 3 ;/' Config.pl
cd ..
./clean
sed -i '141s/.*/    NETCDFF="-lnetcdff"/' configure
sed -i "173s/.*/standard_wrf_dirs=\"WRF-${WRFversion}-${type} WRF WRF-4.0.3 WRF-4.0.2 WRF-4.0.1 WRF-4.0 WRFV3\"/" configure
./configure
logsave compile.log ./compile
sed -i "s# geog_data_path.*# geog_data_path = '../WPS_GEOG/'#" namelist.wps
cd arch
cp Config.pl_backup Config.pl
cd ..
cd ..

##########################################################
#	End						#
##########################################################
echo "Installation has completed"
exec bash
exit
