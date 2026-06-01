// 全局变量
let eventSource = null;
let isRunning = false;
let currentCommand = '';
let executionStats = {
    totalTasks: 0,
    successfulTasks: 0,
    totalTime: 0,
    taskStartTime: null,
    taskEndTime: null
};

// API 基础路径
const API_BASE = '/api';

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    loadQuickCommands();
    updateStats();
    refreshTrajs();
    startClock();
    loadExecutionStats();

    // 页面卸载时关闭连接
    window.addEventListener('beforeunload', function () {
        if (eventSource) {
            eventSource.close();
        }
        if (isRunning) {
            fetch(`${API_BASE}/stop`, { method: 'POST' });
        }
    });
});

// 加载快捷指令
function loadQuickCommands() {
    const commands = [
        { icon: '⚙️', text: '打开设置', desc: '进入系统设置' },
        { icon: '💬', text: '打开微信', desc: '启动微信应用' },
        { icon: '🌤️', text: '查看天气', desc: '查看天气预报' },
        { icon: '📷', text: '拍照', desc: '使用相机拍照' },
        { icon: '📞', text: '打电话', desc: '拨打联系人电话' },
        { icon: '🎵', text: '播放音乐', desc: '播放音乐应用' },
        { icon: '⏰', text: '设置闹钟', desc: '设置新闹钟' },
        { icon: '📅', text: '查看日历', desc: '查看今日日程' }
    ];

    const container = document.getElementById('quick-commands');
    container.innerHTML = '';

    commands.forEach(cmd => {
        const btn = document.createElement('button');
        btn.className = 'btn btn-outline-primary quick-command';
        btn.innerHTML = `${cmd.icon} ${cmd.text}`;
        btn.title = cmd.desc;
        btn.onclick = () => setCommand(cmd.text);
        container.appendChild(btn);
    });
}

// 设置命令
function setCommand(cmd) {
    document.getElementById('cmdInput').value = cmd;
}

// 运行命令
function runCommand() {
    const cmd = document.getElementById('cmdInput').value.trim();
    if (!cmd) {
        showAlert('请输入任务指令', 'warning');
        return;
    }

    // 检查服务器状态
    fetch(`${API_BASE}/status`)
        .then(response => response.json())
        .then(data => {
            console.log('状态检查:', data);

            // 更准确的状态检查：只有当进程确实存在且运行时才提示
            if (data.is_running && data.process_alive) {
                if (!confirm('当前有任务正在执行，是否终止并开始新任务？')) {
                    return;
                }
                stopExecution(() => {
                    setTimeout(() => startExecution(cmd), 1000);
                });
            } else {
                // 如果状态不一致，先重置状态
                if (data.is_running && !data.process_alive) {
                    console.log('状态不一致，正在重置...');
                    fetch(`${API_BASE}/stop`, { method: 'POST' })
                        .then(() => {
                            setTimeout(() => startExecution(cmd), 500);
                        });
                } else {
                    startExecution(cmd);
                }
            }
        })
        .catch(error => {
            console.error('状态检查失败:', error);
            startExecution(cmd);
        });
}

// 开始执行
function startExecution(cmd) {
    currentCommand = cmd;
    isRunning = true;

    // 记录任务开始时间
    executionStats.taskStartTime = new Date();

    const consoleDiv = document.getElementById('console');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const runBtn = document.getElementById('run-btn');
    const runBtnText = document.getElementById('run-btn-text');

    // 添加开始日志
    addLogEntry('🚀 开始执行任务: ' + cmd, 'system');
    addLogEntry('⏳ 正在初始化 AI Agent...', 'warning');

    // 更新状态
    statusDot.className = 'status-dot running';
    statusText.textContent = '执行中';
    runBtn.className = 'btn btn-stop';
    runBtnText.innerHTML = '<i class="fas fa-stop me-2"></i>停止执行';
    runBtn.onclick = function () { stopExecution(); };
    runBtn.disabled = false;

    // 关闭之前的连接
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }

    // 添加唯一的session ID防止浏览器缓存和重连
    const sessionId = Date.now();
    eventSource = new EventSource(`${API_BASE}/execute?cmd=${encodeURIComponent(cmd)}&_=${sessionId}`);

    // 设置连接超时
    let connectionTimeout = setTimeout(() => {
        if (eventSource && eventSource.readyState === EventSource.CONNECTING) {
            addLogEntry('⚠️ 连接超时，请检查网络连接', 'warning');
        }
    }, 10000);

    eventSource.onopen = function () {
        clearTimeout(connectionTimeout);
    };

    eventSource.onmessage = function (e) {
        clearTimeout(connectionTimeout);

        if (e.data === "[DONE]" || e.data === "[ERROR]") {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }

            if (e.data === "[DONE]") {
                setTimeout(() => finishExecution(true), 100);
            } else {
                setTimeout(() => finishExecution(false), 100);
            }
            return;
        }

        processLogLine(e.data);
    };

    eventSource.onerror = function (e) {
        clearTimeout(connectionTimeout);

        if (eventSource) {
            if (eventSource.readyState === EventSource.CLOSED) {
                // 正常关闭，不处理
                return;
            }
            eventSource.close();
            eventSource = null;
        }

        // 只在连接意外中断时显示错误
        if (isRunning) {
            addLogEntry('❌ 连接中断，检查任务状态...', 'error');

            // 检查服务器端状态
            setTimeout(() => {
                fetch(`${API_BASE}/status`)
                    .then(response => response.json())
                    .then(data => {
                        if (!data.is_running) {
                            finishExecution(false);
                        }
                    })
                    .catch(() => {
                        finishExecution(false);
                    });
            }, 1000);
        }
    };
}

