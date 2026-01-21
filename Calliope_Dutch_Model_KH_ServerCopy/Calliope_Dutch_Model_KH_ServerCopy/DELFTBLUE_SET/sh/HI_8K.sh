#!/bin/bash
#
#SBATCH --job-name=HI_8K
#SBATCH --account=education-tpm-msc-cosem
#SBATCH --partition=compute-p1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=47
#SBATCH --mem-per-cpu=3968M
#SBATCH --time=01:00:00


cd $HOME/calliope_models


module purge
module load 2024r1
module unload compiler-2024
module load gcc/12.3.0 gurobi/12.0.0 miniconda3


source /apps/generic/miniconda3/4.12.0/etc/profile.d/conda.sh
conda activate calliope


python "$HOME/calliope_models/Runfile_HI_8K.py"
