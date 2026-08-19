#! /bin/bash

pkill -kill python3.12

bash test.sh &>/tmp/ocrpdf.log
echo "ocrpdf launched"
echo "See it on port 5036"
echo "Launch terminated"
