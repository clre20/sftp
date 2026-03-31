import os
import paramiko
import socket
import threading
import logging
from datetime import datetime
import sys

# --- 輸出排版工具 ---
def log_msg(category, message, level="INFO"):
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    padding = " " * (8 - len(category))
    print(f"[{time_str}] [{category}]{padding} {message}", flush=True)

logging.getLogger("paramiko").setLevel(logging.WARNING)

# --- 設定區 ---
HOST_KEY = paramiko.RSAKey(filename='server.key')
LISTEN_PORT = 2222 

USERS_CONFIG = {
    "user1": {
        "password": "123",
        "root_path": os.path.abspath("./data/u1")
    },
    "user2": {
        "password": "456",
        "root_path": os.path.abspath("./data/u2")
    }
}

class StubSFTPServer(paramiko.SFTPServerInterface):
    def __init__(self, server, user_config):
        self.user_config = user_config
        self.root = os.path.normpath(self.user_config["root_path"]) + os.sep
        self.username = server.authenticated_user
        super().__init__(server)

    def _get_local_path(self, path):
        rel_path = path.lstrip("/").replace("/", os.sep)
        abs_path = os.path.normpath(os.path.join(self.root, rel_path))
        if not abs_path.startswith(self.root.rstrip(os.sep)):
            return None
        return abs_path

    def list_folder(self, path):
        local_path = self._get_local_path(path)
        log_msg("指令", f"<{self.username}> LIST   - {path}")
        
        if local_path is None or not os.path.isdir(local_path):
            log_msg("狀態", "  L 狀態: 失敗 (權限不足或路徑不存在)", "WARN")
            return paramiko.SFTP_PERMISSION_DENIED
        
        try:
            items = os.listdir(local_path)
            log_msg("狀態", f"  L 狀態: 成功 (找到 {len(items)} 個項目)")
            out = []
            for fname in items:
                f_abs = os.path.join(local_path, fname)
                st = os.stat(f_abs)
                out.append(paramiko.SFTPAttributes.from_stat(st, fname))
            return out
        except OSError as e:
            log_msg("狀態", f"  L 狀態: 錯誤 ({e})", "ERROR")
            return paramiko.SFTP_FAILURE

    def stat(self, path):
        local_path = self._get_local_path(path)
        return paramiko.SFTPAttributes.from_stat(os.stat(local_path))

    def lstat(self, path):
        return self.stat(path)

    def canonicalize(self, path):
        if path == "." or path == "" or not path: return "/"
        return "/" + path.lstrip("/").replace(os.sep, "/")

    def open(self, path, flags, attr):
        local_path = self._get_local_path(path)
        mode_desc = "READ" if not (flags & os.O_WRONLY or flags & os.O_RDWR) else "WRITE"
        log_msg("指令", f"<{self.username}> OPEN   - {path} [{mode_desc}]")
        
        if local_path is None: 
            return paramiko.SFTP_PERMISSION_DENIED
        try:
            if flags & os.O_WRONLY: mode = "wb"
            elif flags & os.O_RDWR: mode = "r+b"
            else: mode = "rb"
            
            if (flags & os.O_CREAT) and not os.path.exists(local_path):
                open(local_path, 'ab').close()

            f = open(local_path, mode)
            obj = paramiko.SFTPHandle(flags)
            obj.readfile = f
            obj.writefile = f
            return obj
        except Exception as e:
            log_msg("狀態", f"  L 狀態: 開啟失敗 ({e})")
            return paramiko.SFTP_FAILURE

    def mkdir(self, path, attr):
        local_path = self._get_local_path(path)
        log_msg("指令", f"<{self.username}> MKDIR  - {path}")
        try:
            os.mkdir(local_path)
            log_msg("狀態", "  L 狀態: 成功建立目錄")
            return paramiko.SFTP_OK
        except Exception:
            return paramiko.SFTP_FAILURE

    def remove(self, path):
        local_path = self._get_local_path(path)
        log_msg("指令", f"<{self.username}> DELETE - {path}")
        try:
            os.remove(local_path)
            log_msg("狀態", "  L 狀態: 檔案已刪除")
            return paramiko.SFTP_OK
        except Exception:
            return paramiko.SFTP_FAILURE

    def rename(self, oldpath, newpath):
        log_msg("指令", f"<{self.username}> RENAME - {oldpath} -> {newpath}")
        old_local = self._get_local_path(oldpath)
        new_local = self._get_local_path(newpath)
        try:
            os.rename(old_local, new_local)
            log_msg("狀態", "  L 狀態: 重新命名成功")
            return paramiko.SFTP_OK
        except Exception:
            return paramiko.SFTP_FAILURE

    def chattr(self, path, attr):
        return paramiko.SFTP_OK

class StubServer(paramiko.ServerInterface):
    def __init__(self, client_addr):
        self.authenticated_user = None
        self.client_addr = client_addr

    def check_auth_password(self, username, password):
        if username in USERS_CONFIG and USERS_CONFIG[username]["password"] == password:
            self.authenticated_user = username
            log_msg("驗證", f"使用者 '{username}' 登入成功 (來自 {self.client_addr[0]})")
            return paramiko.AUTH_SUCCESSFUL
        log_msg("驗證", f"登入失敗: 使用者 '{username}' 密碼錯誤 (來自 {self.client_addr[0]})")
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_subsystem_request(self, channel, name):
        if name == 'sftp':
            user_cfg = USERS_CONFIG.get(self.authenticated_user)
            log_msg("系統", f"為 {self.authenticated_user} 啟動 SFTP 子系統")
            sftp = paramiko.SFTPServer(channel, "sftp", self, StubSFTPServer, user_cfg)
            sftp.start()
            return True
        return False

    def get_allowed_auths(self, username):
        return 'password'

def handle_client(client_sock, addr):
    transport = None
    try:
        log_msg("系統", f"偵測到新連線: {addr[0]}:{addr[1]}")
        transport = paramiko.Transport(client_sock)
        transport.add_server_key(HOST_KEY)
        server = StubServer(addr)
        transport.start_server(server=server)
        while transport.is_active():
            transport.join(timeout=1)
    except Exception as e:
        log_msg("系統", f"連線中斷: {e}")
    finally:
        log_msg("系統", f"連線關閉: {addr[0]}")
        if transport: transport.close()

def run_server():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', LISTEN_PORT))
    server_sock.listen(10)
    
    print("-" * 60)
    log_msg("系統", f"SFTP 伺服器啟動完成")
    log_msg("系統", f"監聽地址: 0.0.0.0:{LISTEN_PORT}")
    print("-" * 60)

    while True:
        client, addr = server_sock.accept()
        threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

if __name__ == "__main__":
    run_server()