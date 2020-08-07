#!/usr/bin/env python
import re,sys,subprocess,argparse,logging
from SwifStatus import getWorkflowNames,deleteWorkflow,SWIF_PROBLEMS
from CLAS12SwifStatus import CLAS12SwifStatus,getHeader
from Matcher import matchAny

logging.basicConfig(level=logging.WARNING,format='%(levelname)-9s[%(name)-15s] %(message)s')
logger=logging.getLogger(__name__)

# TODO: switch to JSON format (didn't know it was available at the time)

PROBLEMS=SWIF_PROBLEMS[:]
PROBLEMS.append('ANY')

def processWorkflow(workflow,args):

  status = CLAS12SwifStatus(workflow,args)

#  if args.joblogs:
#    if status.isComplete() and status.isPreviousComplete():
#      status.moveJobLogs()

  if args.missing:
    print('\nMissing outputs in '+workflow+':')
    print(('\n'.join(status.findMissingOutputs())))
    return

  if args.stats:
    print('\nStatus summary for '+workflow+':')
    print(status),
    return

  # print details of jobs with problems:
  if args.problems:
    status.showPersistentProblems()

  # if retrying or abandoning, only print status if problems exist:
  if len(args.abandon)>0 or args.retry or len(args.clas12mon)>0:

    if len(args.abandon)>0:
      res = status.abandonProblems(args.abandon)
      if len(res)>0 and not args.quiet:
        print(status.getPrettyStatus())
        print(res)

    if args.retry:
      res = status.retryProblems()
      if len(res)>0 and not args.quiet:
        print(status.getPrettyStatus())
        print(res)

  # otherwise always print status:
  else:
    print((status.getPrettyStatus()+'\n'))
    if args.details:
      print(status.getPrettyJsonDetails())

  # save job status in text file
  if args.save:
    if status.isComplete():
      if status.isPreviousComplete():
        return
      print('WORKFLOW FINISHED:  '+workflow)
    status.saveStatus()
    status.saveLog()
    if args.details:
      status.saveDetails()

  if len(args.clas12mon)>0 and matchAny(getHeader(workflow)['tag'],args.clas12mon):
    status.saveDatabase()

if __name__ == '__main__':

  df='\n(default=%(default)s)'

  cli = argparse.ArgumentParser()
  cli.add_argument('--list',    help='list workflows',    action='store_true',default=False)
  cli.add_argument('--retry',   help='retry problem jobs',action='store_true',default=False)
  cli.add_argument('--save',    help='save to logs',      action='store_true',default=False)
  cli.add_argument('--details', help='show job details',  action='store_true',default=False)
  cli.add_argument('--problems',help='show problem jobs', action='store_true',default=False)
  cli.add_argument('--quiet',   help='do not print retries', action='store_true',default=False)
#  cli.add_argument('--joblogs', help='move job logs when complete', action='store_true',default=False)
  cli.add_argument('--logdir',  metavar='PATH',help='local log directory'+df, type=str,default=None)
#  cli.add_argument('--publish', help='rsync to www dir',  action='store_true',default=False)
#  cli.add_argument('--webdir',  help='rsync target dir'+df,    type=str,default=None)
#  cli.add_argument('--webhost', help='rsync target host'+df,   type=str,default='jlabl5')
  cli.add_argument('--clas12mon',metavar='TAG',help='write matching workflows to clas12mon (repeatable)',type=str,default=[],action='append')
  cli.add_argument('--delete',   help='delete workflow',   action='store_true',default=False)
  cli.add_argument('--abandon',  help='abandon problem jobs (repeatable)',   action='append',default=[],choices=PROBLEMS)
  cli.add_argument('--workflow', metavar='NAME',help='workflow name (or regex) else all workflows', action='append',default=[])
  cli.add_argument('--missing',  help='find missing output files', action='store_true',default=False)
  cli.add_argument('--stats',    help='show completion status of each workflow component', action='store_true',default=False)

  args = cli.parse_args()

  if args.save and not args.logdir:
    cli.error('Must define --logdir if using the --save option')

  workflows=[]
  if len(args.workflow)==0:
    workflows.extend(getWorkflowNames())
    if args.delete and 'YES' != raw_input('Really delete all workflows?  If so, type "YES" and press return ...'):
        sys.exit('Aborted.')
  else:
    for x in getWorkflowNames():
      for y in args.workflow:
        if re.match('^'+y+'$',x) is not None:
          workflows.append(x)

#  if args.publish and not args.webdir:
#    sys.exit('ERROR:  must define --webdir if using the --publish option')

  if args.list:
    print('\n'.join(workflows))

  else:
    for workflow in workflows:
      if args.delete:
        deleteWorkflow(workflow)
      else:
        processWorkflow(workflow,args)
#        if args.save and args.publish:
#          rsyncCmd=['rsync','-avz',args.logdir+'/',args.webhost+':'+args.webdir]
#          subprocess.check_output(rsyncCmd)

