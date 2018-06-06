Festival and Edinburgh Speech Tools
====================================

This is an unofficial repository for the Festival Speech Synthesis System,
the Edinburgh Speech Tools and Festvox. Official releases can be found
at http://festvox.org/

The upstream branch follows the official releases while the master branch
may include bug fixes and/or additional features. Even though Travis-CI,
coveralls and coverity are set up for continuous integration, there is
a chance that new bugs may also be introduced.

This badges can tell you the build status according to travis continuous
integration, the percentage of code covered by the testsuite and the status
of the static analysis coverity tool

[![Build Status](https://travis-ci.org/zeehio/festival_suite.svg?branch=master)](https://travis-ci.org/zeehio/festival_suite)
[![Coverage Status](https://coveralls.io/repos/zeehio/festival_suite/badge.svg?branch=master)](https://coveralls.io/r/zeehio/festival_suite?branch=master)
[![Coverity Static Analysis](https://scan.coverity.com/projects/3956/badge.svg)](https://scan.coverity.com/projects/3956)

## Changes with respect to upstream:

 - Improvements to the build system
   * Update autoconf and configure.ac
   * Allow passing options to ./configure: ./configure SHARED=2
   * Respect user custom CFLAGS
   * Easy usage of code coverage tools
   * Enable continuous integration using Travis-CI
   * Add `make distclean` to fully clean the source tree
   * Use g++ instead of gcc to compile C++ code 
 - Fix compiler warnings
   * Check return values of functions (fread, fwrite...)
   * Unused variables in functions
   * ... [Ongoing]
 - Audio
   * Allow to compile both the ALSA and PulseAudio modules simultaneously
   * Drop obsolete ESD audio module
 - Documentation
   * Improve speech tools documentation
   * man page for text2wave
   * Update EST_strcasecmp.c license to BSD-3 as allowed by the copyright owner
   * Festival documentation built in html and info formats with make doc
   * Festival reference card: Code updated from deprecated LaTeX-2.09 to LaTeX2e
 - Features
   * Provide compatibility with Festival-1.96 HTS voices
   * Avoid editing festival/lib/languages.scm to add new language
   * voice.find function to search for voices
   * Start support for >2GB files [Ongoing]
   * Do not import the whole std namespace in headers
   * Alaw support for asterisk compatibility
   * Faster text2wave
   * Rewrite some signal processing functions badly ported from Fortran

