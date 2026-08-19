#! /bin/bash

VER=3.14

if test -z $VIRTUAL_ENV; then
	test -d venv || python$VER -m venv venv
	source venv/bin/activate
	export VIRTUAL_ENV
fi

sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-ron tesseract-ocr-eng

pip install -r requirements.txt
python$VER app.py &
