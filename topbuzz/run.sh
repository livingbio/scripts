#! /bin/bash
#
# run.sh
# Copyright (C) 2017 lizongzhe <lizongzhe@george.local>
#
# Distributed under terms of the MIT license.
#

docker run --rm -v `pwd`:/work -w /work markadams/chromium-xvfb-py2 python topbuzz.py $1 $2 $3
