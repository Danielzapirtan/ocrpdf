#! /bin/bash

VER=3.12

if test -z $VIRTUAL_ENV; then
	test -d venv || python$VER -m venv venv
	source venv/bin/activate
	export VIRTUAL_ENV
fi

brew update
brew install tesseract-ocr tesseract-ocr-ron tesseract-ocr-eng

pip install -r requirements.txt
python$VER app.py &
