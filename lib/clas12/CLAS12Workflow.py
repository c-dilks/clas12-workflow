import os,logging

from SwifJob import SwifJob
from SwifWorkflow import SwifWorkflow
import CLAS12Jobs
import ChefUtil

_LOGGER=logging.getLogger(__name__)

class CLAS12Workflow(SwifWorkflow):

  def __init__(self,name,cfg):
    SwifWorkflow.__init__(self,name)
    self.cfg=cfg
    self.addRuns(self.cfg['runs'])
    self.findFiles(self.cfg['inputs'])
    r=self.getRunList()
    if len(r)>0:
      self.name+='-%d'%(r[0])
      if len(r)>1:
        self.name+='x%d'%(len(r))
    self.logDir=None
    self._mkdirs()
    self.ignored=[]

  def addRun(self,run):
    if type(run) is not int:
      return
    if self.cfg['rcdbstrict']:
      c = ChefUtil.getUserComment(run)
      if c.lower().find('junk') >= 0:
        if run not in self.ignored:
            self.ignored.append(run)
        return
    super().addRun(run)

  def _mkdirs(self):
    if self.cfg['logDir'] is not None:
      self.logDir = '%s/%s'%(self.cfg['logDir'],self.name)
      ChefUtil.mkdir(self.logDir,'slurm log')

  def addJob(self,job):
    if isinstance(job,list):
      for j in job: self.addJob(j)
    else:
      job.setLogDir(self.logDir)
      SwifWorkflow.addJob(self,job)

  #
  # reconclara:  add jobs for reconstrucing hipo files
  # - one job per reconSize files
  #
  def reconclara(self,phase,inputs):
    inps,ants,jobs=[],[],[]
    for ii,inp in enumerate(inputs):
      if isinstance(inp,SwifJob):
        ants.append(inp)
        inps.extend(inp.outputData)
      else:
        inps.append(inp)
      if len(inps)>=self.cfg['reconSize'] or ii>=len(inputs)-1:
        job=CLAS12Jobs.ReconJob(self.name,self.cfg)
        job.setPhase(phase)
        if len(ants)>0:
          job.antecedents.extend([x.getJobName() for x in ants])
        for x in inps: job.addInputData(x)
        job.setCmd()
        jobs.append(job)
        inps,ants=[],[]
    self.addJob(jobs)
    return jobs

  def histo(self,phase,inputs):
    inps,ants,jobs=[],[],[]
    for ii,inp in enumerate(inputs):
      if isinstance(inp,SwifJob):
        ants.append(inp)
        inps.extend(inp.outputData)
      else:
        inps.append(inp)
    job = CLAS12Jobs.HistoJob(self.name,self.cfg)
    job.setPhase(phase)
    if len(ants)>0:
      job.antecedents.extend([x.getJobName() for x in ants])
    for x in inps:
      job.addInputData(x)
    job.setCmd()
    jobs.append(job)
    self.addJob(jobs)
    return jobs

  #
  # train: run trains
  # - one job per trainSize files
  # - each job has trainSize*nwagons output files
  #
  def train(self,phase,inputs):
    inps,jobs=[],[]
    for ii,inp in enumerate(inputs):
      inps.append(inp)
      reconSize = 1
      if isinstance(inp,SwifJob):
        reconSize = self.cfg['reconSize']
      if len(inps)>=self.cfg['trainSize']/reconSize or ii>=len(inputs)-1:
        job=CLAS12Jobs.TrainJob(self.name,self.cfg)
        job.setPhase(phase)
        if isinstance(inps[0],SwifJob):
          for x in inps:
            job.addInputData(x.outputData)
            job.antecedents.append(x.getJobName())
        else:
          job.addInputData(inps)
        job.setCmd()
        jobs.append(job)
        self.addJob(job)
        inps=[]
    return jobs

  #
  # trainmerge: merge train outputs into one file per run per wagon
  # - one job per run
  #
  def trainmerge(self,phase,jobs):
    runs={}
    for job in jobs:
      if job.getTag('mode')=='ana':
        if job.getTag('run') not in runs:
          runs[job.getTag('run')]=[]
        runs[job.getTag('run')].append(job)
    jobs=[]
    for run in runs:
      job=CLAS12Jobs.TrainMrgJob(self.name,self.cfg)
      for j in runs[run]:
        job.antecedents.append(j.getJobName())
      job.addTag('run','%.6d'%int(run))
      job.setCmd()
      job.setPhase(phase)
      jobs.append(job)
      self.addJob(job)
    return jobs

  #
  # trainclean: remove intermediate, unmerged train outputs
  # - one job per run
  #
  def trainclean(self,phase,jobs):
    runs={}
    for job in jobs:
      if job.getTag('mode')=='ana' or job.getTag('mode')=='anamrg':
        if job.getTag('run') not in runs:
          runs[job.getTag('run')]=[]
        runs[job.getTag('run')].append(job)
    jobs=[]
    for run in runs:
      job=CLAS12Jobs.TrainCleanupJob(self.name,self.cfg)
      for j in runs[run]:
        job.antecedents.append(j.getJobName())
      job.addTag('run','%.6d'%int(run))
      job.setCmd()
      job.setPhase(phase)
      jobs.append(job)
      self.addJob(job)
    return jobs

  #
  # jput:  add jobs for writing from /cache to /mss
  #
  def jput(self,phase,jobs):
    ret = []
    for job in jobs:
      if len(ret)==0 or len(ret[-1].jputfiles)>30:
        j = CLAS12Jobs.JputJob(self.name,self.cfg)
        j.setPhase(phase)
        ret.append(j)
      ret[-1].addJputs([job])
    if len(ret)>0 and len(ret[-1].jputfiles) == 0:
      ret.pop()
    self.addJob(ret)
    return ret

  #
  # decodemerge:  add jobs for decode+merge EVIO files
  # - one job per mergeSize files
  #
  def decodemerge(self,phase,inputs):
    inps,jobs=[],[]
    for ii,inp in enumerate(inputs):
      inps.append(inp)
      if len(inps)>=self.cfg['mergeSize'] or ii>=len(inputs)-1:
        job=CLAS12Jobs.DecodeAndMergeJob(self.name,self.cfg)
        job.setPhase(phase)
        if isinstance(inps[0],SwifJob):
          raise NotImplementedError('asdf')
          job.addInputData([x.outputData[0] for x in inps])
          job.antecedents.extend(inps)
        else:
          job.addInputData(inps)
        jobs.append(job)
        self.addJob(job)
        inps=[]
    return jobs

  #
  # decode:  add jobs for decoding evio files
  # - one job per file
  #
  def decode(self,phase,inputs):
    jobs=[]
    for inp in inputs:
      job=CLAS12Jobs.DecodingJob(self.name,self.cfg)
      job.setPhase(phase)
      if isinstance(inp,SwifJob):
        job.addInputData(inp.outputData[0])
        job.antecedents.append(inp.getJobName())
      else:
        job.addInputData(inp)
      job.setCmd()
      self.addJob(job)
      jobs.append(job)
    return jobs

  #
  # merge:  add jobs for merging hipo files
  # - one job per merge
  # - return list of output merged hipo files
  #
  def merge(self,phase,inputs):
    inps,jobs=[],[]
    for ii,inp in enumerate(inputs):
      inps.append(inp)
      if len(inps)>=self.cfg['mergeSize'] or ii>=len(inputs)-1:
        job=CLAS12Jobs.MergingJob(self.name,self.cfg)
        job.setPhase(phase)
        if isinstance(inps[0],SwifJob):
          job.addInputData([x.outputData[0] for x in inps])
          job.antecedents.extend(inps)
        else:
          job.addInputData(inps)
        jobs.append(job)
        self.addJob(job)
        inps=[]
    return jobs

  #
  # delete:  add jobs to delete files from disk
  # - one job per 200 files
  #
  def delete(self,phase,deletes):
    jobs=[]
    files = list(deletes)
    while len(files)>0:
      deletes=[]
      while len(deletes)<200 and len(files)>0:
        deletes.append(files.pop(0))
      if len(deletes)>0:
        job=CLAS12Jobs.Job(self.name,self.cfg)
        job.setPhase(phase)
        job.setRam('512MB')
        job.setTime('%ds'%(60+3*len(deletes)))
        job.setDisk('100MB')
        job.setRun(RunFile(deletes[0]).runNumber)
        f1=RunFile(deletes[0]).fileNumber
        f2=RunFile(deletes[len(deletes)-1]).fileNumber
        job.addTag('file','%.5d-%.5d'%(f1,f2))
        job.addTag('mode','delete')
        cmds = [ '(sleep 0.5 ; rm -f %s)'%delete for delete in deletes ]
        job.setCmd(' ; '.join(cmds))
        self.addJob(job)
        jobs.append(job)
    return jobs

  #
  # move:  add jobs to move files to final destination
  # - one job per 200 files
  #
  def move(self,phase,moves):
    jobs=[]
    files = list(moves)
    while len(files)>0:
      moves=[]
      while len(moves)<200 and len(files)>0:
        moves.append(files.pop(0))
      if len(moves)>0:
        job=CLAS12Jobs.Job(self.name,self.cfg)
        job.setPhase(phase)
        job.setRam('512MB')
        job.setTime('%ds'%(600+60*len(moves)))
        job.setDisk('100MB')
        job.setRun(RunFile(moves[0]).runNumber)
        job.addTag('mode','move')
        job.addTag('outDir',self.cfg['decDir'])
        outDir='%s/%.6d'%(self.cfg['decDir'],int(job.getTag('run')))
        ChefUtil.mkdir(outDir)
        cmd = '(sleep 0.5 ; set d=%s ; touch -c $d ; rsync $d %s/ ; rsync $d %s/ && rm -f $d)'
        cmds = [ cmd%(move,outDir,outDir) for move in moves ]
        job.setCmd(' ; '.join(cmds)+' ; true')
        for move in moves:
          job.outputData.append('%s/%s'%(outDir,os.path.basename(move)))
        self.addJob(job)
        jobs.append(job)
    return jobs

  #
  # reconutil:  add jobs for running single-threaded recon
  # - one job per file
  # - return list of reconstructed hipo files
  #
  def reconutil(self,phase,hipoFiles):

    raise NotImplementedError('Need to update GEOM/DC env vars')

    reconnedFiles=[]

    for hipoFileName in hipoFiles:

      runno = RunFile(hipoFileName).runNumber
      fileno = RunFile(hipoFileName).fileNumber
      reconBaseName = os.path.basename(hipoFileName).replace('.hipo','.recon.hipo')

      nFiles = 1
      subDir = 'singles'
      if reconBaseName.count('-')>0:
        nFiles = self.cfg['mergeSize']
        subDir = 'merged'

      if nFiles>1:
        outDir = '%s/recon/%s/%.6d'%(self.cfg['workDir'],subDir,runno)
      else:
        outDir = '%s/recon/%.6d/'%(self.cfg['outDir'],runno)

      reconFileName = outDir+'/'+reconBaseName
      reconnedFiles.append(reconFileName)

      ChefUtil.mkdir(outDir)

      job=CLAS12Jobs.Job(self.name)
      job.setPhase(phase)
      job.setRam('4000MB')
      job.setTime('%dh'%(12*nFiles))
      job.setDisk('%dGB'%(4*nFiles))
      job.setRun(runno)
      job.addTag('file','%.5d'%fileno)
      job.addTag('mode','recon')
      job.addTag('coatjava',self.cfg['coatjava'])
      job.addTag('outDir',outDir)
      job.addInput('in.hipo',hipoFileName)
      job.addOutput('out.hipo',reconFileName)
      job.addEnv('GEOMDBVAR','may_2018_engineers')
      job.addEnv('USESTT','true')
      job.addEnv('SOLSHIFT','-1.9')
      cmd =' %s/bin/recon-util -c 2 -i in.hipo -o out.hipo'%self.cfg['coatjava']
      cmd+=' && ls out.hipo'
      cmd+=' && %s/bin/hipo-utils -test out.hipo'%self.cfg['coatjava']
      cmd+=' || rm -f out.hipo && ls out.hipo'
      job.setCmd(cmd)

      self.addJob(job)

    return reconnedFiles
