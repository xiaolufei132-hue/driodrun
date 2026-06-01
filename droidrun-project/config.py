import os

class SystemConfig:
    # DroidRun 配置
    PROVIDER = "DeepSeek"
    MODEL = "deepseek-chat"
    
    # 执行参数
    MAX_STEPS = 20
    TIMEOUT = 300  # 5分钟
    
    # 虚拟环境路径
    VENV_PYTHON = r"C:\Users\32765\.venv\Scripts\python.exe"
    
    # 轨迹路径
    TRAJ_BASE_PATH = r"C:\Users\32765\trajectories"
    
    # 应用配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # SSE 配置
    SSE_RETRY_TIMEOUT = 30000  # 30秒重连时间