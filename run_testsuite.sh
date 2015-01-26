#!/bin/bash
# -e: stop on the first command that returns error
# -v: print each command on screen
set -ev

run="y"

if [ "${COVERITY_SCAN_BRANCH}" = "1" ]; then
  run="n"
fi

while getopts ":f" opt; do
  case $opt in
    f)
      run="y"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      ;;
  esac
done


if [ "$run" = "y" ]; then
   BASEDIR=`pwd`
   cd "speech_tools"
   autoconf
   ./configure --enable-profile=gcov #--with-pulseaudio
   make
   make test
   cd "$BASEDIR/speech_tools/doc"
   make doc
   cd "$BASEDIR"
   cd "festival"
   ./configure
   make
   cd ".."
   # Download CMU POSLEX and OALD needed for tests:
   if [ ! -f festlex_CMU.tar.gz ]; then
      wget http://www.festvox.org/packed/festival/2.4/festlex_CMU.tar.gz
   fi
   tar xzf festlex_CMU.tar.gz
   if [ ! -f festlex_POSLEX.tar.gz ]; then
      wget http://www.festvox.org/packed/festival/2.4/festlex_POSLEX.tar.gz
   fi
   tar xzf festlex_POSLEX.tar.gz
   if [ ! -f festlex_OALD.tar.gz ]; then
   wget http://www.festvox.org/packed/festival/2.4/festlex_OALD.tar.gz
   fi
   tar xzf festlex_OALD.tar.gz
   # Voices:
   if [ ! -f festvox_kallpc16k.tar.gz ]; then
       wget http://www.festvox.org/packed/festival/2.4/voices/festvox_kallpc16k.tar.gz
   fi
   tar xzf festvox_kallpc16k.tar.gz
   if [ ! -f festvox_rablpc16k.tar.gz ]; then
      wget http://www.festvox.org/packed/festival/2.4/voices/festvox_rablpc16k.tar.gz
   fi
   tar xzf festvox_rablpc16k.tar.gz
   if [ ! -f festvox_cmu_us_rms_cg.tar.gz ]; then
      wget http://www.festvox.org/packed/festival/2.4/voices/festvox_cmu_us_rms_cg.tar.gz
   fi
   tar xzf festvox_cmu_us_rms_cg.tar.gz
   if [ ! -f festvox_cmu_us_awb_cg.tar.gz ]; then
      wget http://www.festvox.org/packed/festival/2.4/voices/festvox_cmu_us_awb_cg.tar.gz
   fi
   tar xzf festvox_cmu_us_awb_cg.tar.gz
   if [ ! -f festvox_cmu_us_slt_cg.tar.gz ]; then
      wget http://www.festvox.org/packed/festival/2.4/voices/festvox_cmu_us_slt_cg.tar.gz
   fi
   tar xzf festvox_cmu_us_slt_cg.tar.gz
   cd festival
   make test
   cd "$BASEDIR/festvox"
   ./configure
   make
fi

