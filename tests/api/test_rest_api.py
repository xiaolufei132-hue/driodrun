"""
REST API 接口自动化测试 —— pytest + requests
三层验证：HTTP状态码 → 响应结构 → 字段值校验
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'droidrun-project'))
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestTrajectoryAPI:
    """轨迹管理接口"""

    def test_get_list_200(self, client):
        resp = client.get('/api/trajectories')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'trajs' in data
        assert isinstance(data['trajs'], list)

    def test_get_detail_exists(self, client):
        resp = client.get('/api/trajectory/test-id')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['traj_id'] == 'test-id'
        assert 'summary' in data
        assert 'log' in data


class TestOptimizeAPI:
    """提示词优化接口"""

    def test_optimize_normal(self, client):
        resp = client.get('/api/optimize-prompt?cmd=打开设置再打开WIFI')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'optimized' in data
        assert len(data['optimized']) > 0

    def test_optimize_empty(self, client):
        resp = client.get('/api/optimize-prompt?cmd=')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['optimized'] == '请输入指令'

    def test_optimize_no_param(self, client):
        resp = client.get('/api/optimize-prompt')
        assert resp.status_code == 200
        assert resp.get_json()['optimized'] == '请输入指令'


class TestExecuteAPI:
    """命令执行接口"""

    def test_execute_normal(self, client):
        resp = client.get('/api/execute?cmd=打开微信')
        assert resp.status_code == 200

    def test_execute_empty(self, client):
        resp = client.get('/api/execute?cmd=')
        assert resp.status_code == 200
        data = resp.data.decode()
        assert 'ERROR' in data or '错误' in data or '未提供' in data

    def test_execute_no_param(self, client):
        resp = client.get('/api/execute')
        assert resp.status_code == 200
        data = resp.data.decode()
        assert 'ERROR' in data or '错误' in data or '未提供' in data


class TestStatusAPI:
    """状态与统计接口"""

    def test_status_200(self, client):
        resp = client.get('/api/status')
        assert resp.status_code == 200

    def test_status_structure(self, client):
        resp = client.get('/api/status')
        data = resp.get_json()
        assert isinstance(data, dict)

    def test_stats_200(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 200

    def test_stats_fields(self, client):
        resp = client.get('/api/stats')
        data = resp.get_json()
        assert 'total_tasks' in data
        assert 'successful_tasks' in data
        assert 'success_rate' in data


class TestStopAPI:
    """停止执行接口"""

    def test_stop_200(self, client):
        resp = client.post('/api/stop')
        assert resp.status_code == 200
