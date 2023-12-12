#!/bin/bash -l
#SBATCH --job-name=ips-image-1361512704
#SBATCH --output=/astro/mwasci/awaszewski/feb_cme/cross_cal/1361512704-ips-image.out
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=38
#SBATCH --time=12:00:00
#SBATCH --clusters=garrawarla
#SBATCH --partition=workq
#SBATCH --account=mwasci
#SBATCH --export=NONE
#SBATCH --gres=tmp:800g

set -euxEo pipefail

# In case of failure
# trap 'ssh mwa-solar "export DB_ASTRO_FILE=/data/awaszewski/ips/feb_cme/db//log.sqlite; python3 /data/awaszewski/ips/feb_cme/db//db_update_log.py -o 1361512704 -s Failed"' ERR
trap 'ssh mwa-solar "python3 /data/awaszewski/ips/feb_cme/db//db_update_log.py -o 1361512704 -s Failed -l /data/awaszewski/ips/feb_cme/db//log_cross.sqlite"' ERR

# Load relevant modules
module use /pawsey/mwa/software/python3/modulefiles
module use /pawsey/mwa_sles12sp5/modulefiles/python
module load wsclean mwa-reduce
module load python scipy astropy h5py

# Move to the temporary working directory on the NVMe
cd /nvmetmp
# copy across files for laer
cp /astro/mwasci/awaszewski/imstack/* ./

# Update database to set observation to processing
# ssh mwa-solar "export DB_FILE=/data/awaszewski/ips/feb_cme/db//log.sqlite; python3 /data/awaszewski/ips/feb_cme/db//db_update_log.py -o 1361512704 -j $SLURM_JOB_ID -s Processing" || echo "Log file update failed"
ssh mwa-solar "python3 /data/awaszewski/ips/feb_cme/db//db_update_log.py -o 1361512704 -j $SLURM_JOB_ID -s Processing -l /data/awaszewski/ips/feb_cme/db//log_cross.sqlite" || echo "Log file update failed"

# Move ms onto nvme
date -Iseconds
rm -rf /astro/mwasci/asvo/633479/1361512704_ch057-068.ms
cp -r /astro/mwasci/asvo/633479/1361512704_ch121-132.ms .
mv 1361512704_ch121-132.ms 1361512704121-132.ms
date -Iseconds

# Locate metafits file
if [ ! -s /astro/mwasci/jmorgan/ips/metafits/1361512704.metafits ]; then
    echo downloading 1361512704 metafits
    wget "http://ws.mwatelescope.org/metadata/fits?obs_id=1361512704" -qO 1361512704.metafits
else
    cp /astro/mwasci/jmorgan/ips/metafits/1361512704.metafits .
fi

# Copy calibration solutions
# cp /astro/mwasci/jmorgan/ips/target_cal/1361512704_121-132.bin .
# cp /astro/mwasci/jmorgan/ips/target_cal/1361512704_sols_avg.bin ./
#cp /astro/mwasci/jmorgan/ips/target_cal/1361512704_sols_avg_160.bin .
cp /astro/mwasci/awaszewski/feb_cme/2023/cal_sols_160/1361514976* ./
mv 1361514976_160.bin 1361512704_sols_avg.bin

# Change centre
date -Iseconds
#date -Iseconds
chgcentre -minw -shiftback 1361512704121-132.ms
date -Iseconds

# Apply calibration solutions
# applysolutions -nocopy  1361512704121-132.ms 1361512704_121-132.bin
applysolutions -nocopy 1361512704121-132.ms 1361512704_sols_avg.bin
date -Iseconds

# Image full standard image
wsclean -j 38 -mem 50 -name 1361512704_121-132 -pol xx,yy -size 2400 2400 -join-polarizations -niter 100000 -minuv-l 50 -nmiter 5 -mgain 0.8 -auto-threshold 2 -auto-mask 3 -taper-inner-tukey 50 -taper-gaussian 2amin -nwlayers 38 -scale 1.0amin -log-time 1361512704121-132.ms
rsync -a ./*.fits /astro/mwasci/awaszewski/feb_cme/2023/1361512704/

# Image snapshot images
wsclean -j 38 -mem 50 --name 1361512704_121-132 -subtract-model -pol xx,yy -size 2400 2400 -join-polarizations -minuv-l 50 -taper-inner-tukey 50 -taper-gaussian 2amin -nwlayers 38 -niter 100000 -auto-threshold 2 -auto-mask 3 -scale 1.0amin -log-time -no-reorder -no-update-model-required -interval 0 400 -intervals-out 400 1361512704121-132.ms

rm ./*-dirty.fits*
rm ./*-model.fits
rm ./*-psf.fits
rsync -a 1361512704*-image.fits /astro/mwasci/awaszewski/feb_cme/cross_cal/
# Make hdf5 file
date -Iseconds
python3 make_imstack2.py -vvn 400 --start=0 --suffixes=image --outfile=1361512704.hdf5 --skip_beam --allow_missing 1361512704 --bands=121-132
date -Iseconds
python3 lookup_beam_imstack.py 1361512704.hdf5 1361512704.metafits 121-132 --beam_path=/astro/mwasci/awaszewski/EoR_scin_pipeline/hdf5/gleam_xx_yy.hdf5 -v
python3 add_continuum.py --overwrite 1361512704.hdf5 1361512704 121-132 image
date -Iseconds

# Copy back relevant files to /astro
rsync -a 1361512704.hdf5 /astro/mwasci/awaszewski/feb_cme/cross_cal/
date -Iseconds

#ssh mwa-solar "python3 /data/awaszewski/ips/feb_cme/db//db_update_log.py -o 1361512704 -s Completed -l /data/awaszewski/ips/feb_cme/db//log_cross.sqlite" || echo "Log file update failed}"

# SAFE MODE
#rm -rf /astro/mwasci/asvo/633479/* 
date -Iseconds
