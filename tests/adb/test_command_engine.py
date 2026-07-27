"""
ADB 命令执行引擎 —— 手工测试用例集
等价类划分 + 边界值分析，覆盖四大类场景
"""
import pytest
from flask import url_for
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'droidrun-project'))
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestNormalCommands:
    """正常指令 —— 等价类：有效的自然语言命令"""

    def test_simple_action(self, client):
        resp = client.get('/api/execute?cmd=打开微信')
        assert resp.status_code == 200
        assert b'data:' in resp.data

    def test_chinese_command(self, client):
        resp = client.get('/api/execute?cmd=向上滑动屏幕')
        assert resp.status_code == 200

    def test_english_command(self, client):
        resp = client.get('/api/execute?cmd=open chrome browser')
        assert resp.status_code == 200

    def test_mixed_language(self, client):
        resp = client.get('/api/execute?cmd=打开APP Store搜索微信')
        assert resp.status_code == 200

    def test_with_punctuation(self, client):
        resp = client.get('/api/execute?cmd=截图保存到桌面！')
        assert resp.status_code == 200

    def test_long_but_valid(self, client):
        resp = client.get('/api/execute?cmd=打开设置找到显示与亮度然后把亮度调到百分之五十然后截图保存')
        assert resp.status_code == 200

    def test_nested_task(self, client):
        resp = client.get('/api/execute?cmd=先打开微信然后点击通讯录然后再点击张三然后发一条你好')
        assert resp.status_code == 200

    def test_optimize_simple(self, client):
        resp = client.get('/api/optimize-prompt?cmd=打开设置')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'optimized' in data

    def test_optimize_complex(self, client):
        resp = client.get('/api/optimize-prompt?cmd=打开浏览器搜索：天气')
        assert resp.status_code == 200

    def test_trajectory_list_empty(self, client):
        resp = client.get('/api/trajectories')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'trajs' in data
        assert isinstance(data['trajs'], list)


class TestErrorCommands:
    """异常指令 —— 等价类：无效/错误输入"""

    def test_empty_command(self, client):
        resp = client.get('/api/execute?cmd=')
        assert resp.status_code == 200
        assert b'ERROR' in resp.data or b'错误' in resp.data

    def test_missing_cmd_param(self, client):
        resp = client.get('/api/execute')
        assert resp.status_code == 200
        assert b'ERROR' in resp.data or b'错误' in resp.data

    def test_empty_optimize(self, client):
        resp = client.get('/api/optimize-prompt?cmd=')
        data = resp.get_json()
        assert data['optimized'] == '请输入指令'

    def test_missing_optimize_param(self, client):
        resp = client.get('/api/optimize-prompt')
        data = resp.get_json()
        assert data['optimized'] == '请输入指令'

    def test_special_chars_only(self, client):
        resp = client.get('/api/execute?cmd=@#$%^&*()')
        assert resp.status_code == 200

    def test_whitespace_only(self, client):
        resp = client.get('/api/execute?cmd=   ')
        assert resp.status_code == 200
        assert b'ERROR' in resp.data or b'错误' in resp.data

    def test_stop_without_running(self, client):
        resp = client.post('/api/stop')
        assert resp.status_code == 200

    def test_trajectory_not_found(self, client):
        resp = client.get('/api/trajectory/nonexistent_id')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['traj_id'] == 'nonexistent_id'


class TestBoundaryValues:
    """边界值分析"""

    def test_max_length_command(self, client):
        cmd = '打开' * 500  # 1000字符
        resp = client.get(f'/api/execute?cmd={cmd[:2000]}')
        assert resp.status_code == 200

    def test_single_char(self, client):
        resp = client.get('/api/execute?cmd=1')
        assert resp.status_code == 200

    def test_unicode_emoji(self, client):
        resp = client.get('/api/execute?cmd=打开📱微信🔍')
        assert resp.status_code == 200

    def test_newline_in_command(self, client):
        resp = client.get('/api/execute?cmd=第一行\n第二行')
        assert resp.status_code == 200

    def test_spaces_around(self, client):
        resp = client.get('/api/execute?cmd=  打开微信  ')
        assert resp.status_code == 200

    def test_optimize_long_input(self, client):
        cmd = '打开' * 500
        resp = client.get(f'/api/optimize-prompt?cmd={cmd[:2000]}')
        assert resp.status_code == 200


class TestEmptyInput:
    """空输入场景"""

    def test_execute_no_params(self, client):
        resp = client.get('/api/execute')
        assert b'ERROR' in resp.data or b'错误' in resp.data

    def test_optimize_no_params(self, client):
        resp = client.get('/api/optimize-prompt')
        data = resp.get_json()
        assert data['optimized'] == '请输入指令'

    def test_execute_empty_string(self, client):
        resp = client.get('/api/execute?cmd=')
        assert b'ERROR' in resp.data or b'错误' in resp.data


class TestStatusAndStats:
    """"状态与统计接口测试"""

    def test_get_status(self, client):
        resp = client.get('/api/status')
        assert resp.status_code == 200

    def test_get_stats(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'total_tasks' in data
        assert 'success_rate' in data
