"""
Run using python 3.x

Uses the PyMySQL package to access database, select random ld block, and compare that block with ones generated by the Broad Institute's SNAP program
"""

def getRandomRsids(cur):
  """
  Choose random ld block and write RSIDs to .txt file for submission to
  """
  pops = ['CEU','CHB','JPT','YRI']

  chroms = ['chrX']

  [chroms.append('chr' + str(i)) for i in range(1,23)]

  pop = pops[random.randrange(0,4)]

  chridx = random.randrange(1,24)
  if chridx is 23:
    chrom = 'chrX'
  else:
    chrom = chroms[chridx]

  # sql = "select max("+ pop + ") from blocks"
  # cur.execute(sql)
  # Deleted for unnecessary queries since max values are fixed

  # for row in cur:
  #   maxblock = int(row[0])

  block = random.randrange(1,maxBlocks[pop]+1)

  return [pop , chrom, block]


def getTestRsids(cur):

  test_rsids = []

  while len(test_rsids) == 0:
    [pop , chrom , block] = getRandomRsids(cur)
  
    sql = "select blocks.rsid from blocks inner join rsids on blocks.rsid=rsids.rs where blocks.%s=%s and rsids.chrom='%s'"

    cur.execute(sql % (pop,str(block),chrom))
    
    test_rsids = cur.fetchall()
    # for row in cur:
    #   test_rsids.append(row[0])

  return(test_rsids,pop)

def getSNAPResults(test_rsids,pop):
  #Use curl to submit a POST form to SNAP in order to retrieve data via command line

  rsidString = "%0D%0A".join([item[0] for item in test_rsids]) #joins separate RSIDs into one string separated by returns (required for SNAP POST format)
  hapMapPanel = pop
  if pop is "JPT" or pop is "CHB":
    hapMapPanel = "CHBJPT" #SNAP combines these two groups

  searchString = """
    SearchPairwise=
    &snpList=%s
    &hapMapRelease=onekgpilot
    &hapMapPanel=%s
    &RSquaredLimit=0.8
    &distanceLimit=500000
    &downloadType=File
    &includeQuerySnp=on
    &arrayFilter=query
    &columnList[]=DP
    &columnList[]=GP
    &columnList[]=AM
    &submit=search
    """ % (rsidString , hapMapPanel)

  subprocess.call(["curl","-s","-d",searchString,"-o","SNAPResults.txt","http://www.broadinstitute.org/mpg/snap/ldsearch.php"])
  time.sleep(1) #wait 1 second to prevent server overload

def compareResults():
  
  match = []
  nomatch_num = []
  nomatch = []
  fh_in = open('SNAPResults.txt','r')
  lines = {}
  dne = []

  linenum = 0

  for line in fh_in:
    linenum+=1
    
    if "SNP" in line: #skip first line
      continue
    
    if "Error" in line: #sometimes connection fails, returns file with "Error:" at beginning of second line
      return False

    lines[linenum] = line

  fh_in.close()
  
  for linenum , line in lines.iteritems():
    entries = line.strip().split('\t')
    
    if 'WARNING' in line: #skip lines where rsid doesn't exist in SNAP data
      dne += '\t'.join([entries[0],entries[1] , str(linenum)]) + '\n'
      continue

    #sql = "select %s from blocks where rsid='%s'"
    #cur.execute(sql % (pop, entries[0]))
    sql = "select %s from blocks where rsid='%s' or rsid='%s'" #query both linked snps at once. 
    cur.execute(sql % (pop, entries[0], entries[1]))

    blocks = []

    for row in cur:
      try:
        blocks.append(int(row[0]))
        
      except IndexError: #throws IndexError if SNAP RSID doesn't exist in MySQL db
        dne += '\t'.join([entries[0] ,entries[1]]),"\n"
        continue
    
    if len(blocks) != 2:
      continue

    if blocks[0] == blocks[1]: #SNAP pairs are in same block in MySQL data
      match += '\t'.join([entries[0] , entries[1] , str(blocks[0])]) + '\n'

    elif  blocks[0] == 0 or blocks[1] == 0:
      dne += '\t'.join([entries[0] , str(blocks[0]) , entries[1] , str(blocks[1])]) + '\n'

    else: #SNAP pairs are not in the same block
      nomatch_num += '\t'.join([entries[0] , str(blocks[0]) , entries[1] , str(blocks[1])]) + '\n'

      if random.randrange(10) == 1: #write only 10% of nomatch
        nomatch += pop+ '\t' + '\t'.join([entries[0] , str(blocks[0]) , entries[1] , str(blocks[1])]) + '\n'

  with open('match.txt','w') as f:
    f.write(''.join(match))

  with open('nomatch.txt','w') as f:
    f.write(''.join(nomatch_num))

  with open('nomatch_pairs.txt','a+') as f:
    f.write(''.join(nomatch))

  with open('dne.txt','w') as f:
    f.write(''.join(dne))

def analyzeResults(out):
  
  i = 0 
  with open("match.txt","r") as f:
    for i, l in enumerate(f,start=1):
      pass
  out.write(str(i))
  out.write('\t')
  f.close()

  del i
  i=0
  with open("nomatch.txt","r") as f:
    for i, l in enumerate(f,start=1):
      pass
  out.write(str(i))
  out.write('\t')
  f.close()
 
  del i
  i=0 
  with open("dne.txt","r") as f:
    for i, l in enumerate(f,start=1):
      pass
  out.write(str(i))
  out.write('\n')
  f.close()

import pymysql
import random
import sys
import subprocess
import time
import connect

[conn,cur] = connect.makeConn('ld')

if ".py" in sys.argv[-1]:
  runTimes = 1
else:
  runTimes = int(sys.argv[-1])

ana_fh = open("analyze.txt","w")

falseCount = 0
global maxBlocks
maxBlocks = {'CEU':171160 , 'CHB':157962 , 'JPT':158172 , 'YRI':158172}

for i in range(0,runTimes):
  [test_rsids,pop] = getTestRsids(cur)

  getSNAPResults(test_rsids,pop)

  if compareResults() is False: #make sure SNAP is sending data
    i-= 1
    falseCount+=1
    if falseCount > 25:
      break
    continue

  analyzeResults(ana_fh)

ana_fh.close()
cur.close()
conn.close()

subprocess.call(["mv", "nomatch_pairs.txt","nomatch_pairs_" + str(time.time()) + ".txt"])
