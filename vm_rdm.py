#! /usr/bin/env python3

#
# adds or removes RDMs from a guest VM
#
# requires pyVmomi
# requires pyvim
#
# usage:
#
# python vm_rdm.x.py -v vc01.fsa.lab -u gthornton -g gct-oradb-rac01 -d 81F096D1C1642A690268A374,81F096D1C1642A690268A375 -r -a a -x
#

import sys
import os
import re
import datetime
import json
import argparse
import getpass

from pyVmomi import vim
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, Disconnect
from pyVim.task import WaitForTasks

import ssl

# global variables

version = "1.0.0"

def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


#
# find a disk on a guest vm
#
def fFindRawDisk2( vm, si, serial_id ):

    spec = vim.vm.ConfigSpec()
    my_dev = None

#    print( spec )
    # get all disks on a VM, set unit_number to the next available
    unit_number = 0
    for dev in vm.config.hardware.device:

        my_dev_label = str(dev.deviceInfo.label)
        if ("HARD DISK" in my_dev_label.upper()):

            my_disk_mode = dev.backing.diskMode
            if( "INDEPENDENT_PERSISTENT" == my_disk_mode.upper()):

                #print( dev.backing )
                #print( f'{dev.backing.lunUuid}' )

                if( serial_id.lower() in str(dev.backing.lunUuid).lower() ):
                    print( f'device match:{dev.deviceInfo.label}' )
                    #print( dev.backing.diskMode )
                    print( f'LUN UUID:{dev.backing.lunUuid}' )
                    my_dev = dev
                    break

    return( my_dev )



#
# add an RDM to the specified VM
#
def mAddRawDisk( my_safe_mode, vm, si, device_path, serial_id, shared_disk ):

    my_dev = fFindRawDisk2( vm, si, serial_id )

    if( my_dev != None ):
        print( 'device is already mapped to this vm' )
        return

    spec = vim.vm.ConfigSpec()

#    print( spec )
    # get all disks on a VM, set unit_number to the next available
    unit_number = 0
    for dev in vm.config.hardware.device:
        if hasattr(dev.backing, 'fileName'):
            unit_number = int(dev.unitNumber) + 1
            # unit_number 7 reserved for scsi controller
            if unit_number == 7:
                unit_number += 1
            if unit_number >= 16:
                print( "we don't support this many disks" )
                return
        if isinstance(dev, vim.vm.device.VirtualSCSIController):
             controller = dev

    disk_spec = vim.vm.device.VirtualDeviceSpec()
    disk_spec.fileOperation = "create"
    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = vim.vm.device.VirtualDisk()
    rdm_info = vim.vm.device.VirtualDisk.RawDiskMappingVer1BackingInfo()
    disk_spec.device.backing = rdm_info
#     print( disk_spec.device.backing )
    disk_spec.device.backing.compatibilityMode = 'physicalMode'
    disk_spec.device.backing.diskMode = 'independent_persistent'
    if ( shared_disk ): disk_spec.device.backing.sharing = 'sharingMultiWriter'
    disk_spec.device.backing.deviceName = device_path
    disk_spec.device.unitNumber = unit_number
    disk_spec.device.controllerKey = controller.key

#    print( disk_spec )

    if my_safe_mode:

        print( f'safety lock engaged, would have added raw disk to {vm.config.name}' )

    else:
        try:

            spec.deviceChange = [disk_spec]
            WaitForTasks([vm.ReconfigVM_Task(spec=spec)], si=si)
            print( f'raw disk added to {vm.config.name}' )

        except:
            raise Exception( 'raw disk add failed' )



