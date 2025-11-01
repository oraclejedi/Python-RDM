# Python-RDM
Python script to add or remove RDMs from a VMware guest VM

Note: This script uses the pyVmomi Python library.
Note: This script uses the pyVim Python library.

Theory of Operation:
This script is designed to quickly add or remove RDMs from a VMware guest VM.

RDMs are one option to add storage to a VM.  Whereas there are pros and cons to each choice, RDMs have the advantage of being hypervisor, OS and storage agnostic.  They also allow the full funcitonality of the underlying stoage array to be exposed to the VM.

# Usage:
The script takes several arguments:

- -v FQDN for vCenter
- -u username to log into vCenter
- -p password to log into vCenter (of not specified the script will prompt for it)
- -g the names of the VMs to which the RDMs will be added.  this can be a comma seperated list
- -d the serial IDs of the RDMs to add.  these should be obtaintable from the storage array interface when you create new volumes.
- -r rescan the HBA of the ESX node where the VM is located.
- -a action - a for add RDMs and r for remove them
- -s shared Multi-Writer flag.  Required when adding shared RDM

# Sample:
add two RDMs to a single VM.
$ python vm_rdm.py -v vcenter.mydomain.com -u username -g my_oracle_vm -d 81F096D1C1642A69026029C0,81F096D1C1642A69026029C1 -r -a a

add two shared RDMs to two VMs (e.g. Oracle RAC)
$ python vm_rdm.py -v vcenter.mydomain.com -u username -g my-oradb-rac01,my-oradb-rac02 -d 81F096D1C1642A69026029C0,81F096D1C1642A69026029C1 -a a -r -s


# Safety Lock
The script requires the argument -x to be added to the command line before it will actuall add or remove RDMs.
If you omit this argument, the script will test connectivity and report what it would do, but will not add or remove anything from the target VMs.
