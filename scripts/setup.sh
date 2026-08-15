#!/bin/sh
set -eu

cd /code/frontend
npm install
npm run build

cd /code/backend
pip install -r requirements.txt
