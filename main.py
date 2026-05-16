"""
我的第一个 Python 程序
"""
import requests
import numpy as np
import pandas as pd

def main():
    print("Hello from Python 3.13!")
    print(f"requests: {requests.__version__}")
    print(f"numpy (as np): {np.__version__}")
    print(f"pandas (as pd): {pd.__version__}")
    
    # 测试 GitHub API
    r = requests.get("https://api.github.com")
    print(f"GitHub API 连接状态: {r.status_code}")

if __name__ == "__main__":
    main()
