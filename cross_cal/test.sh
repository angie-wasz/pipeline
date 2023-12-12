module load singularity
set -euo pipefail
obsid=1352943504
asvo=675600
year=2023

out_dir=/astro/mwasci/awaszewski/feb_cme/2023/${obsid}

central=${obsid}
first=$((central - 200))
last=$((central + 200))

export MWA_ASVO_API_KEY=3144f819-2df7-4baf-9646-3d3854c1ad6e

singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 image-template-trio.sh pipeline-2023.yaml --format=yaml \
-D obsid=${obsid} \
-D asvo=${asvo} \
--strict  -o ${out_dir}/${obsid}-image.sh
slurmid1=$(sbatch ${out_dir}/${obsid}-image.sh | cut -d " " -f 4)
  
singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 post-image-template-2023.sh pipeline-2023.yaml --format=yaml -D obsid=${obsid}  --strict  -o ${out_dir}/${obsid}-post-image.sh
sbatch --dependency=afterok:${slurmid1} ${out_dir}/${obsid}-post-image.sh
#sbatch ${out_dir}/${obsid}-post-image.sh

singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 post-image-template-2023.sh pipeline-2023.yaml --format=yaml -D obsid=${first}  --strict  -o ${out_dir}/${first}-post-image.sh
sbatch --dependency=afterok:${slurmid1} ${out_dir}/${first}-post-image.sh

singularity exec -B $PWD /astro/mwasci/jmorgan/ips_post.img jinja2 post-image-template-2023.sh pipeline-2023.yaml --format=yaml -D obsid=${last}  --strict  -o ${out_dir}/${last}-post-image.sh
sbatch --dependency=afterok:${slurmid1} ${out_dir}/${last}-post-image.sh
