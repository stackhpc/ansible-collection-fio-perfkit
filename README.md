# ansible-collection-fio-perfkit

An ansible collection for benchmarking network filesystem aggregate performance using `fio`, the [flexible IO](https://fio.readthedocs.io/en/latest/) tester.

### Installation

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ansible-galaxy install -r requirements.yml
```

### Usage

#### Ansible inventory

Create a simple Ansible inventory, specifying a single `control` host, and as many network filesystem `client` hosts as required. 

The control `host` may be `localhost`, but the control host must be able to connect to port 8765 on all `client` hosts. 

Equally, the control host may be one of the filesystem clients, but output plots will be generated on the control host and must be retrieved.  

```
[control]
localhost ansible_connection=local # Must be able to connect to port 8765 on all clients

[clients]
fs-client[01-30]
```

#### Ansible playbook
An example Ansible playbook to use with `ansible-collection-fio-perfkit`:
```
---

- hosts: clients,control
  collections:
    - stackhpc.fio_perfkit
  gather_facts: true
  tasks:
    - import_role: 
        name: fs_mixed_io
      vars:
        fio_perfkit_mixed_io:
          # Test the product of fio_bs_list, fio_read_mix and fio_random_mix
          # Ranges for fio_read_mix and fio_random_mix are calculated
          fio_directory: /mnt/scratch # Target directory for fio tests
          fio_runtime: 10 # fio runtime
          fio_numjobs: 2 # fio numjobs
          fio_size: 100M # fio filesize
          fio_nrfiles: 2 # fio nrfiles
          fio_bs_list: # List of blocksizes to test
            - 4M
            - 1M
            - 32k
          fio_read_mix:
            start: 0
            end: 100
            step: 50
          fio_random_mix:
            start: 0
            end: 100
            step: 50

    - import_role:
        name: fs_aggregate_performance
      vars:
        fio_perfkit_agg_io:
          # Test the product of fio_bs_list and fio_rw_list
          fio_directory: /mnt/scratch # Target directory for fio tests
          fio_runtime: 10 # fio runtime
          fio_numjobs: 2 # fio numjobs
          fio_size: 100M # fio filesize
          fio_nrfiles: 2 # fio nrfiles
          fio_bs_list: # List of blocksizes to test
            - 4M
            - 1M
            - 32k
          fio_rw_list: # List of rw modes to test
            - read
            - write
            - randread
            - randwrite 
```

### Benchmarks
All benchmarks are time-based - they run for as long as specified in `fio_runtime`. Additionally, the number of files to test IO over (`fio_nrfiles`), the number of IO threads (`fio_numjobs`) and the file size (`fio_size`) can be adjusted.

#### Aggregate Performance
Filesystem clients are added to the benchmark in turn from one filesystem client, to all filesystem clients. Each clients' contribution to filesystem bandwidth and IOPs is measured and plotted. The benchmark comprises a two-dimensional parameter sweep across multiple IO block-sizes and IO modes.

Useful for measuring saturation of filesystem performance. 

#### Mixed IO
All filesystem clients participate in a range of benchmarks. A three-dimensional parameter sweep from 100% read to 100% write, from 100% random to 100% sequential IOs, and across multiple IO block-sizes is used to assemble the benchmark.