
source /group/clas12/packages/setup.sh
module load rcdb

d="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH=${PYTHONPATH}:${d}/lib

