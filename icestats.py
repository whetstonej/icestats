#!/usr/bin/python2
from datetime import datetime as dt
from datetime import timedelta as td
import sqlite3
from calendar import timegm
import ConfigParser
from sys import argv
from flask import Flask, request, jsonify, render_template

if len(argv) == 1:
    print 'No configuration file specified'
    exit()
CONFIG_FILE = argv[1]
CONFIG = ConfigParser.SafeConfigParser()
CONFIG.read(CONFIG_FILE)
ICE_DB = CONFIG.get('Main', 'database_path')
IGNORED_AGENTS = CONFIG.get('Main', 'ignored_agents').split(',')
IGNORED_AGENTS = tuple([_.strip() for _ in IGNORED_AGENTS])

app = Flask(__name__)

def gen_tables(listeners):
    ref_cnt = {}
    ref_len = {}
    agent_cnt = {}
    for i in listeners:
        ref = i[3]
        # simplify complicated agent strings
        # splitting at the '/' generally removes version information
        agent = i[5].split(' ')[0]
        agent = agent.split('/')[0]
        if ref.startswith('http'):
            ref = ref.split('/')[2]
        if ref not in ref_cnt:
            ref_cnt[ref] = 0
            ref_len[ref] = 0
        if agent not in agent_cnt:
            agent_cnt[agent] = 0
        ref_cnt[ref] += 1
        ref_len[ref] += i[4]
        agent_cnt[agent] += 1
    cnt_tbl = [
        render_template(
            'table_fragment.html',
            data=[[_, ref_cnt[_]] for _ in sorted(ref_cnt.keys())]
            )
        ]
    agent_tbl = [
        render_template(
            'table_fragment.html',
            data=[[_, agent_cnt[_]] for _ in sorted(agent_cnt.keys())]
            )
        ]
    len_tbl = [
        render_template(
            'table_fragment.html',
            data=[[_, ref_len[_]] for _ in sorted(ref_len.keys())]
            )
        ]
    return cnt_tbl, len_tbl, agent_tbl

@app.route('/', methods=['GET', 'POST'])
@app.route('/icestats', methods=['GET', 'POST'])
def icestats():
    if request.method == 'GET':
        return render_template('icestats.html')
    s_d = request.json.get('start')
    e_d = request.json.get('end')
    tzoffset = request.json.get('tzoffset')
    try:
        if len(s_d) == 10:
            s_d = '0' + s_d
        if len(e_d) == 10:
            e_d = '0' + e_d
        s_d = dt.strptime(s_d, '%d-%b-%Y')
        e_d = dt.strptime(e_d, '%d-%b-%Y')
    except ValueError:
        return jsonify(status='error',
                       message='Unable to parse provide_d dates')
    s_d = s_d + td(minutes=tzoffset)
    s_d = timegm(s_d.timetuple())
    e_d = e_d.replace(hour=23, minute=59, second=59)
    e_d = e_d + td(minutes=tzoffset)
    e_d = timegm(e_d.timetuple())

    con = sqlite3.connect(ICE_DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    listeners = cur.execute(
        'select id, start, stop, referrer, length, agent '
        'from listeners '
        'where start < ? and stop > ? ',
        (e_d, s_d)
        )
    listeners = cur.fetchall()
    con.close()

    listeners = [_ for _ in listeners
                 if not _['agent'].startswith(IGNORED_AGENTS)]

    # time is not exact due to inclusion of full duration of listeners
    # that were listening across the start/end time period
    ice_t = [_['length'] for _ in listeners]
    ice_t = sum(ice_t)/3600.0
    hr_label = 'Time period contains ~%.2f streaming hours' % (ice_t)

    # process events in chronological order
    l = [[_['start'], 'start'] for _ in listeners]
    l.extend([[_['stop'], 'stop'] for _ in listeners])
    l = sorted(l, key=lambda x: x[0])

    connections = 0
    data = []
    for i in l:
        if i[0] < s_d:
            connections += 1
            continue
        if i[0] > e_d:
            continue
        if i[1] == 'start':
            connections += 1
        else:
            connections -= 1
        data.append([i[0]*1000, connections])
    cnt_tbl, len_tbl, agent_tbl = gen_tables(listeners)

    return jsonify(status='ok', dataset=data, hr_label=hr_label,
                   cnt_tbl=cnt_tbl, len_tbl=len_tbl, agent_tbl=agent_tbl)

if __name__ == '__main__':
    app.run()
