import EndaceDevices
import pysftp
import threading
from netmiko import ConnectHandler


def enter_maintenance_mode(connection):
    connection.config_mode()
    output = connection.send_command("maintenance-mode noconfirm", strip_prompt = False)
    if "(maintenance)" in output:
        return True
    else:
        print(output)
        print("issue obtaining maintenance mode")
        return False

def install_hotfix(hotfix_name_full, hfn_installed, device):
    conn = ConnectHandler(**device)
    if not enter_maintenance_mode(conn):
        print(device["host"] + "could not enter maintenance mode. Failing gracefully")
        conn.close()
        return False
    conn.send_command("package install " + hotfix_name_full)
    output = conn.send_command("show packages")
    if hfn_installed in output:
        print(device["host"] + "successfully installed on host " + device["host"] + ". rebooting")
        conn.save_config()
        conn.send_command_timing("reload")
        return True
    else:
        print(device["host"] + "possible issue with install. Troubleshoot host " + device["host"])
        return False
    pass

def transfer_via_sftp(filepath, hostname, user, pw):
    opts = pysftp.CnOpts()
    opts.hostkeys = None
    conn = pysftp.Connection(host=hostname,username=user, password=pw, cnopts = opts)
    conn.chdir("/endace/packages")
    conn.put(filepath)
    if conn.exists("OSm6.4.x-CumulativeHotfix-v1.end"):
        conn.close()
        print(hostname + "tx completed successfully for host " + hostname)
        return True
    else:
        conn.close()
        print(hostname + "tx failed. Upload manually for host " + hostname)
        return False

if __name__ == "__main__":
    hf_name_as_installed = "OSm6.4.x-CumulativeHotfix"
    hf_name_full = hf_name_as_installed + "-v1"
    path = "U:/" + hf_name_full + ".end"

    thread_list = []
    devices = EndaceDevices.all_devices

    for dev in devices:
        thread_list.append(threading.Thread(target=transfer_via_sftp, args=(path, dev["host"], dev['username'], dev['password'])))

    for thread in thread_list:
        thread.start()

    for thread in thread_list:
        thread.join()
    
    print("File transferred everywhere")
    thread_list = []

    for dev in devices:
        thread_list.append(threading.Thread(target=install_hotfix, args=(hf_name_full, hf_name_as_installed,dev)))

    for thread in thread_list:
        thread.start()

    for thread in thread_list:
        thread.join()

    print("Hotfix installed everyone. Monitor for devices coming back up")
    pass
