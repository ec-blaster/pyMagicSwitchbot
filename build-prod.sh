#!/bin/sh

pip install --quiet sdist
pip install --quiet wheel
pip install --quiet twine

rm dist/*
python3 setup.py sdist bdist_wheel

twine check dist/*

twine upload dist/*
