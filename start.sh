module load singularity
set -euo pipefail
obsid=$1
asvo=$2
year=$3

out_dir=/astro/mwasci/awaszewski/feb_cme/2023/${obsid}

singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 image-template-2023.sh pipeline-2023.yaml --format=yaml \
-D obsid=${obsid} \
-D asvo=${asvo} \
--strict  -o ${out_dir}/${obsid}-image.sh
slurmid1=$(sbatch ${out_dir}/${obsid}-image.sh | cut -d " " -f 4)
  
singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 post-image-template-2023.sh pipeline-2023.yaml --format=yaml -D obsid=${obsid}  --strict  -o ${out_dir}/${obsid}-post-image.sh
sbatch --dependency=afterok:${slurmid1} ${out_dir}/${obsid}-post-image.sh
#sbatch ${out_dir}/${obsid}-post-image.sh
