#!/bin/bash -l
#SBATCH --job-name=make-hdf5-beam
#SBATCH --output=/astro/mwasci/awaszewski/feb_cme/beam.out
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=38
#SBATCH --time=01:00:00
#SBATCH --clusters=garrawarla
#SBATCH --partition=workq
#SBATCH --account=mwasci
#SBATCH --export=NONE

set -euxEo pipefail

# Load relevant modules
module use /pawsey/mwa/software/python3/modulefiles
module use /pawsey/mwa_sles12sp5/modulefiles/python
module load python scipy astropy h5py

file=/astro/mwasci/awaszewski/feb_cme/2023/

while read -r line; do
	hdf5=${file}/${line}/${line}_beam.hdf5
	if [ -f ${hdf5} ]; then
		rm ${hdf5}
	fi
	python3 make_beam_only.py ${file}/${line}/${line}.hdf5 ${file}/${line}/${line}_beam.hdf5 -f 121-132
#done < full_complete.txt
done < ../first_calibrate.txt
