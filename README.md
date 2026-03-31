<div align="center">

# 簡易 Python SFTP 伺服器

[![Python Version](https://img.shields.io/badge/python-3.x-blue.svg)](https://www.python.org/)
[![Library](https://img.shields.io/badge/library-paramiko-orange.svg)](https://www.paramiko.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](#)

</div>

---

### 特色
> [!TIP]
> 本工具專為需要快速建立臨時 SFTP 傳輸環境的開發者設計。

* **多用戶支援**：可於設定檔中輕鬆定義多組帳號密碼。
* **目錄隔離 (Chroot)**：每個使用者強制鎖定在其專屬的根目錄路徑下，確保安全性。
* **即時日誌系統**：詳細紀錄連線、驗證狀態及所有檔案操作指令（LIST, OPEN, DELETE 等）。
* **高相容性**：支援各類 SFTP 用戶端（如 WinSCP, FileZilla, Cyberduck）。

---

### 快速開始

#### 1. 準備環境
安裝必要的 Python 函式庫：
```bash
pip install paramiko
```

#### 2. 產生存取金鑰
伺服器啟動前需具備 RSA 私鑰。請在專案目錄下開啟 PowerShell 執行：
```powershell
ssh-keygen -t rsa -m PEM -f server.key -N '""'
```

#### 3. 啟動服務
* **Windows 用戶**：雙擊執行 `SFTP Server.bat`。
* **手動啟動**：執行 `python main.py`。

---

### 伺服器配置

您可以在 `main.py` 中直接調整以下參數：

| 參數 | 預設值 | 說明 |
| :--- | :--- | :--- |
| **LISTEN_PORT** | `2222` | 伺服器監聽連接埠 |
| **HOST_KEY** | `server.key` | 指定伺服器金鑰檔案 |

#### 使用者權限設定
```python
USERS_CONFIG = {
    "user1": {
        "password": "123",                    # 登入密碼
        "root_path": os.path.abspath("./data/u1") # 檔案根目錄
    }
}
```

---

### 專案結構
```text
.
├── main.py              # 伺服器核心程式
├── SFTP Server.bat      # Windows 啟動腳本
├── README.md            # 專案說明文件
├── server.key           # RSA 私鑰 
└── data/                # 數據存放區
    ├── u1/
    └── u2/
```

---

<div align="center">

### 安全宣告
**此工具主要用於測試與開發環境。若於生產環境使用，請務必更換複雜密碼並對 `server.key` 進行妥善權限管理。**

</div>
