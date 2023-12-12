#!/bin/bash

set -euxo pipefail

obsid=$1
asvo=$2
db_dir=$3
garra_dir=$4
year=$5

if [ -z "$obsid" ] | [ -z "$asvo" ]; then
	echo "ERROR OBSID or ASVO ID were not passed correctly"
else 
	python3 ${garra_dir}/gen_slurm_cal.py -o ${obsid} -a ${asvo} -g ${garra_dir} --db ${db_dir} -y ${year}

	sbatch ${garra_dir}/${year}/${obsid}/${obsid}-cal-job.sh
fi
