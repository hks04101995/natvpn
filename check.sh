#! /bin/sh

s1=`echo "MjE4" | base64 -d`
s2=`echo "aW4x" | base64 -d`

grep -i ${s1} *.py
grep -i ${s2} *.py
