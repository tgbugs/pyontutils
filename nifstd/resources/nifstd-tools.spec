# you must build this with --nodeps if you are not on a RHEL alike
%define     _unitdir       /lib/systemd/system
%define     _etcdir        /etc/systemd/system

# building on gentoo makes this /var/lib for some reason :/
%define     _localstatedir /var

%define     nt_user  nifstd-tools
%define     nt_group %{nifstd-tools}
%define     nt_home  %{_localstatedir}/lib/nifstd-tools
%define     nt_log   %{_localstatedir}/log/nifstd-tools

%define     name nifstd-tools
%define     version 9999
Name:       %{name}
Version:    %{version}
Release:    0
Summary:    utilities for working with the NIF ontology
License:    MIT
Url:        https://github.com/tgbugs/pyontutils/tree/nifstd
BuildArch:  noarch
BuildRequires: systemd
BuildRequires: git
Requires:   gcc
Requires:   bash
Requires:   nginx
Requires:   python3
Requires:   python3-devel
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd

Source1: ontree.socket
Source2: ontree.service
Source3: ontree.confd
Source4: ontree.tmp

%description
curation workflow automation and coordination

%prep

if [[ ! -d %{buildroot} ]]; then
	mkdir %{buildroot};
fi

%define gitroot pyontutils
if [[ ! -d %{gitroot} ]]; then
	git clone https://github.com/tgbugs/pyontutils.git
fi

%build
#pushd %{gitroot}
#python3 setup.py bdist_wheel
#%py3_build
 
%install
install -p -D -m 644 %{SOURCE1} %{buildroot}/%{_unitdir}/ontree.socket
install -p -D -m 644 %{SOURCE2} %{buildroot}/%{_unitdir}/ontree.service
install -p -D -m 600 %{SOURCE3} %{buildroot}/%{_etcdir}/ontree.service.d/env.conf
install -p -D -m 644 %{SOURCE4} %{buildroot}/etc/tmpfiles.d/ontree.conf
#%py3_install

%pre
getent group %{nt_group} > /dev/null || groupadd -r %{nt_group}
getent passwd %{nt_user} > /dev/null || \
    useradd -r -m -d %{nt_home} -g %{nt_group} \
    -s /bin/bash -c "nifstd-tools services" %{nt_user}
if [[ ! -d %{ontree_log} ]]; then
	mkdir %{ontree_log}  # owner?
	chown %{nt_user}:%{nt_group} %{ontree_log}
fi

%post
systemd-tmpfiles --create
systemctl enable ontree
#systemctl enable nginx

%clean
rm -rf %{buildroot}

%files
%{_unitdir}/ontree.socket
%{_unitdir}/ontree.service
%{_etcdir}/ontree.service.d/env.conf
/etc/tmpfiles.d/ontree.conf
#/etc/nginx/nginx.conf
#/etc/nginx/scibot.conf

%changelog
# skip this for now
