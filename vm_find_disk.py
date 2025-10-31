#! /usr/bin/env python3

#
# adds or removes RDMs from a guest VM
#
# requires pyVmomi
# requires pyvim
#
# usage:
#
# python vm_find_disk.py -v vc01.fsa.lab -u gthornton -p mypassword -d SERIALID1,SERIALID2 
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

# parse the command line args
parser = argparse.ArgumentParser(
                    prog='vm_rdm ', usage='%(prog)s [-v -u -p -d -h]',
                    description='find if RDMs are attached to a VMware guest',
                    epilog='coded by Graham Thornton - gthornton@purestorage.com')

parser.add_argument('-v','--vcenter', help='vCenter address', required=True)
parser.add_argument('-u','--username', help='vCenter username', required=True)
parser.add_argument('-p','--password', help='vCenter password', required=False)
parser.add_argument('-d','--serial_ids', help='serial device list', required=True)


args = parser.parse_args()



def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView( content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def get_all_objs(content, vimtype):

    obj_list = []
    container = content.viewManager.CreateContainerView( content.rootFolder, vimtype, True)
    for c in container.view:
        obj_list.append( c.name )
    return obj_list



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

                try:
                #print( dev.backing )
                #print( f'{dev.backing.lunUuid}' )

                    if( serial_id.lower() in str(dev.backing.lunUuid).lower() ):
                        print( f'device match:{dev.deviceInfo.label}' )
                        #print( dev.backing.diskMode )
                        print( f'LUN UUID:{dev.backing.lunUuid}' )
                        my_dev = dev
                        break

                except:
                    break

    return( my_dev )



##############################################

# MAIN BLOCK

##############################################


def doMain( ):

    # we dont need it to barf its guts up when something goes sideways
    sys.tracebacklimit = 0

    print( '============' )
    print( f'vm_query_rdm.py {version} started at {datetime.datetime.now()} ')

    password = args.password
    if ( password == None ):
        password = getpass.getpass(prompt='enter password for vCenter: ')

    serial_id_list=args.serial_ids

    # allow for non SSL
    context = ssl._create_unverified_context()

    # connect to vSphere
    try:
        si = SmartConnect( host = args.vcenter, user = args.username, pwd = password, sslContext=context )

    except:
        raise Exception( 'vcenter connect failed' )

    print( f'connected to {args.vcenter}' )

    # get all the content
    content = si.RetrieveContent()

    print( '============' )
    # get a list of the vms
    try:
        guest_vms = get_all_objs(content, [vim.VirtualMachine] )

    except:
        print( 'failed to retrieve VM content' )

    for guest_vm in guest_vms: 

        #print( f'checking guest VM {guest_vm}' )

        vm = get_obj( content, [vim.VirtualMachine], guest_vm )

        for serial_id in serial_id_list.split( ',' ):

            #print( f'checking for serial id {serial_id}' )
            res = fFindRawDisk2( vm, si, serial_id )
            if res != None: 
                print( f'disk serial id {serial_id} is attached to vm {guest_vm}' )
                #print( res )

    #
    # end of program
    #
    print( '============' )
    print( 'complete' )



if __name__ == "__main__": doMain()


