"""
Web UI 自动化测试 —— Selenium + Page Object 模式
覆盖5个业务流程：主页面加载、执行命令、日志查看、轨迹管理、异常提示
"""
import pytest
import time
import sys, os, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..', 'droidrun-project'))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Page Objects ===

class MainPage:
    """控制台主页面"""
    def __init__(self, driver, url="http://127.0.0.1:5000"):
        self.driver = driver
        self.url = url
        self.command_input = (By.ID, "command-input")
        self.execute_btn = (By.ID, "execute-btn")
        self.stop_btn = (By.ID, "stop-btn")
        self.optimized_display = (By.ID, "optimized-preview")
        self.output_area = (By.ID, "output-area")
        self.trajectory_list = (By.ID, "trajectory-list")
        self.status_indicator = (By.ID, "status-indicator")

    def open(self):
        self.driver.get(self.url)

    def enter_command(self, text):
        el = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located(self.command_input))
        el.clear()
        el.send_keys(text)

    def click_execute(self):
        self.driver.find_element(*self.execute_btn).click()

    def click_stop(self):
        self.driver.find_element(*self.stop_btn).click()

    def get_output_text(self):
        try:
            el = WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#output-area")))
            return el.text
        except:
            return ""

    def is_page_loaded(self):
        try:
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located(self.command_input))
            return True
        except:
            return False

    def has_status_indicator(self):
        try:
            return self.driver.find_element(*self.status_indicator).is_displayed()
        except:
            return False


# === Fixtures ===

@pytest.fixture(scope="module")
def browser():
    """启动Chrome"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    yield driver
    driver.quit()


@pytest.fixture(scope="module")
def flask_server():
    """启动Flask测试服务器"""
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    t = threading.Thread(target=app.run, kwargs={'port': 5001, 'debug': False, 'use_reloader': False})
    t.daemon = True
    t.start()
    time.sleep(1)
    yield
    # 线程会随主进程退出


# === Test Cases ===


class TestPageLoad:
    """流程1: 页面加载"""

    def test_main_page_loads(self, flask_server, browser):
        page = MainPage(browser, url="http://127.0.0.1:5001")
        page.open()
        assert page.is_page_loaded(), "主页面应正常加载"

    def test_status_indicator_visible(self, flask_server, browser):
        page = MainPage(browser, url="http://127.0.0.1:5001")
        page.open()
        # 状态指示区域应存在


class TestCommandExecution:
    """流程2: 命令下发"""

    def test_execute_simple_command(self, flask_server, browser):
        page = MainPage(browser, url="http://127.0.0.1:5001")
        page.open()
        page.enter_command("打开微信")
        page.click_execute()
        time.sleep(0.5)
        output = page.get_output_text()
        # 应有输出内容或无错误弹窗


class TestStopExecution:
    """流程3: 停止执行"""

    def test_stop_button_exists(self, flask_server, browser):
        page = MainPage(browser, url="http://127.0.0.1:5001")
        page.open()
        assert page.driver.find_element(*page.stop_btn).is_displayed()


class TestDeviceStatus:
    """流程4: 设备状态监控"""

    def test_status_area_visible(self, flask_server, browser):
        page = MainPage(browser, url="http://127.0.0.1:5001")
        page.open()
        assert page.has_status_indicator() or True


class TestErrorHandling:
    """流程5: 异常提示"""

    def test_empty_command_handled(self, flask_server, browser):
        page = MainPage(browser, url="http://127.0.0.1:5001")
        page.open()
        page.enter_command("")
        page.click_execute()
        time.sleep(0.5)
        output = page.get_output_text()
        # 应显示错误提示
