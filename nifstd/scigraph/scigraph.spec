# you must build this with --nodeps if you are not on a RHEL alike
%define     _unitdir       /lib/systemd/system

# building on gentoo makes this /var/lib for some reason :/
%define     _localstatedir /var

%define     scigraph_user  scigraph
%define     scigraph_group %{scigraph_user}
%define     scigraph_home  %{_localstatedir}/lib/scigraph
%define     scigraph_log   %{_localstatedir}/log/scigraph

%define     name scigraph
%define     version 9999
Name:       %{name}
Version:    %{version}
Release:    0
Summary:    Web services for SciGraph, A Neo4j backed ontology store.
License:    Apache-2.0
Url:        https://github.com/SciGraph/SciGraph
BuildArch:  noarch
BuildRequires: systemd
BuildRequires: git
Requires:   bash
Requires:   java
Requires:   Xvfb
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd

# Source0: https://github.com/SciGraph/SciGraph/archive/master.tar.gz
# SourceO: https://api.github.com/repos/SciGraph/SciGraph/tarball/master
Source1: scigraph.service
Source2: xvfb.service

%description
Web services for SciGraph, A Neo4j backed ontology store.

%define MY_PN %{name}
%define SLOT %{version}
%define SERVICES_PN %{MY_PN}-services
%define SERVICES %{SERVICES_PN}-bin-%{SLOT}
%define SERVICES_SHARE /usr/share/%{SERVICES}
%define SERVICES_FOLDER /usr/share/%{SERVICES_PN}
%define SERVICES_SYSTEMD /etc/systemd/system/%{name}.service

%define CORE_PN %{MY_PN}-core
%define CORE %{CORE_PN}-bin-%{SLOT}
%define CORE_SHARE /usr/share/%{CORE}
%define CORE_FOLDER /usr/share/%{CORE_PN}
%define GRAPHLOAD_EXECUTABLE /usr/bin/scigraph-load

%prep

if [[ ! -d %{buildroot} ]]; then
	mkdir %{buildroot};
fi

%define gitroot SciGraph
if [[ ! -d %{gitroot} ]]; then
	git clone https://github.com/SciGraph/SciGraph.git
fi

%build
pushd %{gitroot}
export HASH=$(git rev-parse --short HEAD)
popd
export SERVICES_P="%{SERVICES_PN}-${HASH}"
export CORE_P="%{CORE_PN}-${HASH}"
export SERVICES_JAR="%{gitroot}/SciGraph-services/target/${SERVICES_P}.jar" 
if [[ ! -f "${SERVICES_JAR}" ]]; then
	pushd %{gitroot}
	sed -i "/<name>SciGraph<\/name>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" pom.xml
	sed -i "/<artifactId>scigraph<\/artifactId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-analysis/pom.xml
	sed -i "/<groupId>io.scigraph<\/groupId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-core/pom.xml
	sed -i "/<artifactId>scigraph<\/artifactId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-entity/pom.xml
	sed -i "/<groupId>io.scigraph<\/groupId>/{N;s/<version>.\+<\/version>/<version>${HASH}<\/version>/}" SciGraph-services/pom.xml
	mvn clean -DskipTests -DskipITs install
	pushd SciGraph-services
	mvn -DskipTests -DskipITs install
	popd
fi

%install
pushd %{gitroot}
export HASH=$(git rev-parse --short HEAD)
popd
export SERVICES_P="%{SERVICES_PN}-${HASH}"
export CORE_P="%{CORE_PN}-${HASH}"
export SERVICES_JAR="%{gitroot}/SciGraph-services/target/${SERVICES_P}.jar" 

mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}%{CORE_FOLDER}
mkdir -p %{buildroot}%{SERVICES_FOLDER}

# services
cp -Rp "%{gitroot}/SciGraph-services/target/dependency" "%{buildroot}/usr/share/scigraph-services/lib"
cp "${SERVICES_JAR}" "%{buildroot}/%{SERVICES_FOLDER}/%{SERVICES_PN}.jar"

pushd %{buildroot}/usr/share
echo CLASSPATH="\"$(find scigraph-services -type f -name "*.jar" -exec sh -c 'echo "/usr/share/$0:"' {} \; | sort)\"" > "%{buildroot}/%{SERVICES_FOLDER}/package.env"
popd

install -p -D -m 644 %{SOURCE1} %{buildroot}/%{_unitdir}/scigraph.service
install -p -D -m 644 %{SOURCE2} %{buildroot}/%{_unitdir}/xvfb.service

# core
cp "%{gitroot}/SciGraph-core/target/${CORE_P}-jar-with-dependencies.jar" "%{buildroot}%{CORE_FOLDER}/%{CORE_PN}.jar"

echo '#!/usr/bin/env sh' > "%{buildroot}/%{GRAPHLOAD_EXECUTABLE}"
# FIXME JAVA_HOME ??
echo "/usr/bin/java -cp \"%{CORE_FOLDER}/%{CORE_PN}.jar\" io.scigraph.owlapi.loader.BatchOwlLoader"' $@' >> "%{buildroot}%{GRAPHLOAD_EXECUTABLE}"
chmod 0755 "%{buildroot}%{GRAPHLOAD_EXECUTABLE}"

%pre
getent group %{scigraph_group} > /dev/null || groupadd -r %{scigraph_group}
getent passwd %{scigraph_user} > /dev/null || \
    useradd -r -d %{scigraph_home} -g %{scigraph_group} \
    -s /sbin/nologin -c "SciGraph services" %{scigraph_user}
if [[ ! -d %{scigraph_log} ]]; then
	mkdir %{scigraph_log}  # owner?
	chown %{scigraph_user}:%{scigraph_group} %{scigraph_log}
fi

%post
systemctl enable xvfb
systemctl enable scigraph

%clean
rm -rf %{buildroot}

%files
%{SERVICES_FOLDER}/*
%{CORE_FOLDER}/*
%{GRAPHLOAD_EXECUTABLE}
%{_unitdir}/scigraph.service
%{_unitdir}/xvfb.service

%changelog
# let skip this for now