#
# add a shared RDM to the additional guest vms
#
def mShareRawDisk(my_safe_mode, vm_src, vm_tgt, si, serial_id ):

    # see if the disk is already mapped to this vm
    my_dev = fFindRawDisk2( vm_tgt, si, serial_id )

    if( my_dev != None ):
        print( 'device already mapped to this vm' )
        return

    # get the details of the disk from the source vm
    my_dev = fFindRawDisk2( vm_src, si, serial_id )

    if( my_dev == None ):
        print( 'device not found on the source vm' )
        return

    # check the disk is multi-writer
    if( str(my_dev.backing.sharing) != 'sharingMultiWriter' ):
        print( 'device is not set to shared-multi-writer' )
        print( f'sharing status is:{my_dev.backing.sharing}' )
        return

    spec = vim.vm.ConfigSpec()
    disk_spec = vim.vm.device.VirtualDeviceSpec()

    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
    disk_spec.device = my_dev
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [disk_spec]

    if my_safe_mode:

        print( f'safety lock engaged, would have shared disk to {vm_tgt.config.name}' )

    else:

        spec.deviceChange = [disk_spec]
        WaitForTasks([vm_tgt.ReconfigVM_Task(spec=spec)], si=si)
        print( f'raw disk shared to {vm_tgt.config.name}' )

#
# remove an RDM to the specified VM
#
def mRemoveRawDisk(my_safe_mode, vm, si, serial_id ):

    my_dev = fFindRawDisk2( vm, si, serial_id  )

    if( my_dev == None ):
        print( 'device not found on this vm' )
        return

    spec = vim.vm.ConfigSpec()
    disk_spec = vim.vm.device.VirtualDeviceSpec()

    # is this the VM that the disk was first attached to?
    #print( str(vm.config.name)+"/" )
    if( str(vm.config.name)+"/" in str(my_dev.backing.fileName) ):

        print( 'this is the primary VM, backing file will be removed' )
        disk_spec.fileOperation = vim.vm.device.VirtualDeviceSpec.FileOperation.destroy

    else:
        print( 'this is NOT the primary VM' )

    disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
    disk_spec.device = my_dev
    spec = vim.vm.ConfigSpec()
    spec.deviceChange = [disk_spec]

    if my_safe_mode:

        print( f'safety lock engaged, would have removed raw disk from {vm.config.name}' )

    else:

        spec.deviceChange = [disk_spec]
        WaitForTasks([vm.ReconfigVM_Task(spec=spec)], si=si)
        print( f'raw disk removed from {vm.config.name}' )


#
# for a given VM guest name, determine which VMware hosts it is running on
#

def fQueryESXRuntimeHost( service_instance, vm_name ):

    vm = None
    host_name = 'not found'

    content = service_instance.RetrieveContent()
    #print( content )
    try:
        vm = get_obj(content, [vim.VirtualMachine], vm_name)

        return str(vm.runtime.host)

    except:
        return host_name


#
# for a given VMware host, return the host object
#
def fQueryESXServer2( service_instance, runtime_host_name ):

    my_host = None

#    print( 'check for '+str(host_name) )

    content = service_instance.RetrieveContent()
    host_view = content.viewManager.CreateContainerView( content.rootFolder, [vim.HostSystem], True )
    for host in host_view.view:

        if str(host) == runtime_host_name:
            my_host = host

    host_view.Destroy()

    return my_host

#
# determine if ESX can see an RDM with the name of the volumes provided
# returns a dictionary
#

def fQueryESXServerVols( host, my_serial_id_list ):

    dictData={}

    storage_system = host.configManager.storageSystem
    luns = storage_system.storageDeviceInfo.scsiLun

    for lun in luns:
        # Check if it's a disk LUN and not already in use
        if hasattr(lun, 'deviceType') and lun.deviceType == 'disk':

             #print( f'canonical name:{lun.canonicalName} device path:{lun.devicePath}' )
             for serial_id in my_serial_id_list.split( ',' ):

                 #print( serial_id )

                 if serial_id.lower() in str(lun.canonicalName).lower():

                     dictData.update({ serial_id: lun.canonicalName+'|'+lun.devicePath })
                     #print( f'canonical name:{lun.canonicalName} device path:{lun.devicePath}' )

    return dictData




##############################################

# MAIN BLOCK

##############################################


