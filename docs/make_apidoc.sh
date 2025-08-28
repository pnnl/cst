# API documentation
sphinx-apidoc -f -T -E -M -d 2 -o . ../src/cosim_toolbox/cosim_toolbox
sed -i 's/cosim\\_toolbox p/CoSim Toolbox P/g' cosim_toolbox.rst
mv cosim_toolbox.rst references/.
cat preable.txt ../LICENSE > references/LICENSE.rst
printf "\nFor interested users:  This software system was developed at PNNL with DOE funding [from the Office of Electricity], and PNNL also developed utility applications that are patent-protected and available for licensing for commercial use. More information can be found at PNNL’s Available Technologies site: http://availabletechnologies.pnnl.gov/" >> references/LICENSE.rst
