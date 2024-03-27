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
module load netcdf/4.9.0
module load netcdf-fortran/4.5.4

current_directory=$(pwd)
install_prefix=TO_CHANGE/les_build/Build_UPP/LIBS/nceplibs/
prefix_path=TO_CHANGE/les_build/Build_UPP/LIBS/nceplibs/
grib_path=TO_CHANGE/les_build/Build_UPP/LIBS/grib2
mkdir -p $install_prefix
mkdir -p $grib_path


export CC=gcc
export CXX=g++
export FC=gfortran
#export FCFLAGS=-m64
export F77=gfortran
#export FFLAGS=-m64

#export NETCDF=$install_prefix/netcdf
export HDF5=/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/lib
export LDFLAGS="-L/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/lib -I$install_prefix/grib2/include"
export CPPFLAGS="-I/cluster/apps/gcc-6.3.0/hdf5-1.10.9-xlzu7dxaclmzssn5ukcnhyfyp6z7jtor/include"
#export PATH=$install_prefix/netcdf/bin:$PATH

[ -d "jasper-1.900.1" ] && mv jasper-1.900.1 jasper-1.900.1-old
[ -f "jasper-1.900.1.tar.gz" ] && mv jasper-1.900.1.tar.gz jasper-1.900.1.tar.gz-old
wget https://www2.mmm.ucar.edu/wrf/OnLineTutorial/compile_tutorial/tar_files/jasper-1.900.1.tar.gz -O jasper-1.900.1.tar.gz
tar -zxvf jasper-1.900.1.tar.gz
rm jasper-1.900.1.tar.gz
cd jasper-1.900.1/
./configure --prefix=$install_prefix/grib2
make
make install
export JASPERLIB=$DIR/grib2/lib
export JASPERINC=$DIR/grib2/include
cd ..


# BACIO
git clone --recurse-submodules -b v2.4.1 https://github.com/NOAA-EMC/NCEPLIBS-bacio.git
cd NCEPLIBS-bacio
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX="$install_prefix/bacio" ..
make -j4
make install
cd $current_directory

# BUFR
git clone --recurse-submodules https://github.com/NOAA-EMC/NCEPLIBS-bufr.git
cd NCEPLIBS-bufr
mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX="$install_prefix/bufr" ..
make -j4
#ctest
make install
cd $current_directory

# W3EMC
git clone --recurse-submodules -b v2.9.2 https://github.com/NOAA-EMC/NCEPLIBS-w3emc.git
cd NCEPLIBS-w3emc
mkdir build
cd build
cmake -DCMAKE_INSTALL_PREFIX="$install_prefix/w3emc" -DCMAKE_PREFIX_PATH="$prefix_path"  ..
make -j4
make install
cd $current_directory

# G2
git clone --recurse-submodules -b v3.4.5 https://github.com/NOAA-EMC/NCEPLIBS-g2.git
cd NCEPLIBS-g2
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/g2" -DCMAKE_PREFIX_PATH="$prefix_path;$grib_path"
make -j4
make install
cd $current_directory

# G2TMPL
git clone --recurse-submodules -b develop https://github.com/NOAA-EMC/NCEPLIBS-g2tmpl.git
cd NCEPLIBS-g2tmpl
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/g2tmpl"
make -j4
make install
cd $current_directory

# SP
git clone --recurse-submodules -b v2.3.3 https://github.com/NOAA-EMC/NCEPLIBS-sp.git
cd NCEPLIBS-sp
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/sp"
make -j4
make install
cd $current_directory

# IP
git clone --recurse-submodules -b v3.3.3 https://github.com/NOAA-EMC/NCEPLIBS-ip.git
cd NCEPLIBS-ip
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/ip"
make -j4
make install
cd $current_directory

# W3NCO
git clone --recurse-submodules -b v2.4.1 https://github.com/NOAA-EMC/NCEPLIBS-w3nco.git
cd NCEPLIBS-w3nco
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/w3nco"
make -j4
make install
cd $current_directory

# CRTM
git clone --recurse-submodules -b v2.3.0 https://github.com/NOAA-EMC/EMC_crtm.git
cd EMC_crtm
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/crtm"
make -j4
make install
cd $current_directory

# SIGIO
git clone --recurse-submodules -b v2.3.2 https://github.com/NOAA-EMC/NCEPLIBS-sigio.git
cd NCEPLIBS-sigio
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/sigio"
make -j4
make install
cd $current_directory

# SFCIO 
git clone --recurse-submodules -b v1.4.1 https://github.com/NOAA-EMC/NCEPLIBS-sfcio.git
cd NCEPLIBS-sfcio
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/sfcio"
make -j4
make install
cd $current_directory

# NEMSIO
git clone --recurse-submodules -b v2.5.4 https://github.com/NOAA-EMC/NCEPLIBS-nemsio.git
cd NCEPLIBS-nemsio
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/nemsio" -DCMAKE_PREFIX_PATH="$prefix_path"
make -j4
make install
cd $current_directory

# GFSIO
git clone --recurse-submodules -b v1.4.1 https://github.com/NOAA-EMC/NCEPLIBS-gfsio.git
cd NCEPLIBS-gfsio
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/gfsio"
make -j4
make install
cd $current_directory

# WRF_IO
git clone --recurse-submodules -b v1.2.0 https://github.com/NOAA-EMC/NCEPLIBS-wrf_io.git
cd NCEPLIBS-wrf_io
mkdir build
cd build
cmake .. -DCMAKE_INSTALL_PREFIX="$install_prefix/wrf_io"
make -j4
make install
cd $current_directory

# UPP
git clone --recurse-submodules -b upp_v11.0.0 https://github.com/NOAA-EMC/UPP.git
export CMAKE_PREFIX_PATH=$prefix_path
cd UPP/tests
./compile_upp.sh -p "$install_prefix/upp"


cd ../
mkdir crtm && cd crtm
wget https://github.com/NOAA-EMC/UPP/releases/download/upp_v11.0.0/fix.tar.gz
tar -xzf fix.tar.gz

