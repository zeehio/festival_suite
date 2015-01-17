#!/bin/bash
# -e: stop on the first command that returns error
# -v: print each command on screen
set -ev

if [ ${COVERITY_SCAN_BRANCH} != 1 ]; then
   BASEDIR=`pwd`
   cd "speech_tools"
   ./configure #--enable-profile=gcov --with-pulseaudio
   make
   make test
   cd "$BASEDIR"
   cd "festival"
   ./configure
   make
   cd ".."
   # Download CMU POSLEX and OALD needed for tests:
   wget http://www.festvox.org/packed/festival/2.4/festlex_CMU.tar.gz
   tar xzf festlex_CMU.tar.gz
   wget http://www.festvox.org/packed/festival/2.4/festlex_POSLEX.tar.gz
   tar xzf festlex_POSLEX.tar.gz
   wget http://www.festvox.org/packed/festival/2.4/festlex_OALD.tar.gz
   tar xzf festlex_OALD.tar.gz
   # Voices:
   wget http://www.festvox.org/packed/festival/2.4/voices/festvox_kallpc16k.tar.gz
   tar xzf festvox_kallpc16k.tar.gz
   wget http://www.festvox.org/packed/festival/2.4/voices/festvox_rablpc16k.tar.gz
   tar xzf festvox_rablpc16k.tar.gz
   wget http://www.festvox.org/packed/festival/2.4/voices/festvox_cmu_us_rms_cg.tar.gz
   tar xzf festvox_cmu_us_rms_cg.tar.gz
   wget http://www.festvox.org/packed/festival/2.4/voices/festvox_cmu_us_awb_cg.tar.gz
   tar xzf festvox_cmu_us_awb_cg.tar.gz
   wget http://www.festvox.org/packed/festival/2.4/voices/festvox_cmu_us_slt_cg.tar.gz
   tar xzf festvox_cmu_us_slt_cg.tar.gz
   cd festival
   make test
fi

