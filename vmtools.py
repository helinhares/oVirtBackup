import time
import sys
import datetime
from datetime import date
from ovirtsdk.xml import params

class VMTools:
    """
    Class which holds static methods which are used more than once
    """

    @staticmethod
    def wait_for_snapshot_operation(vm, config, comment):
        """
        Wait for a snapshot operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        while True:
            snapshots = vm.snapshots.list(description=config.get_snapshot_description())
            if snapshots:
                if "ok" in str(snapshots[0].get_snapshot_status()):
                    break
                if config.get_debug():
                    print "Snapshot operation(" + comment + ") in progress ..."
                time.sleep(config.get_timeout())
            else:
                break

    @staticmethod
    def delete_snapshots(vm, config, vm_name):
        """
        Deletes a backup snapshot
        :param vm: Virtual machine object
        :param config: Configuration
        """
        snapshots = vm.snapshots.list(description=config.get_snapshot_description())
        done = False
        if snapshots:
            if config.get_debug():
                print "Found snapshots(" + str(len(snapshots)) + "):"
            for i in snapshots:
                if snapshots:
                    if config.get_debug():
                        print "Snapshots description: " + i.get_description() + ", Created on: " + str(i.get_date())
                    for i in snapshots:
                        try:
                            while True:
                                try:
                                    if not config.get_dry_run():
                                        i.delete()
                                    print "Snapshot deletion started ..."
                                    VMTools.wait_for_snapshot_operation(vm, config, "deletion")
                                    done = True
                                    break
                                except Exception as e:
                                    if "status: 409" in str(e):
                                        time.sleep(config.get_timeout())
                                        continue
                        except Exception as e:
                            print "  !!! Can't delete snapshot for VM: " + vm_name
                            print "  Description: " + i.get_description() + ", Created on: " + str(i.get_date())
                            print "  DEBUG: " + str(e)
                            sys.exit(1)
            if done:
                print "Snapshots deleted"

    @staticmethod
    def delete_vm(api, config, vm_name):
        """
        Delets a vm which was created during backup
        :param vm: Virtual machine object
        :param config: Configuration
        """
        i_vm_name = ""
        done = False
        try:
            for i in api.vms.list():
                i_vm_name = str(i.get_name())
                if i_vm_name.startswith(vm_name + config.get_vm_middle()):
                    print "Delete cloned VM started ..."
                    if not config.get_dry_run():
                        api.vms.get(i_vm_name).delete()
                        while i_vm_name in [vm.name for vm in api.vms.list()]:
                            if config.get_debug():
                                print "Deletion of cloned VM in progress ..."
                            time.sleep(config.get_timeout())
                        done = True
        except Exception as e:
            print "Can't delete cloned VM (" + i_vm_name + ")"
            print "DEBUG: " + str(e)
            sys.exit(1)
        if done:
            print "Cloned VM deleted"

    @staticmethod
    def wait_for_vm_operation(api, config, comment, vm_name):
        """
        Wait for a vm operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param comment: This comment will be used for debugging output
        """
        while str(api.vms.get(vm_name + config.get_vm_middle() + config.get_vm_suffix()).get_status().state) != 'down':
            if config.get_debug():
                print comment + " " + vm_name + " in progress ..."
            time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_backups(api, config, vm_name):
        """
        Delete old backups from the export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """
        exported_vms = api.storagedomains.get(config.get_export_domain()).vms.list()
        for i in exported_vms:
            vm_name = str(i.get_name())
            if vm_name.startswith(vm_name + config.get_vm_middle()):
                datetimeStart = datetime.datetime.combine((datetime.date.today() - datetime.timedelta(config.get_backup_keep_count())), datetime.datetime.min.time())
                timestampStart = time.mktime(datetimeStart.timetuple())
                datetimeCreation = i.get_creation_time()
                datetimeCreation = datetimeCreation.replace(hour=0, minute=0, second=0)
                timestampCreation = time.mktime(datetimeCreation.timetuple())
                if timestampCreation <= timestampStart:
                    print "Backup deletion started for backup: " + vm_name
                    if not config.get_dry_run():
                        i.delete()
                        while vm_name in [vm.name for vm in api.storagedomains.get(config.get_export_domain()).vms.list()]:
                            if config.get_debug():
                                print "Delete old backup in progress ..."
                            time.sleep(config.get_timeout())


    @staticmethod
    def export_clone_vms(api, config, vm_from_list):
        """
        Export the virtual machines cloned to export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """
        try:
            volume_rotate=config.get_volume_rotate()
            if volume_rotate:
               volume_rotate(api, config, 'attach')
            vm_clone = api.vms.get(vm_from_list + config.get_vm_middle() + config.get_vm_suffix())
            print "Export started ..."
            if not config.get_dry_run():
                vm_clone.export(params.Action(storage_domain=api.storagedomains.get(config.get_export_domain())))
                VMTools.wait_for_vm_operation(api, config, "Exporting", vm_from_list)
            print "Exporting finished"
            if volume_rotate:
               volume_rotate(api, config, 'detach')
        except Exception as e:
            print "Can't export cloned VM (" + vm_from_list + config.get_vm_middle() + config.get_vm_suffix() + ") to domain: " + config.get_export_domain()
            print "DEBUG: " + str(e)
            sys.exit(1)


    @staticmethod
    def volume_rotate(api, config, status):
        """
        Attach and Detach export domain as the days of the week
        :param api: ovirtsdk api
        :param config: Configuration
        :param status: 'attach' or 'detach'
        """

        print "'rotate'"
        storage = api.storagedomains.list()
        rotate_position=datetime.date.today().weekday() 
        volumes=dict(yaml.load(config.get_export_domain()))

        volumes_export=[]
        list_storage_domains=datacenter.storagedomains.list()
        for vol in storage:
            if vol.get_name() in volumes.itervalues():
                volumes_export.insert(-1, vol.get_name())

        if volumes_export==[]:
            print "!!! Volumes not found"
            sys.exit(1)


        datacenter=api.datacenters.get(config.get_cluster_name())

        if status == 'attach':
            for export in list_storage_domains:
                if export.get_type()=='export':
                    print "!!! The volume " + export.get_name() + " is already attached"
                    sys.exit(1)

            vol_export=api.storagedomains.get(volumes[rotate_position]);
            datacenter.storagedomains.add(vol_export);

        elif status == 'detach':
            vol_export=datacenter.storagedomains.get(volumes[rotate_position]);
            vol_export.deactivate();
            vol_export.delete();

