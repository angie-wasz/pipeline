#!/usr/bin/env python3

import sys, argparse

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--obsid", type=int, required=True)
parser.add_argument("-a", "--asvo", type=int, required=True)
parser.add_argument("-g", "--garra", type=str, required=True)
parser.add_argument("--db", type=str, required=True)
parser.add_argument("-y", "--year", type=int, required=True)
args = parser.parse_args()

files80 = "{057..068}"
#files162 = "{121..132}"
files162 = "{109..132}"
#files162 = "{157..180}"

obsnum = args.obsid
garra_dir = args.garra
year = args.year

filename = f"{garra_dir}/{year}/{obsnum}/{obsnum}-cal-job.sh"
f = open(filename,"w+")


def gen_slurm(obsid, asvo, files80, files162, garra, db, year):
	string= f"""#!/bin/bash -l
#SBATCH --job-name=cal-{obsid}
#SBATCH --output={garra}/{year}/{obsid}/{obsid}-cal.out
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=40
#SBATCH --time=01:00:00
#SBATCH --clusters=garrawarla
#SBATCH --partition=gpuq
#SBATCH --account=mwasci
#SBATCH --export=NONE
#SBATCH --gres=gpu:1,tmp:850g

set -eux

trap 'ssh mwa-solar "python3 {db}/db_update_log.py -o {obsid} -s Failed -l {db}/log_cal.sqlite"' ERR

cd /nvmetmp

module use /pawsey/mwa/software/python3/modulefiles
module load hyperdrive

ssh mwa-solar "python3 {db}/db_update_log.py -o {obsid} -j $SLURM_JOB_ID -s Processing -l {db}/log_cal.sqlite"

command -V hyperdrive

files=/astro/mwasci/asvo/{asvo}/
cp $files* ./

# GET MODEL
model=/astro/mwasci/awaszewski/feb_cme/{year}/{obsid}/{obsid}_skymodel.txt

# CALIBRATION
#for calibrators
#hyperdrive di-calibrate -vv -d ./*ch{files162}*.fits ./*.metafits -s $model --uvw-min 301m --uvw-max 2600m -o {obsid}_sols.fits --max-iterations 300 --stop-thresh 1e-20 --freq-average 80kHz
#for normal
hyperdrive di-calibrate -d ./*ch{files162}*.fits ./*.metafits $model --uvw-min 130m --uvw-max 2600m -o {obsid}_sols.fits

hyperdrive plot-solutions {obsid}_sols.fits

rsync -av {obsid}_sols.fits {garra}/{year}/{obsid}/
rsync -av {obsid}*.png {garra}/{year}/{obsid}/

ssh mwa-solar "python3 {db}/db_update_log.py -o {obsid} -s Completed -l {db}/log_cal.sqlite"

rm *{obsid}*
"""
	return string

f.write(gen_slurm(args.obsid, args.asvo, files80, files162, args.garra, args.db, args.year))
f.close()