// 处理日志行
function processLogLine(line) {
    let type = 'info';

    if (line.includes("Step ")) {
        type = 'step-log';
    } else if (line.includes("error") || line.includes("Error") || line.includes("fail")) {
        type = 'error';
    } else if (line.includes("success") || line.includes("Success") || line.includes("完成")) {
        type = 'success';
    } else if (line.includes("thought") || line.includes("思考")) {
        type = 'thought';
    } else if (line.includes("action") || line.includes("操作")) {
        type = 'action';
    } else if (line.includes("Initializing") || line.includes("Starting")) {
        type = 'system';
    }

    addLogEntry(line, type);
}

// 添加日志条目
function addLogEntry(text, type) {
    const consoleDiv = document.getElementById('console');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = text;
    consoleDiv.appendChild(entry);
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

// 停止执行
function stopExecution(callback) {
    const runBtn = document.getElementById('run-btn');
    const runBtnText = document.getElementById('run-btn-text');

    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }

    addLogEntry('⏹️ 正在停止任务...', 'warning');

    // 更新按钮状态
    runBtn.disabled = true;
    runBtnText.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>停止中';

    // 发送停止请求
    fetch(`${API_BASE}/stop`, { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            addLogEntry('✅ ' + data.message, 'success');

            // 重置按钮状态
            setTimeout(() => {
                runBtn.className = 'btn btn-primary';
                runBtnText.innerHTML = '<i class="fas fa-play me-2"></i>开始执行';
                runBtn.onclick = runCommand;
                runBtn.disabled = false;

                isRunning = false;
                const statusDot = document.getElementById('status-dot');
                const statusText = document.getElementById('status-text');
                statusDot.className = 'status-dot';
                statusText.textContent = '就绪';

                if (callback) callback();
            }, 500);
        })
        .catch(error => {
            addLogEntry('❌ 停止失败: ' + error, 'error');

            // 重置按钮状态
            runBtn.className = 'btn btn-primary';
            runBtnText.innerHTML = '<i class="fas fa-play me-2"></i>开始执行';
            runBtn.onclick = runCommand;
            runBtn.disabled = false;

            isRunning = false;
            const statusDot = document.getElementById('status-dot');
            const statusText = document.getElementById('status-text');
            statusDot.className = 'status-dot';
            statusText.textContent = '就绪';

            if (callback) callback();
        });
}

// 完成执行
function finishExecution(success) {
    isRunning = false;

    // 记录任务结束时间并计算用时
    if (executionStats.taskStartTime) {
        executionStats.taskEndTime = new Date();
        const taskDuration = (executionStats.taskEndTime - executionStats.taskStartTime) / 1000;

        if (success) {
            addLogEntry(`✅ 任务执行完成 (用时: ${taskDuration.toFixed(1)}秒)`, 'success');
            executionStats.successfulTasks++;
            executionStats.totalTime += taskDuration;
        } else {
            addLogEntry(`❌ 任务执行失败 (用时: ${taskDuration.toFixed(1)}秒)`, 'error');
        }

        executionStats.totalTasks++;

        executionStats.taskStartTime = null;
        executionStats.taskEndTime = null;
    } else {
        if (success) {
            addLogEntry('✅ 任务执行完成', 'success');
            executionStats.successfulTasks++;
        } else {
            addLogEntry('❌ 任务执行失败', 'error');
        }
        executionStats.totalTasks++;
    }

    // 更新状态和统计
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const runBtn = document.getElementById('run-btn');
    const runBtnText = document.getElementById('run-btn-text');

    statusDot.className = 'status-dot';
    statusText.textContent = '就绪';
    runBtn.className = 'btn btn-primary';
    runBtnText.innerHTML = '<i class="fas fa-play me-2"></i>开始执行';
    runBtn.onclick = runCommand;
    runBtn.disabled = false;

    updateStats();
    refreshTrajs();
    saveExecutionStats();
}

