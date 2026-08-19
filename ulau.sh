#! /bin/bash

pkill -kill python3.14

bash utest.sh &>/tmp/ocrpdf.log
echo "ocrpdf launched"
echo "See it on port 5036"
echo "Launch terminated"
