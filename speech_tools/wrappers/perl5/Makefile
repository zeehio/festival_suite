###########################################################################
##                                                                       ##
##                Centre for Speech Technology Research                  ##
##                     University of Edinburgh, UK                       ##
##                         Copyright (c) 2003                            ##
##                        All Rights Reserved.                           ##
##                                                                       ##
##  Permission is hereby granted, free of charge, to use and distribute  ##
##  this software and its documentation without restriction, including   ##
##  without limitation the rights to use, copy, modify, merge, publish,  ##
##  distribute, sublicense, and/or sell copies of this work, and to      ##
##  permit persons to whom this work is furnished to do so, subject to   ##
##  the following conditions:                                            ##
##   1. The code must retain the above copyright notice, this list of    ##
##      conditions and the following disclaimer.                         ##
##   2. Any modifications must be clearly marked as such.                ##
##   3. Original authors' names are not deleted.                         ##
##   4. The authors' names are not used to endorse or promote products   ##
##      derived from this software without specific prior written        ##
##      permission.                                                      ##
##                                                                       ##
##  THE UNIVERSITY OF EDINBURGH AND THE CONTRIBUTORS TO THIS WORK        ##
##  DISCLAIM ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING      ##
##  ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN NO EVENT   ##
##  SHALL THE UNIVERSITY OF EDINBURGH NOR THE CONTRIBUTORS BE LIABLE     ##
##  FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES    ##
##  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN   ##
##  AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION,          ##
##  ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF       ##
##  THIS SOFTWARE.                                                       ##
##                                                                       ##
###########################################################################
#                       Author :  Korin Richmond                          #
#                       Date   :  April 2003                              #
#-------------------------------------------------------------------------#
#           Makefile for perl bindings to speech tools                    #
#                                                                         #
#=========================================================================#

TOP=../..
DIRNAME=wrappers/perl5

SWIG_COMMAND = $(CONFIG_SWIG_COMPILER) -c -c++ -perl -shadow -Wall
SWIG_RUNTIMELIBS = -lswigpl

INTERFACE_DIRS = ../interface/ ../interface/perl5/
INTERFACE_DIRS_SWG = $(foreach d,$(INTERFACE_DIRS),-I$(d))
WRAPPERS = EST_Utterance.i EST_Relation.i EST_Item.i \
	   EST_Wave.i EST_Track.i 

vpath %.i $(INTERFACE_DIRS)

WRAPPER_SRCS = $(WRAPPERS:.i=_wrap.cc)
OBJS = $(WRAPPER_SRCS:.cc=.o)
ALL_WRAPPERS = $(WRAPPERS:.i=.so)

FILES= Makefile
ALL = .make_wrappers
LOCAL_INCLUDES = $(CONFIG_PERL_INCLUDES)
LOCAL_LIBS += $(SWIG_RUNTIMELIBS)
LOCAL_CLEAN = $(WRAPPER_SRCS) $(WRAPPERS:.i=.pm) $(ALL_WRAPPERS)

include $(TOP)/config/common_make_rules
include $(TOP)/config/rules/bin_process.mak

# implicit build rules 
$(WRAPPER_SRCS) : %_wrap.cc : %.i
	$(SWIG_COMMAND) $(INTERFACE_DIRS_SWG) -o $@ $<

$(ALL_WRAPPERS) : %.so : %_wrap.o
	$(CXX) -shared $(LIBS) -o $@ $<

.make_wrappers : $(ALL_WRAPPERS) 


