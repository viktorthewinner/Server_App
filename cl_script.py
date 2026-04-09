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

def get_db_credentials(client, folder):
    cmd = f"grep -E 'DB_NAME|DB_USER|DB_PASSWORD' {folder}/wp-config.php"
    stdin, stdout, stderr = client.exec_command(cmd)

    raw_data = stdout.read()
    if not raw_data:
        return {}

    output = raw_data.decode('latin-1', errors='ignore')

    creds = {}
    import re
    name = re.search(r"DB_NAME', '(.+?)'", output)
    user = re.search(r"DB_USER', '(.+?)'", output)
    pw = re.search(r"DB_PASSWORD', '(.+?)'", output)
    
    if name: creds['name'] = name.group(1)
    if user: creds['user'] = user.group(1)
    if pw: creds['pass'] = pw.group(1)
    
    return creds

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

        console_log("🔍 Reading database credentials from wp-config.php...")
        creds = get_db_credentials(client, folder)
        if creds:
            console_log(f"📦 Found database: {creds['name']}. Exporting...")
            db_file = f"{folder}/db_migrate.sql"
            export_cmd = f"mysqldump -u {creds['user']} -p'{creds['pass']}' {creds['name']} > {db_file}"
            client.exec_command(export_cmd)
        else:
            console_log("⚠️ Could not find DB credentials. Skipping DB export.")

        
        client.exec_command(f"rm {folder}/archive.tar.gz")

        archive_path = f"{folder}/archive.tar.gz"
        full_command = f"tar -czf {archive_path} -C {folder} --exclude=archive.tar.gz --exclude='wp-content/uploads/backup' ."
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
        console_log(f"{final_archive_size}")
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
        console_log("🔍 Reading target server database credentials...")
        new_creds = get_db_credentials(client, folder)
        if not new_creds:
            raise Exception("Could not find a wp-config.php on the new server to get DB credentials.")
        
        clear_cmd = f"rm -rf {folder}/*"
        client.exec_command(clear_cmd)
        console_log(f"🧹 Folder {folder} has been cleared of all existing files.")
        
        archive_name = "archive.tar.gz"
        
        clean_url = url.rstrip('/')
        download_url = f"{clean_url}/{archive_name}"
        
        dest_path = f"{folder}/{archive_name}"

        full_command = f"wget -q -c -t 0 --timeout=60 --no-check-certificate '{download_url}' -O '{dest_path}'"
        client.exec_command(full_command)

        console_log(f"📥 Downloading archive into: {folder}")

        while True:
            current_size = get_remote_file_size(client, dest_path)
            
            if total_size_bytes > 0:
                progress = min(current_size / total_size_bytes, 0.99)
                update_progress(progress)
            
            stdin, stdout, stderr = client.exec_command("pgrep wget")
            if not stdout.read().decode().strip():
                time.sleep(2)
                final_size = get_remote_file_size(client, dest_path)
                
                if final_size > 0 and final_size >= (total_size_bytes * 0.35):
                    break
                else:
                    console_log(f"❌ Size mismatch: Got {final_size} bytes, expected ~{total_size_bytes}")
                    raise Exception("Transfer failed or file is too small.")
            
            time.sleep(5)

        update_progress(1.0)
        console_log("✅ Transfer complete. Starting extraction...")

        extract_command = f"tar -xzf '{dest_path}' -C '{folder}' --overwrite --ignore-failed-read"
        stdin, stdout, stderr = client.exec_command(extract_command)
        
        exit_status = stdout.channel.recv_exit_status()
        error_output = stderr.read().decode().strip()
        
        if exit_status == 0:
            console_log("🚀 Files extracted successfully!")
            client.exec_command(f"rm '{dest_path}'")
        else:
            if "Permission denied" in error_output:
                raise Exception(f"Extraction failed: Permission denied in {folder}")
            elif "not found" in error_output:
                raise Exception("Extraction failed: 'tar' utility is not installed on this server.")
            else:
                raise Exception(f"Extraction failed: {error_output}")
            
        db_file = f"{folder}/db_migrate.sql"
        stdin, stdout, stderr = client.exec_command(f"ls {db_file}")
        if stdout.channel.recv_exit_status() == 0:
            console_log(f"🗄️ Importing database into {new_creds['name']}...")
            import_cmd = f"mysql -u {new_creds['user']} -p'{new_creds['pass']}' {new_creds['name']} < {db_file}"
            stdin, stdout, stderr = client.exec_command(import_cmd)
            
            if stdout.channel.recv_exit_status() == 0:
                console_log("✅ Database imported successfully!")
                
                console_log("🔧 Reconfiguring wp-config.php using stream redirection...")

                new_lines = {
                    'DB_NAME': f"define( 'DB_NAME', '{new_creds['name']}' );",
                    'DB_USER': f"define( 'DB_USER', '{new_creds['user']}' );",
                    'DB_PASSWORD': f"define( 'DB_PASSWORD', '{new_creds['pass']}' );"
                }

                for key, new_content in new_lines.items():
                    
                    cmd = (
                        f"sed \"/{key}/c\\{new_content}\" {folder}/wp-config.php > {folder}/wp-config.tmp && "
                        f"cat {folder}/wp-config.tmp > {folder}/wp-config.php && "
                        f"rm {folder}/wp-config.tmp"
                    )
                    
                    stdin, stdout, stderr = client.exec_command(cmd)
                    exit_status = stdout.channel.recv_exit_status()
                    
                    if exit_status != 0:
                        err = stderr.read().decode().strip()
                        console_log(f"⚠️ Warning updating {key}: {err}")
                    else:
                        console_log(f"✅ Updated {key}")

                console_log("✨ wp-config.php is now correctly configured.")
                
                # Cleanup
                client.exec_command(f"rm {db_file}")
                client.exec_command(f"rm {dest_path}")
            else:
                console_log(f"❌ DB Import Error: {stderr.read().decode().strip()}")
        else:
            console_log("⚠️ No SQL file found in archive. Skipping DB import.")

        console_log("✨ Migration finished! Connect your domain now.")

        client.exec_command(f"wp cache flush --path={folder} --allow-root")
        client.exec_command(f"rm -rf {folder}/wp-content/cache/*")


    except Exception as e:
        console_log(f"❌ Error: {str(e)}")
    finally:
        client.close()