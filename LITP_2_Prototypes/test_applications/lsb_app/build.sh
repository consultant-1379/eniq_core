#!/bin/bash

basename=basename
cat=cat
cp=cp
echo=echo
find=find
mkdir=mkdir
rm=rm
sed=sed
rpmbuild=rpmbuild
getopt=getopt

_thisdir=$PWD/build
_topdir=${_thisdir}/binary_build
_builddir=${_topdir}/BUILD
_rpmdir=${_topdir}/RPMS
_sourcedir=${_topdir}/SOURCES
_specdir=${_topdir}/SPECS
_srcrpmdir=${_topdir}/SRPMS

BUILDROOT=${_sourcedir}
PREFIX=/opt/ericsson/test_lsb_app


clean()
{
	${echo} "Cleaning previous build ..."
	$rm -rf ${_topdir}
	$rm -rf ${_bundledir_}
}


build_rpm()
{
	$echo "Generating RPM ..."
	$rm -rf $_topdir
	$mkdir -p $_builddir
	$mkdir -p $_rpmdir
	$mkdir -p $_sourcedir
	$mkdir -p $_specdir
	$mkdir -p $_srcrpmdir

	_version_=`$cat version`
	_version_=$((_version_+1))
	$echo $_version_ > version

	$mkdir -p ${BUILDROOT}/${PREFIX}/bin
	$mkdir -p ${BUILDROOT}/etc/init.d/
	
	$cp bin/test_lsb_app ${BUILDROOT}/${PREFIX}/bin/
  $cp bin/test_lsb_app ${BUILDROOT}/etc/init.d/
	$sed -e "s|%_prefix_dir_%|$PREFIX|g;s|%_version_%|1.0.${_version_}|g" test_lsb_app.spec > ${_specdir}/test_lsb_app.spec

	local _output_=
	_output_=`$rpmbuild -bb \
		--buildroot=${BUILDROOT} \
		--define "_topdir ${_topdir}" \
		--define "_builddir ${_builddir}" \
		--define "_rpmdir ${_rpmdir}" \
		--define "_sourcedir ${_sourcedir}" \
		--define "_specdir ${_specdir}" \
		--define "_srcrpmdir ${_srcrpmdir}" \
		${_specdir}/test_lsb_app.spec 2>&1`
	_rc_=${?}
	if [ ${_rc_} -ne 0 ] ; then
		${echo} "${_output_}"
		exit ${_rc_}
	fi
  _rpm_=`${find} ${_rpmdir} -name "test_lsb_app-*.rpm" -type f -print`
	_name_=`${basename} ${_rpm_}`
	${cp} ${_rpm_} .
	${echo} "Built ${_name_}"
}


usage()
{
	echo "$0 [--clean|-c] [--build|-b]"
}

if [ $# -eq 0 ] || [ "${1}" == "-h" ] || [ "${1}" == "-help" ]; then
  usage
  exit 0
fi

# Execute getopt
ARGS=`getopt -o "cb" \
  -l "clean,build" -n "$0" -- "$@"`
#Bad arguments
if [ $? -ne 0 ] ; then
  usage
  exit 2
fi

# A little magic
eval set -- "$ARGS"
_CLEAN_=0
_BUILD_=0
while true ; do
  case "$1" in
    --clean|-c)
      _CLEAN_=1
      shift
      ;;
    --build|-b)
      _BUILD_=1
      shift
      ;;
    --)
      shift
      break;;
	esac
done


if [ ${_CLEAN_} -eq 1 ] ; then
	clean
fi
if [ ${_BUILD_} -eq 1 ] ; then
	build_rpm
fi
