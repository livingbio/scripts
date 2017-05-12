#! /bin/bash
#
# run.sh
# Copyright (C) 2017 lizongzhe <lizongzhe@george.local>
#
# Distributed under terms of the MIT license.
#


echo $1 $2
docker run -it --rm -v `pwd`:/work -w /work markadams/chromium-xvfb-py2 python topbuzz.py $1 $2 tmp
mkdir -p $1
mv tmp `date +$1/%Y-%m-%d.csv`
