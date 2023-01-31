#!/usr/bin/env python3

import argparse
import json
import matplotlib.pyplot as plt
import os
from pathlib import Path, PurePath
import shlex
import socket
import subprocess
import sys
from binary import BinaryUnits, DecimalUnits, convert_units

GLOBAL_CONFIG = [
        '[global]',
        'bs={bs}',
        'iodepth=16',
        'direct=1',
        'ioengine=libaio',
        'randrepeat=0',
        'time_based',
        'runtime={runtime}',
        'filesize={filesize}'
        ]


DEVICE_CONFIG = [
        "[{device_name}]",
        "rw={mode}",
        "filename={device}",
        "name={device_name}"
        ]

PLOTS = [
        {
            "title": "Multiple Disks\nAggregate IOPS\nmode: {mode},BS: {bs} | {hostname}",
            "varname": "iops",
            "y_label": "IOPS",
            "name": "iops"
            },
        {
            "title": "Mutiple disks\nAggregate Bandwidth\nmode: {mode},BS: {bs} | {hostname}",
            "varname": "bw",
            "y_label": "Bandwidth (MB/s)",
            "name" : "bandwidth"
	}
        ]

def check_block_devices(devices):
    for device in devices:
        if not Path(device).is_block_device():
            sys.exit("{device} is not a block device, quitting".format(
                device=device)
                )

def run_fio(args, outdir):
    summary_output = []
    total_disks = len(args.devices)
    for idx in range(1, 1 + total_disks):
        count_output = {}
        devices = args.devices[:idx]
        config_fn = PurePath(
            outdir
            ).joinpath(
            "{hostname}-aggregate-{mode}-{bs}-{idx}.fio".format(
                hostname=socket.gethostname(),
                mode=args.mode,
                bs=args.bs,
                idx=idx
            )
        )
        config = []

        print("Device count: {count}\nDevices included: {devices}".format(
            count=idx,
            devices=",".join(devices)
            )
        )
        for device in devices:
            device_name = os.path.basename(device)
            for line in DEVICE_CONFIG:
                config.append(
                        line.format(
                            device=device,
                            idx=idx,
                            device_name=device_name,
                            mode=args.mode
                            )
                        )
        with open(config_fn, "w") as f:
            for line in GLOBAL_CONFIG:
                line = line.format(
                        bs=args.bs,
                        runtime=args.runtime,
                        filesize=args.filesize,
                        )
                f.write(line+'\n')
            for line in config:
                f.write(line+'\n')
        
        fio_cmd = "fio --output-format=json --output={config_fn}.output.json {config_fn}".format(
                config_fn=config_fn,
                )
        print("Running fio...")
        print(fio_cmd)        
        subprocess.run(
                shlex.split(
                    fio_cmd
                    ), 
                stderr = subprocess.DEVNULL, 
                stdout = subprocess.DEVNULL
                )
        
        f = open("{config_fn}.output.json".format(
            config_fn=config_fn
            )
        )
        
        data = json.load(f)

        if args.cleanup:
            Path(config_fn).unlink()
            Path(
                "{config_fn}.output.json".format(
                    config_fn=config_fn
                    )
                ).unlink()

        for dev_idx,device in enumerate(devices, 1):
            device_name = os.path.basename(device)
            print("Parsing output for {device}".format(
                device=device
                )
            )
            dev_data = [i[args.mode] for i in data['jobs'] if i['jobname'] == device_name][0]
            count_output.update(
                    {
                        device: {
                            'bw': dev_data['bw'], 
                            'iops':  dev_data['iops']
                            }
                        }
                    )

        for device in args.devices:
            if device in count_output:
                bw, _ = convert_units(
                        count_output[device]['bw'], 
                        unit=BinaryUnits.KB, 
                        to=DecimalUnits.MB
                        )
                iops = count_output[device]['iops']

            else:
                bw = iops = 0
            
            summary_output.append(
                    {
                        'count': idx,
                        'device': device,
                        'bw': bw,
                        'iops': iops
                        }
                    )

    return summary_output

def plot_bar(summary, args, plot, outdir):
    print("Making {name} plot".format(name=plot['name']))
    labels = [str(i) for i in range(1, len(args.devices) + 1)]
    fig, ax = plt.subplots()
    cum_size = [0] * len(args.devices)
    for idx,device in enumerate(args.devices):
        values = [i[plot['varname']] for i in summary if i['device'] == device]
        ax.bar(labels, values, bottom=cum_size, width=0.9, label=device)

        for a,b in enumerate(cum_size):
            cum_size[a] += values[a]

    ax.tick_params(axis='x', which='major', labelsize=4)
    ax.set_title(plot['title'].format(
        bs=args.bs,
        hostname=socket.gethostname(),
        mode=args.mode
        )
    )
    ax.set_ylabel(plot['y_label'])
    ax.set_xlabel('Devices active')
    ax.legend(bbox_to_anchor=(1.04, 1), loc="upper left")
    fig.savefig(
        PurePath(
            outdir
            ).joinpath(
            '{hostname}-aggregate-{mode}-{bs}-{name}.png'.format(
                hostname=socket.gethostname(),
                mode=args.mode,
                name=plot['name'],
                bs=args.bs
                )
            ), 
            dpi=1000, 
            bbox_inches='tight'
        )

def parse_args():

    parser = argparse.ArgumentParser(
            description='Plot the aggregated bandwidth and IO characteristics of a set of block devices, using fio.'
            )
    parser.add_argument('devices', metavar='device', type=str, nargs='+',
                                help='Block device')
    parser.add_argument('-c', '--cleanup', action='store_true', help="Clean up fio job and output JSON files [Default: no]." )
    parser.add_argument('-o', '--outdir', type=str, default='.', help="Output directory for plots and fio job and json files [Default: .].")
    parser.add_argument('-b', '--bs', type=str, default='8k', help='fio bs parameter [Default: 8k].')
    parser.add_argument('-m', '--mode', type=str, default='read', help='fio rw parameter [Default: read].')
    parser.add_argument('-r', '--runtime', type=str, default='30', help='fio runtime parameter in seconds [Default: 30].')
    parser.add_argument('-f', '--filesize', type=str, default='2G', help='fio filesize parameter [Default: 2G].')

    args = parser.parse_args()
    print(args)
    return args

def make_output_directory(outdir):
    p = Path(outdir).resolve()

    p.mkdir(parents=True, exist_ok=True)

    return p

def main():
    args = parse_args()
    check_block_devices(args.devices)
    outdir = make_output_directory(args.outdir)
    summary = run_fio(args, outdir)
    for plot in PLOTS:
    	plot_bar(summary, args, plot, outdir)

if __name__ == '__main__':
    main()
