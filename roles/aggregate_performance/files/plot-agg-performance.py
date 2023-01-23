#!/usr/bin/env python3

import argparse
import json
import matplotlib.pyplot as plt
import os
from pathlib import Path, PurePath
import sys
from binary import BinaryUnits, DecimalUnits, convert_units

PLOTS = [
        {
            "title": "Multiple Clients\nAggregate IOPS\nmode: {mode}, BS: {bs}\nclient threads: {threads}\nMax BW (MB/s): {max_bw}, Max IOPS: {max_iops}",
            "varname": "iops",
            "y_label": "IOPS",
            "name": "iops"
            },
        {
            "title": "Multiple Clients\nAggregate Bandwidth\nmode: {mode}, BS: {bs}\nclient threads: {threads}\nMax BW (MB/s): {max_bw}, Max IOPS: {max_iops}",
            "varname": "bw",
            "y_label": "Bandwidth (MB/s)",
            "name" : "bandwidth"
	}
        ]

RW_LOOKUP = {
            'randwrite': 'write',
            'randread' : 'read',
            'read': 'read',
            'write' : 'write'
        }


def slurp_fio_output(args):   
    results_summary = []
    all_hosts = []
    for jsonfile in args.fio_output_json:
        f = open(jsonfile, "r")
        data = json.load(f)
        clients = [ i for i in data['client_stats'] if i['jobname'] != "All clients" ]
        
        rw = RW_LOOKUP.get(data['global options']['rw'])
        if rw == None:
            print("Unsupported rw mode")
            sys.exit(1)

        n_clients = len(clients)
        for client in clients:
                bw, _ = convert_units(
                    int(client[rw]['bw']),
                    unit=BinaryUnits.KB, 
                    to=DecimalUnits.MB
                    )
                results_summary.append(
                    {
                        'count': n_clients,
                        'hostname': client['hostname'],
                        'bw': bw,
                        'iops': int(client[rw]['iops']),
                        'numjobs': data['global options']['numjobs'],
                        'bs': data['global options']['bs'],
                        'rw': data['global options']['rw']
                    }
                )
                if client['hostname'] not in all_hosts:
                    all_hosts.append(client['hostname'])
    for count in range(1, 1+len(all_hosts)):
        count_hosts = [i['hostname'] for i in results_summary if i['count'] == count]
        for host in all_hosts:
            if host not in count_hosts:
                results_summary.append(
                    {
                        'count': count,
                        'hostname': host,
                        'bw': 0,
                        'iops': 0,
                        'numjobs': data['global options']['numjobs'],
                        'bs': data['global options']['bs'],
                        'rw': data['global options']['rw']
                    }
                )

    return sorted(results_summary, key=lambda k: (k['count'], k['hostname']))

def plot_bar(summary, args, plot, outdir):
    all_hosts = set([i['hostname'] for i in summary])
    labels = [str(i) for i in range(1, len(all_hosts) + 1)]
    fig, ax = plt.subplots()
    cum_size = [0] * len(all_hosts)
    
    for host in all_hosts:
        values = [i[plot['varname']] for i in summary if i['hostname'] == host]
        ax.bar(labels, values, bottom=cum_size, width=0.9, label=host)

        for a in range(len(cum_size)):
            cum_size[a] += values[a]

    client_threads = summary[0]['numjobs']
    bs = summary[0]['bs']
    rw = summary[0]['rw']

    max_perf = {'clients': 0, 'bw': 0, 'iops': 0}
    for k in range(1, len(all_hosts)):
        total_bw = sum([int(i['bw']) for i in summary if i['count'] == k])
        total_iops = sum([int(i['iops']) for i in summary if i['count'] == k])
        if total_bw > max_perf['bw']:
            max_perf['bw'] = total_bw
            max_perf['clients'] = k
            max_perf['iops'] = total_iops

    ax.tick_params(axis='x', which='major', labelsize=4)
    ax.set_title(plot['title'].format(
        bs=bs,
        mode=rw,
        threads=client_threads,
        max_bw=max_perf['bw'],
        max_iops=max_perf['iops']
        )
    )
    ax.set_ylabel(plot['y_label'])
    ax.set_xlabel('Clients active')
    ax.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    fig.savefig(
        PurePath(
            outdir
            ).joinpath(
            '{prefix}-aggregate-{mode}-{bs}-{name}.png'.format(
                prefix=args.output_file_prefix,
                mode=rw,
                name=plot['name'],
                bs=bs
                )
            ), 
            dpi=1000, 
            bbox_inches='tight'
        )

    
def parse_args():

    parser = argparse.ArgumentParser(
            description='Plot the aggregated bandwidth and IO characteristics of a filesystem from fio JSON output'
            )
    parser.add_argument('fio_output_json', type=str, nargs='+',
                                help='fio output json file')
    parser.add_argument('-o', '--outdir', type=str, default='.', help="Output directory for plots and fio job and json files [Default: .].")
    parser.add_argument('-p', '--output-file-prefix', type=str, default='', help="Prefix for output plots filenames [Default: ''].")
    parser.add_argument('-a', '--annotation', type=str, default='', help="Ceph pg_num for tested pool [Default: ''].")
    args = parser.parse_args()
    return args

def make_output_directory(outdir):
    p = Path(outdir).resolve()

    p.mkdir(parents=True, exist_ok=True)

    return p

def main():
    args = parse_args()
    outdir = make_output_directory(args.outdir)
    summary = slurp_fio_output(args)
    for plot in PLOTS:
     	plot_bar(summary, args, plot, outdir)

if __name__ == '__main__':
    main()
