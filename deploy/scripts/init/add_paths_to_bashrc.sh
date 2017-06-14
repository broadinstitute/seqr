header='seqr settings'

#echo grep -q '$header' ~/.bashrc
if grep -q "$header" ~/.bashrc
then
    echo $header already found in ~/.bashrc. Skipping..
    exit 0
fi

echo "# $header" >> ~/.bashrc
echo 'export PATH='${INSTALL_DIR}'/postgres/pgsql/bin:$PATH' >> ~/.bashrc
echo 'export PATH='`ls -d ${INSTALL_DIR}/mongo/mongodb-*/bin`':$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH='${INSTALL_DIR}'/postgres/pgsql/lib:$LD_LIBRARY_PATH' >> ~/.bashrc

source ~/.bashrc
