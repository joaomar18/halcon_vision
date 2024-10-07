#!/bin/bash
export LD_LIBRARY_PATH=/home/joao/MVTec/HALCON-22.11-Steady/lib/x64-linux:$LD_LIBRARY_PATH
cd /home/joao/Desktop/halcon_pulleys/
python3 main.py &
cd frontend
npm start
