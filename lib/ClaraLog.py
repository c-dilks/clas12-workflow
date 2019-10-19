import os,sys,re,datetime

from JobSpecs import JobSpecs
from JobErrors import ClaraErrors
from LogFinder import LogFinder

_MAXLOGSIZEMB=10
_MINHIPOSIZEMB=100

_LOGTAGS=['Number','Threads','TOTAL','Total','Average','Start time','shutdown DPE','Exception','Input','Output',' is cached']

class ClaraLog(JobSpecs):

  logFinder=LogFinder()

  def __init__(self,filename):
    JobSpecs.__init__(self)
    self.errors=ClaraErrors()
    self.filename=filename
    self.slurmlog=None
    self.filesize=os.path.getsize(filename)
    self.host=self.getFarmoutHostname(filename)
    self.slurmid=ClaraLog.logFinder.getClaraSlurmId(filename)
    self.outputprefix=None
    self.lastline=None
    if self.host is None:
      self.host=self.getClaraHostname(filename)
    if self.host is None:
      print 'Unfound host:  '+filename
      return
    for x in JobSpecs._FLAVORS:
      if self.host.find(x)==0:
        self.flavor=x
        break
    if os.path.getsize(filename)>_MAXLOGSIZEMB*1e6:
      self.errors.setBit('HUGE')
    else:
      with open(filename,'r') as f:
        while True:
          line=f.readline()
          if not line:
            break
          if line.strip()!='':
            self.lastline=line.strip()
          self.parse(line)
      if not self.isComplete():
        self.errors.parse(self.lastline)
    self.attachFarmout()
    if self.slurmstatus=='R':
      self.slurmerrors.setBit('ALIVE')
      self.errors.unsetBit('TRUNC')

  def findOutputFiles(self):
    of=[]
    for f in self.inputfiles:
      basename=self.outputprefix+f.split('/').pop()
      fout=self.outputdir+'/'+basename
      if os.path.exists(fout) and os.path.getsize(fout)>_MINHIPOSIZEMB*1e6:
        of.append(fout)
    return of

  # Extract the hostname from a /farm_out logfile
  def getClaraHostname(self,logfilename):
    for flavor in JobSpecs._FLAVORS:
      # CLARA-generated names:
      m=re.match('.*/(%s)(\d+)_.*'%(flavor),logfilename)
      if m is not None:
        return m.group(1)+m.group(2)
    return None

  def attachFarmout(self):
    files=ClaraLog.logFinder.findFarmoutLog(self.host,self.filename)
    if len(files)<3:
      for file in files:
        if file.endswith('.err'):
          self.slurmerrors.parse(file)
          self.augerid=ClaraLog.logFinder.getFarmoutAugerId(file)
          self.slurmstatus=ClaraLog.logFinder.getStatus(self.augerid,ClaraLog.logFinder.getuser(file))
          self.slurmlog=file
          break
    if self.slurmerrors.watchdog:
      self.errors.bits=0
      self.errors.setBit('WDOG')
#      self.errors.unsetBit('TRUNC')

  def stringToTimestamp(self,string):
    fmt='\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d'
    m=re.match('('+fmt+').*',string.strip())
    if m is None:
      m=re.match('.*('+fmt+').*',string.strip())
    if m is not None:
      t=datetime.datetime.strptime(m.group(1),'%Y-%m-%d %H:%M:%S')
      return t
    return None

  def parse(self,x):
    # abort ASAP unless we find a tag:
    keeper=False
    for tag in _LOGTAGS:
      if x.find(tag)>=0:
        keeper=True
        break
    if not keeper:
      return
    x=x.strip()
    cols=x.split()
    if len(cols)==3:
      if cols[0]=='Threads' and cols[1]=='=':
        threads=int(cols[2])
        if self.threads is None:
          self.threads=int(cols[2])
        elif self.threads != threads:
          sys.exit('Invalid threads: %d!=%d'%(threads,self.threads))
    elif len(cols)==4:
      if x.find('shutdown DPE')>0:
        print x
        self.endtime=self.stringToTimestamp(x)
        print self.endtime
      elif x.find('Input directory')==0:
        self.inputdir=cols[3]
      elif x.find('Output directory')==0:
        self.outputdir=cols[3]
    elif len(cols)==5:
      if x.find('Number of files')>=0:
        if self.nfiles<0:
          self.nfiles=int(cols[4])
        else:
          print self.filename,self.nfiles,x
      elif x.find('Start time')==0:
        if self.starttime is None:
          self.starttime=self.stringToTimestamp(x)
      elif x.find('Output file prefix')>=0:
        self.outputprefix=cols[4]
    elif len(cols)==6:
      if cols[4]=='is' and cols[5]=='cached':
        self.inputfiles.append(cols[3].split('/').pop())
    elif len(cols)==8:
      if cols[2]=='Average' and cols[3]=='processing' and cols[4]=='time':
        if self.t2<0:
          self.t2=float(cols[6])
        else:
          print self.filename,self.threads,x
    elif len(cols)==16:
      if cols[2]=='TOTAL' and cols[4]=='events' and cols[5]=='total':
        if self.events<0:
          self.events=int(cols[3])
        else:
          print self.filename,self.threads,x
      if cols[2]=='TOTAL' and cols[11]=='event' and cols[12]=='time':
        if self.t1<0:
          self.t1=float(cols[14])
        else:
          print self.filename,self.threads,x
    elif x.find('com.mysql.jdbc')>=0 and x.find('Too many connections')>0:
      self.errors.setBit('DB')

