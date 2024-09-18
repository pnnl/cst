# Build runtime image
FROM alpine:latest AS cosim-alpine

ARG SIM_UID
ARG COSIM_USER

# ENV PATH=$PATH:/usr/bin/ 
# ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/bin/

# Do not use apt/apt-get in Alpine Linux

RUN echo "===== Building CoSim Alpine =====" && \
apk update && \
apk upgrade && \
apk add build-base bash cmake pkgconf autoconf automake libtool && \
apk add gcc libgcc musl libgfortran libquadmath && \
apk add git wget lsof unzip && \ 
# java support(openjdk11-jdk)
echo "==ADDING JAVA SUPPORT PACKAGE==" && \
apk add openjdk11-jdk && \
# message support
echo "==ADDING MESSAGE SUPPORT PACKAGES==" && \
apk add zeromq-dev czmq-dev && \
# misc libraries
echo "==ADDING MISC LIBRARIES==" && \
apk add boost-dev xerces-c-dev hdf5-dev && \
# solver libraries
echo "==ADDING SOLVER LIBRARIES==" && \
apk add tar suitesparse-dev make && \
apk add --update ca-certificates openssl && \
apk add jsoncpp-dev sudo spdlog-dev && \
# nauty2 link: https://pallini.di.uniroma1.it/
echo "==ADDING LIBNAUTY2 PACKAGE==" && \
wget http://pallini.di.uniroma1.it/nauty2_8_8.tar.gz && \
gunzip nauty2_8_8.tar.gz && \
tar -xvf nauty2_8_8.tar && \
cd nauty2_8_8 && \
./configure --prefix=/usr/bin/ && \
make -j8 && \
make install prefix=/usr/bin && \
cd .. && \
# METIS link: http://glaros.dtc.umn.edu/gkhome/metis/metis/download
echo "==ADDING GKLIB AND METIS PACKAGES==" && \
git clone https://github.com/KarypisLab/GKlib.git && \
cd GKlib && \
make config shared=1 prefix=/usr/bin/ && \
make -j8 && \
make install prefix=/usr/bin/ && \
cd .. && \
git clone https://github.com/KarypisLab/METIS.git && \
cd METIS && \
make config shared=1 prefix=/usr/bin/ && \
make -j8 && \
make install prefix=/usr/bin/ && \
cd .. && \
# Can also use wget to fetch and install Metis:
# wget http://glaros.dtc.umn.edu/gkhome/fetch/sw/metis/metis-5.1.0.tar.gz && \
# gunzip metis-5.1.0.tar.gz && \
# tar -xvf metis-5.1.0.tar && \
# cd metis-5.1.0 && \
# make -j8 && \
# make config prefix=/usr/bin/ && \
# make install && \
# cd .. && \
# LAPACK link: https://www.netlib.org/lapack/#_lapack_version_3_12_0
# Contains pre-built BLAS, LAPACK, and LAPACKE libraries
echo "==ADDING LAPACK PACKAGE==" && \
wget https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v3.12.0.tar.gz && \
gunzip v3.12.0.tar.gz && \
tar -xvf v3.12.0.tar && \
cd lapack-3.12.0 && \
mkdir build-lapack && \
cd build-lapack && \
cmake .. && \
make -j8 && \
make install prefix=/usr/bin/ && \
cd ../.. && \
echo "==FETCHING AND BUILDING COINUTILS==" && \
git clone https://github.com/coin-or/CoinUtils.git && \
cd CoinUtils && \
./configure --prefix=/usr/bin/ && \
make -j8 && \
make install prefix=/usr/bin/ && \
cd .. && \
echo "==FETCHING AND BUILDING IPOPT==" && \
# Can use wget to build and install Ipopt: 
wget https://github.com/coin-or/Ipopt/archive/refs/tags/releases/3.14.16.tar.gz && \
gunzip 3.14.16.tar.gz && \
tar -xvf 3.14.16.tar && \
cd Ipopt-releases-3.14.16 && \
mkdir build-ipopt && \
cd build-ipopt && \
../configure prefix=/usr/bin/ && \
make -j8 && \
make install && \
cd ../.. && \
# Can also use GitHub to build and install Ipopt:
# git clone https://github.com/coin-or/Ipopt.git && \
# cd Ipopt && \
# mkdir build-ipopt && \
# cd build-ipopt && \
# ./../configure prefix=/usr/bin/ && \
# make && \
# make install && \
# cd ../.. && \
# remove nauty2, metis, LAPACK, CoinUtils, and Ipopt build directories
echo "==REMOVING COINUTILS AND IPOPT BUILD DIRECTORIES==" && \
rm -r CoinUtils && \
# rm -r Ipopt && \
# Comment out below two commands & uncomment above command if using GitHub for Ipopt
rm -r Ipopt-releases-3.14.16 && \
rm -r 3.14.16.tar && \
echo "==REMOVING NAUTY2 BUILD DIRECTORY==" && \
rm -r nauty2_8_8.tar && \
rm -r nauty2_8_8 && \
echo "==REMOVING METIS AND GKLIB BUILD DIRECTORIES==" && \
rm -r METIS && \
rm -r GKlib && \
# Uncomment below two comments and comment out above two comments if using wget for Metis
# rm -r metis-5.1.0.tar && \
# rm -r metis-5.1.0 && \
echo "==REMOVING LAPACK BUILD DIRECTORY==" && \
rm -r v3.12.0.tar && \
rm -r lapack-3.12.0 && \
# python support packages
echo "==ADDING PYTHON SUPPORT PACKAGES==" && \
apk add py3-pip py3-pillow && \
ln -s /usr/lib/jvm/java-11-openjdk /usr/lib/jvm/default-java && \ 
# setting up cosim user
echo "==SETTING UP COSIM USER==" && \
echo "root:${COSIM_USER}" | chpasswd && \
echo "<<<< Adding the '${COSIM_USER}' user >>>>" && \
adduser -D -s /bin/bash -u $SIM_UID ${COSIM_USER} && \
echo "<<<< Changing ${COSIM_USER} password >>>>" && \
echo "${COSIM_USER}:${COSIM_USER}" | chpasswd && \
echo "%wheel ALL=(ALL) ALL" >> /etc/sudoers.d/wheel && \
adduser ${COSIM_USER} wheel 
