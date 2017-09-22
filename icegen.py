from datetime import datetime as dt
from datetime import timedelta as td
from calendar import timegm
import re
import sqlite3
from os import listdir, path
from sys import argv
import ConfigParser

if len(argv) == 1:
    print 'No configuration file specified'
    exit()
CONFIG_FILE = argv[1]

config = ConfigParser.SafeConfigParser()
config.read(CONFIG_FILE)

DB_PATH = config.get('Main', 'database_path')
LOG_DIR = config.get('Main', 'icecast_log_dir')
MOUNTS = config.get('Main', 'mounts').split(',')
MOUNTS = [_.strip() for _ in MOUNTS]
MIN_CONN_LENGTH = config.getint('Main', 'min_connection_length')

INSERT_LISTENER = ('insert into listeners (ip, start, stop, length, '
                   ' mount, referrer, agent) values (?,?,?,?,?,?,?)')
log_pat = re.compile(
    r'([(\d\.)]+) - - \[(.*?)\] "(.*?)" (\d+) (\d+) "(.*?)" "(.*?)" (\d+)'
    )
db_con = sqlite3.connect(DB_PATH)
cur = db_con.cursor()
count = 0

# determine most recent log entry added
# only newer entries will be processed
cur.execute('select max(stop) from listeners')
maxtime = cur.fetchone()[0]
maxtime = 0 if maxtime is None else maxtime

d = [_ for _ in sorted(listdir(LOG_DIR)) if 'access' in _]
for filename in d:
    log = open(path.join(LOG_DIR, filename))
    for line in log:
        s = log_pat.split(line)
        remote_addr = s[1]
        conn_length = int(s[8])
        agent = s[6]
        referrer = s[7]
        if conn_length < MIN_CONN_LENGTH:
            continue
        mount = (s[3].split(' '))[1]
        if mount not in MOUNTS:
            continue

        # back to UTC
        time_str, tz_str = s[2].split(' ')
        endtime = dt.strptime(time_str, '%d/%b/%Y:%H:%M:%S')
        endtime = endtime + td(minutes=(int(tz_str[0:3])*-60)+int(tz_str[3:5]))
        starttime = endtime - td(seconds=conn_length)
        et = timegm(endtime.utctimetuple())
        st = timegm(starttime.utctimetuple())

        if et > maxtime:
            count += 1
            cur.execute(
                INSERT_LISTENER,
                (remote_addr, st, et, conn_length, mount, agent, referrer)
                )
    log.close()
db_con.commit()
print 'Icestats added entries: %i' % (count,)
