#!/usr/bin/env python3
"""
Run until the workflow ends by checking the jobstate.log file.
"""
import time

if __name__ == '__main__':
    from argparse import ArgumentParser
    ap = ArgumentParser()
    ap.add_argument("-j", "--jobstate_path", type=str, required=True,
            help="The path to the Pegasus jobstate.log file.")
    ap.add_argument("-i", "--interval", type=float, default=3,
            help="Default: %(default)s. "
            "The time interval (in seconds) between checking the jobstate.log file.")
    args = ap.parse_args()
    
    start_time = None
    continue_to_monitor = True
    counter = 0
    while continue_to_monitor:
        time.sleep(args.interval)
        input_file = open(args.jobstate_path, 'r')
        for line in input_file:
            timestamp = int(line.split()[0])
            if start_time is None:
                start_time = timestamp
            if line.find('MONITORD_FINISHED')>=0:
                end_time = timestamp
                continue_to_monitor = False
        input_file.close()
        counter += 1
    time_delta=  end_time - start_time
    print(f"Workflow finished in {time_delta} seconds, {time_delta/60:.2f} minutes.", flush=True)
