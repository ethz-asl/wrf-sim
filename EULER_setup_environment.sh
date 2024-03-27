module load gcc/6.3.0
module load openmpi/4.1.4
module load libszip/2.1.1
module load zlib/1.2.11
module load hdf5/1.10.9 --enable-fortran --enable-parallel --with-zlib --with-szlib
module load curl/7.72.0
module load perl/5.34.0
module load m4/1.4.18
module load libpng/1.6.34
module load eth_proxy
module load libgeotiff/1.7.1
module load python/3.8.5
module load cmake/3.19.8
module load libgeotiff/1.7.1
module load python/3.8.5
module load gdal/3.5.3
module load proj/8.2.1
module load eccodes/2.21.0
module load netcdf/4.9.0
module load netcdf-fortran/4.5.4
module load geos

DIR=TO_CHANGE/Build_WRF/LIBRARIES/
export CC=gcc
export CXX=g++
export FC=gfortran
export FCFLAGS=-m64
export F77=gfortran
export FFLAGS=-m64

#export NETCDF=$DIR/netcdf
export HDF5=/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/lib
export LDFLAGS="-L/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/lib -I$DIR/grib2/include"
export CPPFLAGS="-I/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/include"
export PATH=TO_CHANGE/convert_geotiff:$DIR/netcdf/bin:$PATH
