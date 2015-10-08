import time
import sys
import datetime
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
            snapshots = vm.snapshots.list(
                description=config.get_snapshot_description())

            if snapshots:
                if "ok" in str(snapshots[0].get_snapshot_status()):
                    break
                if config.get_debug():
                    print "Snapshot operation(" + comment + ") in progress..."
                time.sleep(config.get_timeout())
            else:
                break

    @staticmethod
    def wait_for_storage_domain(api, config, status, vol_export_name):
        """
        Wait for a snapshot operation to be finished
        :param vm: Virtual machine object
        :param config: Configuration
        :param status: This is the state that is waiting
        :param vol_export_name: This vol_export_name is name of volume export
        """

        while True:
            try:
                datacenter_storage_domain_status = api.datacenters.get(
                    config.get_cluster_name()).storagedomains.get(
                        vol_export_name).get_status().state
            except:
                print "Volume not attached or not listed in config.cfg"
                sys.exit(1)
            if not datacenter_storage_domain_status == status:
                print ""
                print "Waiting  operation( " + status + " ) in progress ..."
                time.sleep(config.get_timeout())
            else:
                time.sleep(config.get_timeout())
                break

    @staticmethod
    def delete_snapshots(vm, config, vm_name):
        """
        Deletes a backup snapshot
        :param vm: Virtual machine object
        :param config: Configuration
        """

        snapshots = vm.snapshots.list(
            description=config.get_snapshot_description())
        done = False
        if snapshots:
            if config.get_debug():
                print "Found snapshots(" + str(len(snapshots)) + "):"
            for i in snapshots:
                if snapshots:
                    if config.get_debug():
                        print "Snapshots description: " + i.get_description()
                        + ", Created on: " + str(i.get_date())
                    for i in snapshots:
                        try:
                            while True:
                                try:
                                    if not config.get_dry_run():
                                        i.delete()
                                    print "Snapshot deletion started ..."
                                    VMTools.wait_for_snapshot_operation(
                                        vm, config, "deletion")
                                    done = True
                                    break
                                except Exception as e:
                                    if "status: 409" in str(e):
                                        time.sleep(config.get_timeout())
                                        continue
                        except Exception as e:
                            print "  !!! Can't delete snapshot for VM: "\
                                + vm_name
                            print "  Description: " + i.get_description()\
                                + ", Created on: " + str(i.get_date())
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

        while str(api.vms.get(vm_name + config.get_vm_middle()
                  + config.get_vm_suffix()).get_status().state) != 'down':

            if config.get_debug():
                print comment + " " + vm_name + " in progress ..."
            time.sleep(config.get_timeout())

    @staticmethod
    def delete_old_backups(api, config, vm_name, always):
        """
        Delete old backups from the export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """

        exported_vms = api.storagedomains.get(
            VMTools.get_export_domain(api, config, always)).vms.list()
        for i in exported_vms:
            vm_name = str(i.get_name())

            if vm_name.startswith(vm_name + config.get_vm_middle()):
                datetimeStart = datetime.datetime.combine((
                    datetime.date.today() - datetime.timedelta(
                        config.get_backup_keep_count())),
                    datetime.datetime.min.time())
                timestampStart = time.mktime(datetimeStart.timetuple())
                datetimeCreation = i.get_creation_time()
                datetimeCreation = datetimeCreation.replace(
                    hour=0, minute=0, second=0)

                timestampCreation = time.mktime(datetimeCreation.timetuple())

                if timestampCreation <= timestampStart:
                    print "Backup deletion started for backup: " + vm_name

                    if not config.get_dry_run():
                        i.delete()

                        while vm_name in [vm.name for vm in exported_vms]:
                            if config.get_debug():
                                print "Delete old backup in progress ..."
                            time.sleep(config.get_timeout())

    @staticmethod
    def export_vms(api, config, vm_from_list, always):
        """
        Export the virtual machines cloned to export domain
        :param api: ovirtsdk api
        :param config: Configuration
        """

        try:
            vm_clone = api.vms.get(vm_from_list + config.get_vm_middle()
                                   + config.get_vm_suffix())
            print "Export started ..."

            if not config.get_dry_run():
                vm_clone.export(params.Action(
                    storage_domain=api.storagedomains.get(
                        VMTools.get_export_domain(api, config, always))))
                VMTools.wait_for_vm_operation(api, config, "Exporting",
                                              vm_from_list)

            print "Exporting finished"

        except Exception as e:
            print "Can't export cloned VM (" + vm_from_list\
                    + config.get_vm_middle() + config.get_vm_suffix()\
                    + ") to domain: " + VMTools.get_export_domain(api, config,
                                                                  always)
            print "DEBUG: " + str(e)
            sys.exit(1)

    @staticmethod
    def volume_rotate(api, config, status, vol_export_name):
        """
        Attach and Detach export domain as the days of the week
        :param api: ovirtsdk api
        :param config: Configuration
        :param status: 'attach' or 'detach'
        """

        if status == 'attach':
            VMTools.volume_attach(api, config, 'active', vol_export_name)
        elif status == 'detach':
            VMTools.volume_detach(api, config, 'maintenance', vol_export_name)

    @staticmethod
    def verify_volume_attached(api, config):
	"""
        Make sure the volume is attached, if it detaches
        :param api: ovirtsdk api
        :param config: Configuration
        """

        volumes = config.get_export_domain()
        storage = api.storagedomains.list()
        datacenter = api.datacenters.get(config.get_cluster_name())
        list_storage_domains = datacenter.storagedomains.list()
        volumes_export = []

        for vol in storage:
            if vol.get_name() in volumes.itervalues():
                volumes_export.insert(-1, vol.get_name())

        if volumes_export == []:
            print "!!! Volumes not found"
            sys.exit(1)

        for export in list_storage_domains:
            if export.get_type() == 'export':
                print "!!! The volume " + export.get_name()\
                        + " is already attached, Detaching volume!"
                if not config.get_dry_run():
                    VMTools.volume_detach(api, config, 'maintenance',
                                          export.get_name())

    @staticmethod
    def volume_attach(api, config, status, vol_export_name):
        """
        Attach export domain as the days of the week
        :param api: ovirtsdk api
        :param config: Configuration
        :param status: 'attach' or 'detach'
        :param vol_export_name: Name of volume export
        """

        if not config.get_dry_run():
            datacenter = api.datacenters.get(config.get_cluster_name())
            vol_export = api.storagedomains.get(vol_export_name)
            datacenter.storagedomains.add(vol_export)
            VMTools.wait_for_storage_domain(api, config, status,
                                            vol_export_name)

    @staticmethod
    def volume_detach(api, config, status, vol_export_name):
        """
        Detach export domain as the days of the week
        :param api: ovirtsdk api
        :param config: Configuration
        :param status: 'attach' or 'detach'
        :param vol_export_name: Name of volume export
        """

        if not config.get_dry_run():
            datacenter = api.datacenters.get(config.get_cluster_name())
            vol_export = datacenter.storagedomains.get(vol_export_name)
            vol_export.deactivate()
            VMTools.wait_for_storage_domain(api, config, status,
                                            vol_export_name)
            vol_export.delete()

    @staticmethod
    def get_export_domain(api, config, always):
        """
        Get export domain name
        :param config: Configuration
        :param always: True or False
        """
        if always:
            rotate_position = 'always'
        else:
            rotate_position = datetime.date.today().weekday()

        try:
            if not config.get_dry_run():
                export_domains = config.get_export_domain()
                return export_domains[rotate_position]
        except:
            if VMTools.get_always(api, config):
                return export_domains['always']
            print "!!! No domain set for today in config.cfg"

    @staticmethod
    def get_always(api, config):
        """
        Get 'always' in export domain config
        :param api: ovirtsdk api
        :param config: Configuration
        """

        export_domains = config.get_export_domain()
        if 'always' in export_domains:
            return True
