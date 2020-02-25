# Commands to generate config files and graph on the build host

``` bash
export TARGET=localhost  # set this!
export BUILD_DIR=/tmp/scigraph-build
scigraph-deploy config --local ${HOSTNAME} ${TARGET} -l ${BUILD_DIR} -z ${BUILD_DIR}
ontload graph NIF-Ontology NIF -p -b master -l ${BUILD_DIR} -z ${BUILD_DIR}
```

Example build command `ontload graph NIF-Ontology NIF -z /tmp/scigraph-build -l /tmp/scigraph-build -O SciGraph -B patch-issue-264 -b master -p`

See also [.travis.yml](https://github.com/SciCrunch/NIF-Ontology/blob/master/.travis.yml) for NIF-Ontology.

# RPM builds
The easiest way to deploy SciGraph to amazon is to build an RPM using [scigraph.spec](./scigraph.spec).
If you have a default rpmbuild setup, and you have the
[services files](https://github.com/tgbugs/tgbugs-overlay/tree/master/dev-java/scigraph-bin/files/)
from `tgbugs-overlay` in `rpmbuild/SOURCES`, you should be able to run the following.
`TODO` CI for this via the SciGraph repo?
``` bash
rpmbuild --nodeps -ba scigraph.spec &&
scp ~/rpmbuild/RPMS/scigraph*.rpm ${scigraph_host_admin}:
ssh ${scigraph_host_admin} "sudo yum -y install scigraph*.rpm""

scp services.yaml ${scigraph_host}:

scp NIF-Ontology*.zip ${scigraph_host}:
ssh ${scigraph_host} 'unzip $(ls -t NIF-Ontology-*-graph-*.zip | head -n 1)'

ssh ${scigraph_host_admin} "sudo systemctl stop scigraph"

ssh ${scigraph_host} 'unlink /var/lib/scigraph/graph
                      export GRAPH_NAME=$(ls -dt NIF-Ontology-*-graph-* | grep -v zip | head -n 1)
                      ln -sT /var/lib/scigraph/${GRAPH_NAME} /var/lib/scigraph/graph'

ssh ${scigraph_host_admin} "sudo systemctl start scigraph"
```

Post graph install stress testing is suggested to make sure that java is awake an alert.
`ontutils scigraph-stress -r 0` with `auth.get('scigraph-api')` pointing to `${scigraph_host}`.

Later installs from the 9999 version require the use of `reinstall`
instead of `install`. If you want to have more than one service
or have a different name for `services.yaml` then take a look at
`/lib/systemd/system/scigraph.service` and take what you want to
customize and put it in `/etc/systemd/system/scigraph.service.d/scigraph.conf`
(retaining the section hearders).

One alternative for systems that don't use sudo is to set an ssh key for
the SciGraph user and use that to deposit files directly. This is probably
preferable for a variety of reasons.

I will upstream the spec file to the main SciGraph repo in the near future.

# Merging commits from SciGraph/SciGraph master into upstream

https://github.com/SciCrunch/SciGraph/compare/upstream...SciGraph:master

# Old but possibly still useful if something strange comes up.
## oneshots for rhel 7 on ec2

```
sudo yum install screen vim
sudo yum install unzip  # wat
sudo yum install xorg-x11-server-Xvfb  # capitalization matters and need to enable rhel-server-optional
sudo yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm  # for nginx
sudo yum install nginx
```

### if not handled by puppet

```
sudo yum install java-1.8.0-openjdk java-1.8.0-openjdk-devel
alternatives --config java  # must set to 1.8
wget http://www.apache.org/dist/maven/maven-3/3.5.0/binaries/apache-maven-3.5.0-bin.tar.gz
sudo mv apache-maven-3.5.0-bin.tar.gz /opt/ && sudo cd /opt/ && sudo tar xvzf apache-maven-* && ln -sT apache-maven-* maven
sudo echo "export M2_HOME=/opt/maven" > /etc/profile.d/maven.sh
sudo echo "export PATH=${M2_HOME}/bin:${PATH}" >> /etc/profile.d/maven.sh
```

## etc for centos 7
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