// 更新统计信息（从后端轨迹数据获取真实统计）
function updateStats() {
    fetch(`${API_BASE}/stats`)
        .then(response => response.json())
        .then(data => {
            // 总执行任务数（有 summary.json 的真实记录）
            document.getElementById('total-tasks').textContent = data.total_tasks;
            // 成功率
            document.getElementById('success-rate').textContent = data.success_rate + '%';
            // 轨迹记录总数
            document.getElementById('traj-count').textContent = data.traj_count;
            // 平均用时（仅成功任务）
            document.getElementById('avg-time').textContent = data.avg_time + 's';
        })
        .catch(() => {
            // 请求失败时保留当前显示值，不做变动
            console.warn('统计信息加载失败');
        });
}

// 加载执行统计
function loadExecutionStats() {
    const stats = localStorage.getItem('droidrun_stats');
    if (stats) {
        const savedStats = JSON.parse(stats);
        executionStats = {
            totalTasks: savedStats.totalTasks || 0,
            successfulTasks: savedStats.successfulTasks || 0,
            totalTime: savedStats.totalTime || 0,
            taskStartTime: null,
            taskEndTime: null
        };
        updateStats();
    }
}

// 保存执行统计
function saveExecutionStats() {
    const statsToSave = {
        totalTasks: executionStats.totalTasks,
        successfulTasks: executionStats.successfulTasks,
        totalTime: executionStats.totalTime
    };
    localStorage.setItem('droidrun_stats', JSON.stringify(statsToSave));
}

// ────────────────────────────────────────
//  轨迹记录 — 增强版（Level 1）
// ────────────────────────────────────────

// 当前选中的轨迹ID
let selectedTrajId = null;

