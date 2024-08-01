#module load singularity
set -euo pipefail
obsid=$1
asvo=$2
year=$3


#out_dir=/astro/mwasci/awaszewski/feb_cme/2023/${obsid}
out_dir=/scratch/mwasci/awaszewski/pipeline/${year}/${obsid}

python3 gen_slurm_image.py -o ${obsid} -a ${asvo} -y ${year}


#singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 image-template-2023.sh pipeline-2023.yaml --format=yaml \
#-D obsid=${obsid} \
#-D asvo=${asvo} \
#--strict  -o ${out_dir}/${obsid}-image.sh
#slurmid1=$(sbatch ${out_dir}/${obsid}-image.sh | cut -d " " -f 4)

#singularity exec -B $PWD /scratch/mwasci/awaszewski/ips_post.img jinja2 imaging_scripts/image-template.sh pipeline-info.yaml --format=yaml \
#	-D obsid=${obsid} \
#	-D asvo=${asvo} \
#	--strict -o ${out_dir}/${obsid}-image.sh
slurmid1=$(sbatch ${out_dir}/${obsid}-image.sh | cut -d " " -f 4)


#singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 post-image-template-2023.sh pipeline-2023.yaml --format=yaml -D obsid=${obsid}  --strict  -o ${out_dir}/${obsid}-post-image.sh
#sbatch --dependency=afterok:${slurmid1} ${out_dir}/${obsid}-post-image.sh
#sbatch ${out_dir}/${obsid}-post-image.sh

#singularity exec -B $PWD /scratch/mwasci/awaszewski/ips_post.img jinja2 imaging_scripts/post-image-template.sh pipeline-info.yaml --format=yaml \
#	-D obsid=${obsid} \
#	--strict -o ${out_die}/${obsid}-post-image.sh
slurmid2=$(sbatch --dependency=afterok:${slurmid1} ${out_dir}/${obsid}-post-image.sh)


# Add _beam.hdf5 creation in the post imaging