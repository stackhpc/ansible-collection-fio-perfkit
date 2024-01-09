# ansible-collection-fio-perfkit

An ansible collection for benchmarking network filesystem aggregate performance using `fio`, the [flexible IO](https://fio.readthedocs.io/en/latest/) tester.

### Installation

```
python3 -m venv venv
source venv/bin/activate
pip install ansible>=9.0
ansible-galaxy collection install git+https://github.com/stackhpc/ansible-collection-fio-perfkit.git
```

### Usage

#### Ansible inventory

Create a simple Ansible inventory, specifying a single `control` host, and as many network filesystem `fs_client` hosts as required. 

The control `host` may be `localhost`, but the control host must be able to connect to port 8765 on all `fs_client` hosts. 

Equally, the control host may be one of the filesystem clients, but output plots will be generated on the control host and must be retrieved.  

```
[control]
localhost ansible_connection=local # Must be able to connect to port 8765 on all clients

[fs_clients]
fs-client[01-30]
```

#### Ansible playbook
An example Ansible playbook to use with `ansible-collection-fio-perfkit`:
```yaml
---
- name: Run device tests
  hosts: fs_clients
  gather_facts: true
  tasks:
    - name: Test conncurrent IO to all devices on a host
      ansible.builtin.import_role:
        name: stackhpc.fio_perfkit.fio_perfkit_single_host
      vars:
        fio_perfkit_single_host_config:
          - devices:
              - /dev/vdb
              - /dev/vdc
            max_numjobs: 4
            bs: 1M
            rw: write
            runtime: 2
            filesize: 2M

    - name: Test conncurrent IO from multiple processes to a single device on a host
      ansible.builtin.import_role:
        name: stackhpc.fio_perfkit.fio_perfkit_single_device
      vars:
        fio_perfkit_single_device_config:
          - device: /dev/vdb
            max_numjobs: 4
            bs: 1M
            rw: write
            runtime: 2
            filesize: 2M

- name: Run filesystem tests
  hosts: fs_clients,control
  gather_facts: true
  tasks:
    - name: Test a mix of read/write IO to a shared filesystem from many clients
      ansible.builtin.import_role:
        name: stackhpc.fio_perfkit.fio_perfkit_fs_mixed_io
      vars:
        fio_perfkit_fs_mixed_io_config:
        # Test the product of fio_bs_list, fio_read_mix and fio_random_mix
        # Ranges for fio_read_mix and fio_random_mix are calculated
          fio_directory: /mnt/scratch # Target directory for fio tests
          fio_runtime: 5 # fio runtime
          fio_numjobs: 2 # fio numjobs
          fio_size: 1M # fio filesize
          fio_nrfiles: 2 # fio nrfiles
          fio_bs_list: # List of blocksizes to test
            - 1M
          fio_read_mix:
            start: 0
            end: 100
            step: 50
          fio_random_mix:
            start: 0
            end: 100
            step: 50

    - name: Test the aggregate performance of a shared filesystem from many clients
      ansible.builtin.import_role:
        name: stackhpc.fio_perfkit.fio_perfkit_fs_aggregate_io
      vars:
        fio_perfkit_fs_aggregate_io_config:
          # Test the product of fio_bs_list and fio_rw_list
          fio_directory: /mnt/scratch # Target directory for fio tests
          fio_runtime: 5 # fio runtime
          fio_numjobs: 2 # fio numjobs
          fio_size: 1M # fio filesize
          fio_nrfiles: 2 # fio nrfiles
          fio_bs_list: # List of blocksizes to test
            - 1M
            - 32k
          fio_rw_list: # List of rw modes to test
            - read
            - write

- name: Run io500 tests
  hosts: io500
  gather_facts: true
  tasks:
    - name: Run the io500 tests
      ansible.builtin.import_role:
        name: stackhpc.fio_perfkit.io500
      vars:
        io500_test_path: "/mnt/share"
        io500_stonewall_time: 300
```

### Benchmarks
All benchmarks are time-based - they run for as long as specified in `fio_runtime`. Additionally, the number of files to test IO over (`fio_nrfiles`), the number of IO threads (`fio_numjobs`) and the file size (`fio_size`) can be adjusted.

#### Single device performance
Use fio to test a single device with multiple jobs. This is useful for testing Ceph OSD host db/wal disks.

#### Single host, multiple device performance
Use fio to test all devices on a host. This is useful for testing the aggregate performance of all OSD disks on OSD hosts. 

#### Aggregate Performance
Filesystem clients are added to the benchmark in turn from one filesystem client, to all filesystem clients. Each clients' contribution to filesystem bandwidth and IOPs is measured and plotted. The benchmark comprises a two-dimensional parameter sweep across multiple IO block-sizes and IO modes.

Useful for measuring saturation of filesystem performance. 

#### Mixed IO
All filesystem clients participate in a range of benchmarks. A three-dimensional parameter sweep from 100% read to 100%
write, from 100% random to 100% sequential IOs, and across multiple IO block-sizes is used to assemble the benchmark.

#### io500
Run the io500 using OpenMPI and [io500-singularity](https://github.com/stackhpc/io500-singularity). All members of the
`[io500]` group will participate in the benchmark, and the first host will act as the MPI coordinator. 