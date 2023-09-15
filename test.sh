#!/bin/bash

source ./env.sh

clas12-workflow.py \
  --model          his                                                                            \
  --runGroup       rgb                                                                            \
  --tag            pr_physics0  --timelinePhysics                                                 \
  --runs           11274,11540                                                                    \
  --inputs         '/volatile/clas12/rg-b/production/recon/pass0/v29.33/mon/recon/*/*-0000?.hipo' \
  --outDir         '/volatile/clas12/users/dilks/test_workflow'                                   \
  --coatjava       '/group/clas12/packages/coatjava/10.0.2'             #       --submit

### SWIF notes ###
### submission
# swif2 import -file [JSON_FILE]
# swif2 run [WORKFLOW_NAME]
### status
# swif2 list
# swif2 status [WORKFLOW_NAME]
# swif-status.py --list
# swif-status.py
### cancel
# swif2 
