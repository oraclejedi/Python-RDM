# Python-RDM
Python script to add or remove RDMs from a VMware guest VM

Note: This script uses the pypureclient Python library.
Theory of Operation:
This script is designed to use the "pod-clone" feature of a Pure Storage Flash Array to quickly clone a pod with an exported NFS file system.

The snapshot functionality of Purity's FA file delivers a read-only copy of the files in the file system. To provide a writeable copy, the file system needs to be put into a pod, and then cloned, and re-exported. The pod-clone functionalty is instant and consumes minimal space as the two exported file systems are fully deduplicated. This script automates the entire process.

After the pod has been cloned and exported, the exported file systems may be mounted in the guest OS.

#Usage:
The script takes several arguments:

- -v
- -u username to log into vCenter
- -p password to log into vCenter (of not specified the script will prompt for it)
- -g the names of the VMs to which the RDMs will be added.  this can be a comma seperated list
- -d the serial IDs of the RDMs to add.  these should be obtaintable from the storage array interface when you create new volumes.
- -r rescan the HBA of the ESX node where the VM is located.
- -a action - a for add RDMs and r for remove them
- -s shared Multi-Writer flag.  Required when adding shared RDM

# Sample:
add two RDMs to a single VM.
$ python vm_rdm.py -v myesxiserver -u username -g my_oracle_vm -d 81F096D1C1642A69026029C0,81F096D1C1642A69026029C1 -r -a a

add two shared RDMs to two VMs (e.g. Oracle RAC)
$ python vm_rdm.py -v myesxiserver -u username -g my-oradb-rac01,my-oradb-rac02 -d 81F096D1C1642A69026029C0,81F096D1C1642A69026029C1 -a a -r -s


# Safety Lock
The script requires the argument -x to be added to the command line before it will actuall add or remove RDMs.
If you omit this argument, the script will test connectivity and report what it would do, but will not add or remove anything from the target VMs.
