import os
import subprocess
import threading
import time
import datetime
import uuid
from config import SystemConfig
from utils.file_utils import save_trajectory_summary, save_trajectory_log


class ProcessManager:
    def __init__(self):
        self.current_process = None
        self.is_running = False
        self.current_command = ""
        self.process_lock = threading.Lock()
        self.task_parts = []          # 存储拆分后的任务列表
        self.current_task_index = 0   # 当前执行的任务索引
        self.original_command = ""    # 原始用户指令

    def get_status(self):
        """获取当前执行状态"""
        has_process = False
        process_alive = False

        with self.process_lock:
            if self.current_process:
                try:
                    # 检查进程是否还在运行
                    return_code = self.current_process.poll()
                    if return_code is None:  # 进程还在运行
                        has_process = True
                        process_alive = True
                    else:
                        # 进程已结束，清理状态
                        self.current_process = None
                        self.is_running = False
                        self.task_parts = []
                        self.current_task_index = 0
                except:
                    self.current_process = None
                    self.is_running = False
                    self.task_parts = []
                    self.current_task_index = 0

        # 如果标记为运行中但没有进程，则纠正状态
        if self.is_running and not process_alive:
            self.is_running = False
            self.task_parts = []
            self.current_task_index = 0

        return {
            "is_running": self.is_running,
            "current_command": self.current_command,
            "has_process": has_process,
            "process_alive": process_alive,
            "task_count": len(self.task_parts),
            "current_task_index": self.current_task_index
        }

    def execute_tasks(self, task_parts, original_command=""):
        """执行任务列表"""
        self.original_command = original_command

        # 生成轨迹ID
        traj_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]

        # 设置运行状态
        with self.process_lock:
            self.is_running = True
            self.task_parts = task_parts
            self.current_task_index = 0

        # 设置环境变量
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"

        # 基础命令
        base_cmd = f'"{SystemConfig.VENV_PYTHON}" -m droidrun run'

        def generate():
            process = None
            all_output_lines = []  # 收集所有输出，用于保存日志
            start_time = datetime.datetime.now()
            final_success = True
            step_count = 0

            try:
                # 顺序执行所有任务部分
                for i, task in enumerate(task_parts):
                    # 更新当前任务索引
                    with self.process_lock:
                        self.current_task_index = i

                    # 任务开始提示
                    if len(task_parts) > 1:
                        msg = f"data: 🔄 开始执行第{i+1}/{len(task_parts)}部分\n\n"
                        all_output_lines.append(msg)
                        yield msg
                    else:
                        msg = f"data: 🔄 开始执行任务\n\n"
                        all_output_lines.append(msg)
                        yield msg

                    # 构建完整命令
                    full_cmd = f'{base_cmd} "{task}" --provider {SystemConfig.PROVIDER} --model {SystemConfig.MODEL}'

                    # 启动进程
                    with self.process_lock:
                        process = subprocess.Popen(
                            full_cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding='utf-8',
                            errors='replace',
                            env=env,
                            cwd=SystemConfig.TRAJ_BASE_PATH,
                            bufsize=1
                        )
                        self.current_process = process

                    print(f"[启动进程] PID: {process.pid}, 命令: {full_cmd[:100]}...")

                    # 收集输出
                    task_output = []
                    while True:
                        line = process.stdout.readline()
                        if not line:
                            if process.poll() is not None:
                                break
                            continue

                        cleaned_line = line.rstrip('\n').rstrip('\r')
                        if cleaned_line:
                            sse_line = f"data: {cleaned_line}\n\n"
                            all_output_lines.append(cleaned_line)
                            yield sse_line
                            task_output.append(cleaned_line)

                            # 统计步骤数
                            if "Step " in cleaned_line:
                                step_count += 1

                    # 检查退出状态
                    return_code = process.poll()
                    print(f"[进程结束] PID: {process.pid}, 返回码: {return_code}")

                    # 如果是多部分任务，检查第一部分是否完成
                    if len(task_parts) > 1 and i == 0:
                        combined_output = "\n".join(task_output)
                        if "'完成操作'" in combined_output or "完成操作" in combined_output:
                            msg = f"data: ✅ 第一部分完成，继续第二部分...\n\n"
                            all_output_lines.append(msg)
                            yield msg
                            time.sleep(0.5)
                        else:
                            msg = f"data: ⚠️ 第一部分未明确完成，但仍继续第二部分\n\n"
                            all_output_lines.append(msg)
                            yield msg
                            time.sleep(0.5)

                    elif return_code != 0:
                        final_success = False
                        msg = f"data: ❌ 任务执行失败，返回码: {return_code}\n\n"
                        all_output_lines.append(msg)
                        yield msg
                        msg = "data: [ERROR]\n\n"
                        yield msg
                        break

                    # 如果是最后一个任务
                    if i == len(task_parts) - 1:
                        msg = f"data: ✅ 所有任务执行完成\n\n"
                        all_output_lines.append(msg)
                        yield msg
                        msg = "data: [DONE]\n\n"
                        yield msg

            except Exception as e:
                final_success = False
                print(f"[执行异常] {str(e)}")
                err_msg = f"data: 执行错误: {str(e)}\n\n"
                all_output_lines.append(err_msg)
                yield err_msg
                error_msg = "data: [ERROR]\n\n"
                yield error_msg
            finally:
                end_time = datetime.datetime.now()
                duration = (end_time - start_time).total_seconds()

                # ── 保存轨迹摘要 + 日志 ──
                try:
                    summary = {
                        "traj_id": traj_id,
                        "original_command": self.original_command,
                        "task_parts": task_parts,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "duration_seconds": round(duration, 1),
                        "success": final_success,
                        "step_count": step_count,
                        "task_count": len(task_parts),
                    }
                    save_trajectory_summary(traj_id, summary)
                    # 只保存纯日志行（去掉 SSE 格式前缀）
                    log_lines = [l for l in all_output_lines if not l.startswith("data:")]
                    save_trajectory_log(traj_id, log_lines)
                    print(f"[轨迹已保存] {traj_id} | 成功: {final_success} | 步骤: {step_count} | 耗时: {duration:.1f}s")
                except Exception as save_err:
                    print(f"[轨迹保存失败] {save_err}")

                print(f"[清理状态] 进程: {process}, 运行状态: {self.is_running}")
                # 清理状态
                with self.process_lock:
                    if self.current_process == process:
                        self.current_process = None
                    self.is_running = False
                    self.task_parts = []
                    self.current_task_index = 0

        return generate()

    def stop(self):
        """停止当前执行的命令"""
        with self.process_lock:
            if self.current_process:
                try:
                    # 检查进程是否还在运行
                    return_code = self.current_process.poll()
                    if return_code is None:  # 进程还在运行
                        try:
                            # 尝试导入psutil
                            import psutil
                            parent = psutil.Process(self.current_process.pid)

                            # 终止整个进程树
                            children = parent.children(recursive=True)
                            for child in children:
                                try:
                                    child.terminate()
                                except:
                                    pass

                            try:
                                parent.terminate()
                            except:
                                pass

                            # 等待进程结束
                            gone, alive = psutil.wait_procs([parent] + children, timeout=3)

                            # 如果还有进程存活，强制杀死
                            for p in alive:
                                try:
                                    p.kill()
                                except:
                                    pass

                            print(f"[已停止进程] PID {parent.pid}")

                        except ImportError:
                            # 如果psutil不可用，使用taskkill命令（Windows）
                            import subprocess as sp
                            sp.run(f"taskkill /F /T /PID {self.current_process.pid}",
                                   shell=True, capture_output=True)
                            print(f"[已停止进程] PID {self.current_process.pid} (使用taskkill)")

                        # 确保进程被终止
                        try:
                            self.current_process.terminate()
                            self.current_process.wait(timeout=2)
                        except:
                            try:
                                self.current_process.kill()
                            except:
                                pass

                    self.current_process = None
                    self.is_running = False
                    self.task_parts = []
                    self.current_task_index = 0

                    return {
                        "status": "success",
                        "message": "进程已停止"
                    }

                except Exception as e:
                    print(f"[停止失败] {str(e)}")
                    self.current_process = None
                    self.is_running = False
                    self.task_parts = []
                    self.current_task_index = 0

                    return {
                        "status": "error",
                        "message": f"停止失败: {str(e)}"
                    }
            else:
                self.is_running = False
                self.task_parts = []
                self.current_task_index = 0
                return {
                    "status": "info",
                    "message": "没有正在运行的进程"
                }
