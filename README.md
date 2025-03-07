# Python 開發環境設置（使用 VSCode 與 PyCharm）

## 環境版本
- Python 版本：3.13.2
- 系統內建版本：3.9.6

## 在 VSCode 建立虛擬環境（venv）
在 PyCharm 建立專案時，會自動建立虛擬環境，使每個專案擁有獨立的 Python 套件。但在 VSCode 需要手動建立，方法如下：

### 1. 建立虛擬環境
打開終端機，進入專案資料夾，輸入：
```sh
python3 -m venv venv
```

### 2. 啟動虛擬環境
```sh
source venv/bin/activate
```
啟動成功後，終端機會顯示類似以下內容：
```sh
(venv) user@MacBook ~$ 
```

### 3. 使用 VSCode 開啟專案
在啟動虛擬環境的狀態下，輸入：
```sh
code .
```

### 4. 安裝 Python 套件
#### 1. 更新 pip
```sh
pip install --upgrade pip
```

#### 2. 安裝特定套件
```sh
pip install numpy pandas
```

#### 3. 一次安裝所有需求套件
如果專案有 `requirements.txt`，可使用以下指令安裝所有依賴：
```sh
pip install -r requirements.txt
```

#### 4. 查看已安裝套件
```sh
pip list
```

### 5. 退出虛擬環境
```sh
deactivate
```

## 選擇 Python 解析器
1. 按 `Cmd + Shift + P`
2. 搜尋 `Python: Select Interpreter`
3. 選擇 `./venv/bin/python`

## 在 PyCharm 建立專案（自動建立 venv）
使用 PyCharm 建立專案時，會自動設定虛擬環境，無需手動部署。

### 1. 建立新專案
1. 開啟 PyCharm，點選 `Create New Project`
2. 選擇 `New environment using`，確保 `Virtualenv` 被選取
3. `Location` 選擇專案資料夾
4. `Base interpreter` 選擇系統的 Python 版本
5. 勾選 `Inherit global site-packages`（可選）
6. 點擊 `Create` 創建專案

### 2. 安裝 Python 套件
在 `Terminal` 視窗中輸入：
```sh
pip install numpy pandas
```
或透過 `File -> Settings -> Project: <你的專案名稱> -> Python Interpreter` 來管理套件。


### 引用
stocker 取自 https://github.com/WillKoehrsen/Data-Analysis