// 刷新轨迹列表（展示真实摘要信息）
function refreshTrajs() {
    fetch(`${API_BASE}/trajectories`)
        .then(response => response.json())
        .then(data => {
            const trajList = document.getElementById('traj-list');

            if (data.trajs.length === 0) {
                trajList.innerHTML = `
                    <div class="list-group-item text-muted text-center py-4">
                        <i class="fas fa-inbox fa-2x mb-2"></i><br>
                        暂无轨迹记录<br>
                        <small class="text-muted">执行任务后将自动生成</small>
                    </div>`;
                return;
            }

            trajList.innerHTML = '';

            data.trajs.forEach(traj => {
                const tid = traj.traj_id;
                const isLegacy = traj.legacy;

                if (isLegacy) {
                    // 旧版空文件夹，简单展示
                    const trajItem = document.createElement('div');
                    trajItem.className = 'list-group-item traj-item';
                    trajItem.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <small class="text-muted"><i class="far fa-folder me-1"></i>${tid}</small>
                            </div>
                            <span class="badge bg-secondary">历史</span>
                        </div>`;
                    trajItem.onclick = () => viewTrajectory(tid);
                    trajList.appendChild(trajItem);
                    return;
                }

                // 新版 — 展示摘要
                const dateStr = tid.split('_')[0];
                const formattedDate = `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
                const timeStr = tid.split('_')[1];
                const formattedTime = `${timeStr.slice(0,2)}:${timeStr.slice(2,4)}:${timeStr.slice(4,6)}`;

                const success = traj.success;
                const statusIcon = success ? '✅' : '❌';
                const statusClass = success ? 'text-success' : 'text-danger';
                const cmdPreview = (traj.original_command || '未知指令').substring(0, 18)
                    + ((traj.original_command || '').length > 18 ? '…' : '');
                const duration = traj.duration_seconds ? traj.duration_seconds + 's' : '—';
                const steps = traj.step_count || 0;
                const tasks = traj.task_count || 1;

                const trajItem = document.createElement('div');
                trajItem.className = `list-group-item traj-item ${tid === selectedTrajId ? 'active' : ''}`;
                trajItem.dataset.trajId = tid;
                trajItem.innerHTML = `
                    <div class="traj-item-header">
                        <span class="${statusClass}">${statusIcon}</span>
                        <span class="traj-cmd" title="${escapeHtml(traj.original_command || '')}">${escapeHtml(cmdPreview)}</span>
                    </div>
                    <div class="traj-item-meta">
                        <span><i class="far fa-clock"></i> ${duration}</span>
                        <span><i class="fas fa-shoe-prints"></i> ${steps}步</span>
                        ${tasks > 1 ? `<span><i class="fas fa-list"></i> ${tasks}段</span>` : ''}
                        <span class="text-muted small">${formattedDate} ${formattedTime}</span>
                    </div>`;
                trajItem.onclick = () => viewTrajectory(tid);

                trajList.appendChild(trajItem);
            });
        });
}

// 查看轨迹详情 — 加载日志到控制台
function viewTrajectory(trajId) {
    // 如果正在执行任务，不允许查看
    if (isRunning) {
        showAlert('请先停止当前执行的任务再查看轨迹', 'warning');
        return;
    }

    // 高亮选中项
    selectedTrajId = trajId;
    document.querySelectorAll('#traj-list .traj-item').forEach(el => {
        el.classList.toggle('active', el.dataset.trajId === trajId);
    });

    // 加载详情
    const consoleDiv = document.getElementById('console');
    consoleDiv.innerHTML = `
        <div class="log-entry system text-center py-3">
            <i class="fas fa-spinner fa-spin me-2"></i>加载轨迹记录中...
        </div>`;

    fetch(`${API_BASE}/trajectory/${trajId}`)
        .then(response => response.json())
        .then(data => {
            consoleDiv.innerHTML = '';

            if (data.summary) {
                const s = data.summary;
                const statusEmoji = s.success ? '✅' : '❌';
                const statusText = s.success ? '执行成功' : '执行失败';

                // 摘要头
                addLogEntry(`📋 轨迹记录: ${trajId}`, 'system');
                addLogEntry(`${statusEmoji} 状态: ${statusText} | ⏱ ${s.duration_seconds || '?'}秒 | 👣 ${s.step_count || 0}步 | 📦 ${s.task_count || 1}个任务`, 'info');
                addLogEntry(`💬 原始指令: ${s.original_command || '无'}`, 'thought');

                if (s.task_parts && s.task_parts.length > 0) {
                    addLogEntry(`✂️ 拆分为 ${s.task_parts.length} 个子任务:`, 'system');
                    s.task_parts.forEach((part, idx) => {
                        const preview = part.length > 100 ? part.substring(0, 100) + '…' : part;
                        addLogEntry(`  [${idx+1}] ${preview}`, 'action');
                    });
                }

                addLogEntry('─'.repeat(50), 'system');
            }

            // 加载日志内容
            if (data.log) {
                const lines = data.log.split('\n');
                lines.forEach(line => {
                    if (line.trim()) {
                        processLogLine(line.trim());
                    }
                });
            } else {
                addLogEntry('⚠️ 该轨迹暂无详细日志记录', 'warning');
            }
        })
        .catch(err => {
            consoleDiv.innerHTML = '';
            addLogEntry(`❌ 加载轨迹失败: ${err.message}`, 'error');
        });

    // 滚动到控制台顶部
    consoleDiv.scrollTop = 0;
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ────────────────────────────────────────

// 打开轨迹文件夹
function openTrajFolder() {
    window.open('file:///C:/Users/32765/trajectories', '_blank');
}

// 清空控制台
function clearConsole() {
    if (isRunning) {
        alert('请先停止当前执行的任务');
        return;
    }
    selectedTrajId = null;
    document.querySelectorAll('#traj-list .traj-item').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById('console').innerHTML = `
        <div class="log-entry system">
            <i class="fas fa-check-circle me-2 text-success"></i>
            控制台已清空
        </div>`;
}

// 导出日志
function exportLogs() {
    const consoleDiv = document.getElementById('console');
    const logs = consoleDiv.innerText;
    const blob = new Blob([logs], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `droidrun-logs-${new Date().toISOString().slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 显示警告
function showAlert(message, type = 'info') {
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alert.style.top = '20px';
    alert.style.right = '20px';
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}

// 时钟
function startClock() {
    function updateClock() {
        const now = new Date();
        document.getElementById('current-time').textContent =
            now.toLocaleTimeString('zh-CN', { hour12: false });
    }
    updateClock();
    setInterval(updateClock, 1000);
}
