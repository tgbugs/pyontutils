# TODO
scigraph-services.conf also needs to be generated per server due to matrix urls

# oneshots for centos 7
```
sudo mkdir /opt/scigraph-services/
sudo chown bamboo:bamboo /opt/scigraph-services/
sudo mkdir /var/log/scigraph-services/
sudo chown bamboo:bamboo /var/log/scigraph-services/
sudo touch /etc/scigraph-services.conf
sudo chown bamboo:bamboo /etc/scigraph-services.conf
sudo mkdir -p /var/scigraph-services/
sudo chown -R bamboo:bamboo /var/scigraph-services
```

## if not handled by puppet
`sudo yum install java-1.8.0-openjdk java-1.8.0-openjdk-devel`
must set `alternatives --config java` to 1.8
`wget http://www.apache.org/dist/maven/maven-3/3.5.0/binaries/apache-maven-3.5.0-bin.tar.gz`
`sudo mv apache-maven-3.5.0-bin.tar.gz /opt/ && sudo cd /opt/ && sudo tar xvzf apache-maven-* && ln -sT apache-maven-* maven`
`sudo echo "export M2_HOME=/opt/maven" > /etc/profile.d/maven.sh`
`sudo echo "export PATH=\${M2_HOME}/bin:\${PATH}" >> /etc/profile.d/maven.sh`

# etc for centos 7
1. local services
```
TARGET=target
ontload scigraph # TODO ontload scigraph independent...
scp /tmp/SciGraph-*-services-*.zip ${TARGET}:~/
# RUN 3.
```

2. remote services ssh to target
```
export SERVICES_FOLDER=/opt/scigraph-services/  # FIXME from ontload as well?
unzip SciGraph-*-services-*.zip
export SERVICES_NAME=$(echo scigraph-services-*-SNAPSHOT/)
sudo chown -R bamboo:bamboo ${SERVICES_NAME}
sudo rm -rf ${SERVICES_FOLDER}scigraph*
sudo rm -rf ${SERVICES_FOLDER}lib
sudo mv ${SERVICES_NAME}* ${SERVICES_FOLDER}
# NOTE scigraph-services.jar is set by start.sh  # FIXME propagate this via ontload
sudo mv ${SERVICES_FOLDER}scigraph-services-*-SNAPSHOT.jar ${SERVICES_FOLDER}scigraph-services.jar
# RUN 4. deploy services config
sudo systemctl restart scigraph-services
rmdir ${SERVICES_NAME}
unset SERVICES_FOLDER
unset SERVICES_NAME
```

3. local graph generate services config and move to this folder and scp everything in the folder
this README is in over to your target server and ssh to target 
```
TARGET=target
ontload services NIF-Ontology
cp /tmp/NIF-Ontology/scigraph/services.yaml .
scp s* ${TARGET}:~/
rm services.yaml  # prevent staleness by accident
```

4. remote graph
```
# deploy services config
export SERVICES_FOLDER=/opt/scigraph-services/  # FIXME from ontload as well?
sudo cp services.yaml ${SERVICES_FOLDER}
sudo cp start.sh ${SERVICES_FOLDER}
sudo cp stop.sh ${SERVICES_FOLDER}
# systemd services config
sudo cp scigraph-services.service /etc/systemd/system/
sudo systemctl daemon-reload
# java server config
sudo cp scigraph-services.conf /etc/

# deploy graph
export GRAPH_FOLDER=$(grep location services.yaml | cut -d':' -f2 | tr -d '[:space:]')
export GRAPH_PARENT_FOLDER=$(dirname ${GRAPH_FOLDER})/
# get a graph build TODO
wget https://github.com/SciCrunch/NIF-Ontology/releases/download/v2.14/NIF-Ontology-master-graph-2017-09-13-4633a79-f52329a.zip
sudo unzip NIF-Ontology-*-graph-*.zip
export GRAPH_NAME=$(echo NIF-Ontology-*-graph-*/)
sudo chown -R bamboo:bamboo $GRAPH_NAME
sudo mv ${GRAPH_NAME} ${GRAPH_PARENT_FOLDER}
sudo systemctl stop scigraph-services
sudo unlink ${GRAPH_FOLDER}
sudo ln -sT ${GRAPH_PARENT_FOLDER}/${GRAPH_NAME} ${GRAPH_FOLDER}
sudo systemctl start scigraph-services
unset SERVICES_FOLDER
unset GRAPH_FOLDER
unset GRAPH_PARENT_FOLDER
unset GRAPH_NAME
```

# deploy services config
