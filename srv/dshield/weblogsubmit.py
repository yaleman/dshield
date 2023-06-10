#!/usr/bin/env python3
# submit logs to DShield 404 project

# version 2019-11-17-01

import os
from pathlib import Path
import sys
import sqlite3
from DShield import DshieldSubmit

# We need to collect the local IP to scrub it from any logs being submitted for anonymity, and to reduce noise/dirty data.

ipaddr = os.popen('/bin/hostname -I').read().replace(" \n", "")

pidfile = "/var/run/weblogparser.pid"
d = DshieldSubmit('')
if os.path.exists(pidfile) and os.path.isfile(pidfile):
    if d.check_pid(pidfile):
        sys.exit('PID file found. Am I already running?')
    else:
        print("stale lock file.")
        os.remove(pidfile)

f = open(pidfile, 'w')
f.write(str(os.getpid()))
f.close()

config = Path(os.path.join("..", "www", "DB", "webserver.sqlite")).resolve()
if not config.parent.exists():
    print(f"Failed to find DB dir: {config.parent}")
    sys.exit(1)
# config = '..' + os.path.sep + 'www'+os.path.sep+'DB' + os.path.sep + 'webserver.sqlite'
if os.getenv("DEBUG"):
    print(f"Database file: {config}")
try :
    conn = sqlite3.connect(config)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS submissions
            (
              timestamp integer primary key,
              linessent integer
            )
          ''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                (
                    date text,
                    headers text,
                    address text,
                    cmd text,
                    path text,
                    useragent text,
                    vers text,
                    summary text,
                    targetip text
                )
            ''')

    maxid = c.execute("""SELECT max(timestamp) from submissions""").fetchone()
except sqlite3.Error as error:
    print(f"Error pulling submissions from db at {config}: {error}")
    os.remove(pidfile)
    sys.exit(1)

starttime=0

if str(maxid[0]) != "None" :
    starttime=float(maxid[0])
try:
    rsx=c.execute(
        """SELECT date, headers, address, cmd, path, useragent, targetip from requests where date>?""",
        [starttime],
        ).fetchall()
except sqlite3.Error as error:
    print(f"Error pulling requests from db at {config}: {error}")
    os.remove(pidfile)
    sys.exit(1)

logs = []
lasttime = starttime
linecount = 0
for r in rsx:
    logdata = {}
    headerdata = {}
    logdata['time']=float(r[0])
    # Header data was stored as a string with extra characters, so some clean-up needed.
    for each in r[1].split('\r\n'):
        if (each and ipaddr in each): # scrubbing local IP from data before submission
            try:
                headerdata['header_'+str(each.split(': ')[0])] = each.split(': ')[1]
            except IndexError:
                headerdata['header_' + str(each.split(':')[0])] = each.split(':')[1]
    logdata['headers']=headerdata # Adding header data as a sub-dictionary
    logdata['sip']=r[2]
    logdata['dip']=r[6]
    logdata['method']=str(r[3])
    logdata['url']=str(r[4])
    logdata['useragent']=str(r[5])
    lasttime = int(float(r[0]))+1
    linecount = linecount+1
    logs.append(logdata)
if starttime == lasttime:
    conn.close()
    os.remove(pidfile)
    sys.exit(1)
try:
    c.execute("INSERT INTO submissions (timestamp,linessent) VALUES (?,?)",(lasttime,linecount))
    conn.commit()
    conn.close()
except sqlite3.Error as error:
    print(f"Error storing submissions into db at {config}: {error}")
    os.remove(pidfile)
    sys.exit(1)

# Changed type from 404report to reflect addition of new header data
l = {'type': 'webhoneypot', 'logs': logs}
d.post(l)
os.remove(pidfile)

try:
    # Web.py seems to hang periodically, so to bandaid this situation, we restart web.py twice an hour
    os.popen("systemctl restart webpy")
except Exception as error:
    if os.getenv("DEBUG"):
        print(f"Failed to restart webpy service! {error}")
    pass


