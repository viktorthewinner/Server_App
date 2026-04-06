import paramiko
import time

def get_folder_size_bytes(client, folder):
    stdin, stdout, stderr = client.exec_command(f"du -sb {folder} 2>/dev/null | cut -f1 | tail -n 1")
    res = stdout.read().decode().strip()
    return int(res) if res.isdigit() else 0

def get_file_size_bytes(client, path):
    stdin, stdout, stderr = client.exec_command(f"du -b {path} 2>/dev/null | cut -f1 | tail -n 1")
    res = stdout.read().decode().strip()
    return int(res) if res.isdigit() else 0

def get_remote_file_size(client, path):
    stdin, stdout, stderr = client.exec_command(f"du -b {path} 2>/dev/null | cut -f1 | tail -n 1")
    res = stdout.read().decode().strip()
    return int(res) if res.isdigit() else 0

def get_folder_name(client):
    command = "find . -type d -name 'wp-content' -exec dirname {} \; | head -n 1"
    stdin, stdout, stderr = client.exec_command(command)
    path = stdout.read().decode('utf-8').strip()
    return path if path else "."

def execute(host, user, password, port, update_progress, console_log):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        console_log(f"Connecting to {host}...")
        client.connect(host, username=user, password=password, port=int(port), timeout=10)
        
        folder = get_folder_name(client)
        console_log(f"Calculating size for: {folder}...")
        
        total_bytes = get_folder_size_bytes(client, folder)
        if total_bytes == 0:
            console_log("Error: Could not calculate folder size.")
            return 0

        console_log(f"Total size: {total_bytes / (1024*1024):.2f} MB. Starting compression...")

        archive_path = f"{folder}/archive.tar.gz"
        full_command = f"tar -czf {archive_path} -C {folder} --exclude=archive.tar.gz ."
        client.exec_command(full_command)

        while True:
            current_bytes = get_file_size_bytes(client, archive_path)
            estimated_ratio = 0.2 
            progress = min(current_bytes / (total_bytes * estimated_ratio), 0.99)
            update_progress(progress)
            
            stdin, stdout, stderr = client.exec_command("pgrep -f 'tar -czf'")
            if not stdout.read().decode().strip():
                break
            time.sleep(1) 

        update_progress(1.0)
        console_log("✅ Archive completed successfully!")
        final_archive_size = get_file_size_bytes(client, archive_path)
        return final_archive_size # Trimitem mărimea reală a fișierului .tar.gz
    except Exception as e:
        console_log(f"❌ Error: {str(e)}")
        return 0
    finally:
        client.close()

def upload(host, user, password, port, url, total_size_bytes, update_progress, console_log):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        console_log(f"Connecting to {host}...")
        client.connect(host, username=user, password=password, port=int(port), timeout=10)
        
        folder = get_folder_name(client)
        archive_name = "archive.tar.gz"
        
        # Eliminăm slash-urile duble dacă URL-ul are unul la final
        clean_url = url.rstrip('/')
        download_url = f"{clean_url}/{archive_name}"
        
        # Calea completă unde trebuie să ajungă fișierul
        dest_path = f"{folder}/{archive_name}"

        # Pas 1: Download - folosim calea absolută pentru siguranță
        # -q (quiet), -O (output document), -c (continue if interrupted)
        full_command = f"wget -q '{download_url}' -O '{dest_path}'"
        client.exec_command(full_command)

        console_log(f"📥 Downloading archive into: {folder}")

        while True:
            current_size = get_remote_file_size(client, dest_path)
            
            if total_size_bytes > 0:
                # Calculăm progresul raportat la mărimea sursei
                progress = min(current_size / total_size_bytes, 0.99)
                update_progress(progress)
            
            # Verificăm dacă wget mai rulează
            stdin, stdout, stderr = client.exec_command("pgrep wget")
            if not stdout.read().decode().strip():
                # Așteptăm o secundă pentru ca sistemul de fișiere să facă sync
                time.sleep(1)
                final_size = get_remote_file_size(client, dest_path)
                
                # Verificare mai tolerantă (85% din mărimea originală)
                if final_size > 0 and final_size >= (total_size_bytes * 0.85):
                    break
                else:
                    console_log(f"❌ Size mismatch: Got {final_size} bytes, expected ~{total_size_bytes}")
                    raise Exception("Transfer failed or file is too small.")
            
            time.sleep(2)

        update_progress(1.0)
        console_log("✅ Transfer complete. Starting extraction...")

        # Pas 2: Dezarhivare
        # Folosim -xzf (fără 'v' pentru a nu bloca buffer-ul SSH cu mii de linii de text)
        extract_command = f"tar -xzf '{dest_path}' -C '{folder}' --overwrite"
        stdin, stdout, stderr = client.exec_command(extract_command)
        
        # Așteptăm rezultatul
        exit_status = stdout.channel.recv_exit_status()
        error_output = stderr.read().decode().strip()
        
        if exit_status == 0:
            console_log("🚀 Files extracted successfully!")
            client.exec_command(f"rm '{dest_path}'")
            console_log("It is time for you to connect your domain to the new server!")
        else:
            # Afișăm eroarea REALĂ din sistemul Linux
            if "Permission denied" in error_output:
                raise Exception(f"Extraction failed: Permission denied in {folder}")
            elif "not found" in error_output:
                raise Exception("Extraction failed: 'tar' utility is not installed on this server.")
            else:
                raise Exception(f"Extraction failed: {error_output}")

    except Exception as e:
        console_log(f"❌ Error: {str(e)}")
    finally:
        client.close()