def doMain( ):

    # we dont need it to barf its guts up when something goes sideways
    sys.tracebacklimit = 0

    # parse the command line args
    parser = argparse.ArgumentParser(
                    prog='vm_rdm ', usage='%(prog)s [-a -v -u -p -g -d -r -s -x -h]',
                    description='add RDMs to a VMware guest VM',
                    epilog='coded by Graham Thornton - gthornton@purestorage.com')

    parser.add_argument('-a','--action', help='action [a]dd, [r]emove - defaults to add', required=False)
    parser.add_argument('-v','--vcenter', help='vCenter address', required=True)
    parser.add_argument('-u','--username', help='vCenter username', required=True)
    parser.add_argument('-p','--password', help='vCenter password', required=False)
    parser.add_argument('-g','--guest_vm', help='comma seperated guest VM name list', required=True)
    parser.add_argument('-d','--serial_ids', help='serial device list', required=True)
    parser.add_argument('-r','--rescan_hba', action='store_true', help="specify flag to rescan HBA (default is no)")
    parser.add_argument('-s','--shared_disk', action='store_true', help="specify flag to enable multi-writer-flag")
    parser.add_argument('-x','--execute_lock', action='store_false', help="specify -x to actually add the RDMs (default is safety lock on)")

    args = parser.parse_args()

    print( '============' )
    print( f'vm_rdm.py {version} started at {datetime.datetime.now()} ')

    password = args.password
    if ( password == None ):
        password = getpass.getpass(prompt='enter password for vCenter: ')

    # action must be A or R
    action = args.action
    if( action == None ): action='A'
    if( action.upper() not in ['A','R'] ):
        raise Exception( 'action must be A or R' )

    serial_id_list=args.serial_ids
    lst_rescanned=[]

    # allow for non SSL
    context = ssl._create_unverified_context()

    # connect to vSphere
    try:
        si = SmartConnect( host = args.vcenter, user = args.username, pwd = password, sslContext=context )

    except:
        raise Exception( 'vcenter connect failed' )

    print( f'connected to {args.vcenter}' )
    content = si.RetrieveContent()

    my_guest_vms = args.guest_vm.split(',')

    if ( not args.shared_disk and len( my_guest_vms )>1 ):
        raise Exception( 'multiple hosts require shared disk mode' )

    shared="dedicated"
    if( args.shared_disk ): shared="shared"

    for guest_vm in my_guest_vms:

        print( '============' )

        my_esx_host = fQueryESXRuntimeHost( si, guest_vm )
        my_esx_server_obj = fQueryESXServer2( si, my_esx_host )

        print( f'locating guest vm:{guest_vm}' )
        print( f'ESX host:{my_esx_host}' )
        print( f'ESX server:{my_esx_server_obj.name}' )

        #
        # do we rescan the HBA?
        #
        if args.rescan_hba:

            print( '============' )

            if( my_esx_server_obj.name in lst_rescanned ):
                print( 'the HBAs for this server have already been rescanned' )

            else:
                print( f'rescanning HBAs on host: {my_esx_server_obj.name}' )
                my_esx_server_obj.configManager.storageSystem.RescanAllHba()
                lst_rescanned.append( my_esx_server_obj.name )
                print( f'{lst_rescanned}' )

        print( '============' )

        #
        # can ESX see the volumes?
        #
        dictVols = fQueryESXServerVols( my_esx_server_obj, serial_id_list )

#        for index, (key, value) in enumerate(dictVols.items()):
#            print(f"Index: {index}, Key: {key}, Value: {value}")

        #
        # add the RDM to the VM
        #
        vm = get_obj(content, [vim.VirtualMachine], guest_vm )
        #print( vm )

        for serial_id in serial_id_list.split( ',' ):

            my_payload = dictVols.get( serial_id, "none" )
            if ( my_payload == "none" ):
                print( f'serial id {serial_id} was not found' )

            else:

                my_payload_list = my_payload.split( '|' )

                # if we are adding RDMs
                if ( action.upper() == 'A' ):

                    print( f'adding {shared} RDM {my_payload_list[1]}' )

                    # if this is the first guest vm, save it
                    if ( guest_vm == my_guest_vms[0] ):
                        vm_1st = vm

                        mAddRawDisk( args.execute_lock, vm, si, my_payload_list[1], serial_id, args.shared_disk )

                    else:

                        mShareRawDisk( args.execute_lock, vm_1st, vm, si, serial_id )

                elif( action.upper() == 'R' ):

                    print( f'removing RDM {my_payload_list[1]}' )
                    mRemoveRawDisk( args.execute_lock, vm, si, serial_id )

    #
    # end of program
    #
    print( '============' )
    print( 'complete' )



if __name__ == "__main__": doMain()


