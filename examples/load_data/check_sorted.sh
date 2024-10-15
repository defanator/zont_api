#!/bin/sh

if [ ! -d "data" ]; then
    exit 0
fi

trap "rm -f tmp.$$" EXIT

for f in $(find data/ -type f -name "*.csv"); do
    cat $f | sort -k1 -n -t ',' >tmp.$$
    diff -u $f tmp.$$
done
