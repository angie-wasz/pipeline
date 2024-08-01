#!/usr/bin/env python3

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--obsid", type=int, required=True)
parser.add_argument("-a", "--asvo", type=int, required=True)
parser.add_argument("-y", "--year", type=int, required=True)
parser.add_argument("-d", "--dir", type=str, required=True)
args = parser.parse_args()

#Pipeline configuration
tmp_dir = "/nvmetmp"
pipeline_dir = "/scratch/mwasci/awaszewski/pipeline/"
metafits_dir = "scratch/mwasci/awaszewski/pipeline/"
DB_dir = "/data/awaszewski/ips/db/"
n_core = 38
year = args.year
freq = "121-132"
pols:
        - XX
        - YY
container = "/scratch/mwasci/awaszewski/ips_post.img"
mem = 50

# Imaging parameters
niter = 100000
minuv_l = 50
taper_inner_tukey = 50
size = 2400
scale = "1.0amin"
taper = "2amin"
nmiter = 5
mgain = 0.8
automask = 3
autothresh = 2
interval_start = 0
interval_stop = 400

def gen_image(obsid, asvo):
    string=f"""#!/bin/bash -l
    #SBATCH --job-name=ips-image-{{obsid}}
    #SBATCH --output={{pipeline_dir}}/{{year}}/{{obsid}}/{{obsid}}-image.out
    #SBATCH --nodes=1
    #SBATCH --ntasks-per-node={{n_core}}
    #SBATCH --time=06:00:00
    #SBATCH --clusters=garrawarla
    #SBATCH --partition=workq
    #SBATCH --account=mwasci
    #SBATCH --export=NONE
    #SBATCH --gres=tmp:800g

    set -euxEo pipefail

    # In case of failure
    trap 'ssh mwa-solar "python3 {{DB_dir}}/db_update_log.py -o {{obsid}} -s Failed -l {{DB_dir}}/log_image.sqlite"' ERR

    # Load relevant modules
    module use /pawsey/mwa/software/python3/modulefiles
    module use /pawsey/mwa_sles12sp5/modulefiles/python
    module load wsclean mwa-reduce
    module load python scipy astropy h5py

    # Move to the temporary working directory on the NVMe
    cd {{tmp_dir}}
    # copy across files for later
    cp /scratch/mwasci/awaszewski/imstack/* ./

    # Update database to set observation to processing
    ssh mwa-solar "python3 {{DB_dir}}/db_update_log.py -o {{obsid}} -j $SLURM_JOB_ID -s Processing -l {{DB_dir}}/log_image.sqlite" || echo "Log file update failed"

    # Move ms onto nvme
    date -Iseconds
    cp -r /scratch/mwasci/asvo/{{asvo}}/{{obsid}}_ch121-132.ms .
    mv {{obsid}}_ch121-132.ms {{obsid}}{{freq}}.ms
    date -Iseconds

    # Locate metafits file
    wget "http://ws.mwatelescope.org/metadata/fits?obs_id={{obsid}}" -q0 {{obsid}}.metafits
    rsync -av {{obsid}}.metafits {{pipeline_dir}}/{{year}}/{{obsid}}/

    # Copy calibration solutions
    rsync -a mwa-solar:/data/awaszewski/ips/pipeline/{{year}}/central/cal_sols_160/{{obsid}}_160.bin ./
    mv {{obsid}}_160.bin {{obsid}}_sols_avg.bin

    # Change centre
    date -Iseconds
    chgcentre -minw -shiftback {{obsid}}{{freq}}.ms
    date -Iseconds

    # Apply calibration solutions
    applysolutions {{obsid}}{{freq}}.ms {{obsid}}_sols_avg.bin
    date -Iseconds

    # Image full standard image
    wsclean -j {{n_core}} -mem {{mem}} -name {{obsid}}_{{freq}} -pol xx,yy -size {{size}} {{size}} -join-polarizations -niter {{niter}} -minuv-l {{minuv_l}} -nmiter {{nmiter}} -mgain {{mgain}} -auto-threshold {{autothresh}} -auto-mask {{automask}} -taper-inner-tukey {{taper_inner_tukey}} -taper-gaussian {{taper}} -nwlayers {{n_core}} -scale {{scale}} -log-time {{obsid}}{{freq}}.ms

    # Image snapshot images
    wsclean -j {{n_core}} -mem {{mem}} --name {{obsid}}_{{freq}} -subtract-model -pol xx,yy -size {{size}} {{size}} -join-polarizations -minuv-l {{minuv_l}} -taper-inner-tukey {{taper_inner_tukey}} -taper-gaussian {{taper}} -nwlayers {{n_core}} -niter {{niter}} -auto-threshold {{autothresh}} -auto-mask {{automask}} -scale {{scale}} -log-time -no-reorder -no-update-model-required -interval {{interval_start}} {{interval_stop}} -intervals-out {{interval_stop-interval_start}} {{obsid}}{{freq}}.ms

    rm ./*-dirty.fits*
    rm ./*-model.fits
    rm ./*-psf.fits
    # Make hdf5 file
    date -Iseconds
    python3 make_imstack2.py -vvn 400 --start=0 --suffixes=image --outfile={{obsid}}.hdf5 --skip_beam --allow_missing {{obsid}} --bands={{freq}}
    date -Iseconds
    python3 lookup_beam_imstack.py {{obsid}}.hdf5 {{obsid}}.metafits {{freq}} --beam_path=/astro/mwasci/awaszewski/EoR_scin_pipeline/hdf5/gleam_xx_yy.hdf5 -v
    python3 add_continuum.py --overwrite {{obsid}}.hdf5 {{obsid}} {{freq}} image
    date -Iseconds

    # Copy back relevant files to /astro
    rm *-t0*
    rsync -av ./*.fits {{pipeline_dir}}/{{year}}/{{obsid}}/
    rsync -av {{obsid}}.hdf5 {{pipeline_dir}}/{{year}}/{{obsid}}/
    date -Iseconds

    #rm -rf /astro/mwasci/asvo/{{asvo}}/* 
    date -Iseconds
    """
    return string

