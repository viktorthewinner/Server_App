import paramiko
import socket
import time

def get_folder_size_bytes(client, folder):
    """Returnează dimensiunea folderului în Bytes."""
    stdin, stdout, stderr = client.exec_command(f"du -sb {folder} | cut -f1")
    res = stdout.read().decode().strip()
    return int(res) if res.isdigit() else 0

def get_file_size_bytes(client, path):
    """Returnează dimensiunea actuală a arhivei în Bytes."""
    stdin, stdout, stderr = client.exec_command(f"du -b {path} | cut -f1")
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
            return

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

    except Exception as e:
        console_log(f"❌ Error: {str(e)}")
    finally:
        client.close()