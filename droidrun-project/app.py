from flask import Flask
import os
import webbrowser
from config import SystemConfig
from utils.file_utils import ensure_trajectory_dir

app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')

# 注册蓝图和路由
def create_app():
    # 确保轨迹目录存在
    ensure_trajectory_dir()
    
    # 导入视图（必须在函数内部导入，避免循环导入）
    from view import main_blueprint, api_blueprint
    app.register_blueprint(main_blueprint)
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    return app

if __name__ == '__main__':
    app = create_app()
    
    print("=" * 70)
    print("🤖 DroidRun 智能控制台")
    print("=" * 70)
    print(f"轨迹目录: {SystemConfig.TRAJ_BASE_PATH}")
    print(f"工作目录: {os.getcwd()}")
    print(f"AI 模型: {SystemConfig.PROVIDER}/{SystemConfig.MODEL}")
    print("=" * 70)
    print("✨ 主要特性:")
    print("  • 简化的提示词优化器")
    print("  • 智能任务拆分功能")
    print("  • 多部分任务顺序执行")
    print("  • 改进的状态管理")
    print("=" * 70)
    print("🌐 访问地址: http://127.0.0.1:5000")
    print("=" * 70)
    
    # debug 模式下 Flask reloader 会跑两次进程，只在主进程打开浏览器
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        webbrowser.open('http://127.0.0.1:5000')
    
    app.run(debug=True, port=5000, threaded=True)