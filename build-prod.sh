#!/bin/sh

rm dist/*
python3 setup.py sdist bdist_wheel

twine check dist/*

twine upload dist/*
