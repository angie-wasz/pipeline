#!/bin/bash

source_dir="/astro/mwasci/awaszewski/feb_cme/cross_cal/"

#central=1352273824
#first=$((central - 200))
#last=$((central + 200))
obsid=1361512704
freq="121-132"

new_prefix="${obsid}_${freq}"

start_number=400

for file in ${source_dir}/${obsid}*t*XX-image.fits; do
	if [ -f "$file" ]; then
		
		formatted=$(printf "%04d" ${start_number})
		
		new_filename="${new_prefix}_t${formatted}-XX-image.fits"
		
		echo ${file}
		echo "${source_dir}/${new_filename}"
		echo " "
			
		((start_number++))
	fi
done 
