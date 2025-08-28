# API documentation
sphinx-apidoc -f -T -M -d 2 -o . ../src/cosim_toolbox/cosim_toolbox
sed -i 's/cosim\\_toolbox p/CoSim Toolbox P/g' cosim_toolbox.rst
mv cosim_toolbox.rst references/.
# Traditional documentation
python -m sphinx -T -E -b html -d _build/doctrees -D language=en . _build/html