def gen_post_image(obsid, asvo):
    string="""#!/bin/bash -l
    #SBATCH --job-name=ips-post-image-{{obsid}}
    #SBATCH --output={{pipeline_dir}}/{{year}}/{{obsid}}/{{obsid}}-post-image.out
    #SBATCH --nodes=1
    #SBATCH --ntasks-per-node={{n_core}}
    #SBATCH --time=3:00:00
    #SBATCH --clusters=garrawarla
    #SBATCH --partition=workq
    #SBATCH --account=mwasci
    #SBATCH --export=NONE
    #SBATCH --gres=tmp:100g

    set -exE

    ##########
    # Preamble
    ##########

    # Load relevant modules
    module load singularity

    # Incase of failure
    trap 'ssh mwa-solar "python3 {{DB_dir}}/db_update_log.py -o {{obsid}} -s Failed -l {{DB_dir}}/log_image.sqlite"' ERR

    # Move to the temporary working directory on the NVMe
    cd {{tmp_dir}}
    cp {{pipeline_dir}}/pipeline_scripts/* .

    # Move relevant files onto nvme
    date -Iseconds
    rsync -a {{pipeline_dir}}/{{year}}/{{obsid}}/{{obsid}}.hdf5 \
        {% for p in pols %}{{pipeline_dir}}/{{year}}/{{obsid}}/{{obsid}}_{{freq}}-{{p}}-image.fits \
        {% endfor %} ./
    date -Iseconds

    # Locate metafits file
    if [ ! -s {{pipeline_dir}}/{{year}}/{{obsid}}/{{obsid}}.metafits ]; then
        echo downloading {{obsid}} metafits
        wget http://ws.mwatelescope.org/metadata/fits?obs_id={{obsid}} -O {{obsid}}.metafits
    else
        cp {{pipeline_dir}}/{{year}}/{{obsid}}/{{obsid}}.metafits ./
    fi

    #########################
    # Continuum and abs scale
    #########################
    date -Iseconds

    {% for pol in pols %}
    singularity exec -B $PWD {{container}} BANE --noclobber --compress {{obsid}}_{{freq}}-{{pol}}-image.fits
    singularity exec -B $PWD {{container}} aegean --autoload --seedclip=5 --floodclip=4 --table {{obsid}}_{{freq}}-{{pol}}-image.vot  {{obsid}}_{{freq}}-{{pol}}-image.fits
    singularity exec -B $PWD {{container}} python3 make_cat.py --pol={{pol}} {{obsid}}.hdf5 {{obsid}}_{{freq}}-{{pol}}-image_comp.vot {{obsid}}_{{freq}}-{{pol}}-image.vot -o {{obsid}}
    singularity exec -B $PWD {{container}} python3 match_calibration.py {{obsid}}_{{freq}}-{{pol}}-image.vot {{pipeline_dir}}/catalogs/ips_continuum_cal.fits {{obsid}}_{{freq}}-{{pol}}-image_cal.vot
    {% endfor %}

    singularity exec -B $PWD {{container}} python3 abs_scale.py {{obsid}} {{freq}}
    date -Iseconds

    #################################
    # Moment images and measure noise
    #################################
    mypath=$PATH
    mypythonpath=$PYTHONPATH
    module use /pawsey/mwa_sles12sp5/modulefiles/python
    module load python numpy scipy mpi4py astropy h5py
    srun --export=all -N 1 -n {{n_core}} python3 moment_image.py {{obsid}}.hdf5 -f {{freq}} --filter_lo --filter_hi --trim=900 --pol --n_moments=2
    rm *moments.hdf5
    export PATH=$mypath
    export PYTHONPATH=$mypythonpath
    singularity exec -B $PWD {{container}} python3 measure_noise.py {{obsid}}

    #########################
    # Get final files
    #########################
    singularity exec -B $PWD {{container}} python3 get_continuum.py --sigma {{obsid}}.hdf5 {{freq}} {{obsid}}_{{freq}}-image.fits
    singularity exec -B $PWD {{container}} BANE --noclobber --compress {{obsid}}_{{freq}}-image.fits
    singularity exec -B $PWD {{container}} aegean --autoload --seedclip=4 --floodclip=3 --table {{obsid}}_{{freq}}-image.vot {{obsid}}_{{freq}}-image.fits

    mypath=$PATH
    mypythonpath=$PYTHONPATH
    module use /pawsey/mwa_sles12sp5/modulefiles/python
    module load python numpy scipy mpi4py astropy h5py
    srun --export=all -N 1 -n {{n_core}} python3 moment_image.py {{obsid}}.hdf5 -f {{freq}} --filter_lo --filter_hi
    export PATH=$mypath
    export PYTHONPATH=$mypythonpath

    singularity exec -B $PWD {{container}} BANE --noclobber --compress {{obsid}}_{{freq}}_image_moment2.fits
    singularity exec -B $PWD {{container}} aegean --autoload --seedclip=4 --floodclip=3 --table {{obsid}}_{{freq}}_image_moment2.vot {{obsid}}_{{freq}}_image_moment2.fits

    python3 make_beam_only.py {{obsid}}.hdf5 {{obsid}}_beam.hdf5 -f 121-132

    # Copy back relevant files to /astro
    date -Iseconds
    rsync -a {{obsid}}.hdf5 \
        {{obsid}}_beam.hdf5 \
        {% for i in range(1, 5) %}{{obsid}}_{{freq}}_image_moment{{i}}.fits \
        {% endfor %}{{obsid}}_{{freq}}_image_moment2_comp.vot \
        {{obsid}}_{{freq}}-image.fits \
        {{obsid}}_{{freq}}-image_bkg.fits \
        {{obsid}}_{{freq}}-image_rms.fits \
        {{obsid}}_{{freq}}_image_moment2_bkg.fits \
        {{obsid}}_{{freq}}_image_moment2_rms.fits \
        {{obsid}}_{{freq}}-image_comp.vot \
        {{pipeline_dir}}/{{year}}/{{obsid}}/
    date -Iseconds

    # Update database to show that observation has finished processing
    # ssh mwa-solar "export DB_FILE={{DB_dir}}/log.sqlite; python3 {{DB_dir}}/db_update_log.py -o {{obsid}} -s Completed" || echo "Log file update failed"
    ssh mwa-solar "python3 {{DB_dir}}/db_update_log.py -o {{obsid}} -s Completed -l {{DB_dir}}/log_image.sqlite" || echo "Log file update failed}"	
    """
    return string

filename_1 = f"{pipeline_dir}/{year}/{args.obsid}/{args.obsid}-image.sh"
with open(filename_1, "w+") as f:
    f.write(gen_image(args.obsid, args.asvo))

filename_2 = f"{pipeine_dir}/{year}/{args.obsid}/{args.obsid}-post-image.sh"
with open(filename_2, "w+") as f:
    f.write(gen_post_image(args.obsid, args.asvo))
