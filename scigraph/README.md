# Commands to generate config files and graph on the build host

``` bash
export TARGET=localhost  # set this!
export BUILD_DIR=/tmp/scigraph-build
scigraph-deploy config --local ${HOSTNAME} ${TARGET} -l ${BUILD_DIR} -z ${BUILD_DIR}
ontload graph NIF-Ontology NIF -p -b master -l ${BUILD_DIR} -z ${BUILD_DIR}
```

Example build command `ontload graph NIF-Ontology NIF -z /tmp/scigraph-build -l /tmp/scigraph-build -O SciGraph -B patch-issue-264 -b master -p`

See also [.travis.yml](https://github.com/SciCrunch/NIF-Ontology/blob/master/.travis.yml) for NIF-Ontology.

# Merging commits from SciGraph/SciGraph master into upstream

https://github.com/SciCrunch/SciGraph/compare/upstream...SciGraph:master

# DO NOT FORGET TO ENABLE THE SERVICES AT STARTUP

```
sudo systemctl enable scigraph-services
```

# oneshots for centos 7

```
export $USER=bamboo
sudo mkdir /opt/scigraph-services/
sudo chown ${USER}:${USER} /opt/scigraph-services/
sudo mkdir /var/log/scigraph-services/
sudo chown ${USER}:${USER} /var/log/scigraph-services/
sudo touch /etc/scigraph-services.conf
sudo chown ${USER}:${USER} /etc/scigraph-services.conf
sudo mkdir -p /var/scigraph-services/
sudo chown -R ${USER}:${USER} /var/scigraph-services
```

# oneshots for rhel 7 on ec2

```
sudo yum install screen vim
sudo yum install unzip  # wat
sudo yum install xorg-x11-server-Xvfb  # capitalization matters and need to enable rhel-server-optional
sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm  # for nginx
sudo yum install nginx
```

## if not handled by puppet

```
sudo yum install java-1.8.0-openjdk java-1.8.0-openjdk-devel
alternatives --config java  # must set to 1.8
wget http://www.apache.org/dist/maven/maven-3/3.5.0/binaries/apache-maven-3.5.0-bin.tar.gz
sudo mv apache-maven-3.5.0-bin.tar.gz /opt/ && sudo cd /opt/ && sudo tar xvzf apache-maven-* && ln -sT apache-maven-* maven
sudo echo "export M2_HOME=/opt/maven" > /etc/profile.d/maven.sh
sudo echo "export PATH=${M2_HOME}/bin:${PATH}" >> /etc/profile.d/maven.sh
```

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
export $USER=bamboo
export SERVICES_FOLDER=/opt/scigraph-services/  # FIXME from ontload as well?
unzip SciGraph-*-services-*.zip
export SERVICES_NAME=$(echo scigraph-services-*-SNAPSHOT/)
sudo chown -R ${USER}:${USER} ${SERVICES_NAME}
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
#export TARGET=target  # YOU MUST EXPORT THIS YOURSELF
export BUILD_DIR=/tmp/build
mkdir ${BUILD_DIR}
ontload scigraph-deploy config --local $(hostname) ${TARGET} -z ${BUILD_DIR}
scp ${BUILD_DIR}/s* ${TARGET}:~/
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
export $USER=bamboo
curl -LOk $(curl --silent https://api.github.com/repos/SciCrunch/NIF-Ontology/releases/latest | awk '/browser_download_url/ { print $2 }' | sed 's/"//g')
sudo unzip NIF-Ontology-*-graph-*.zip
export GRAPH_NAME=$(echo NIF-Ontology-*-graph-*/)
sudo chown -R ${USER}:${USER} $GRAPH_NAME
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
