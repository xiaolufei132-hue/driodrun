from flask import Blueprint, render_template, jsonify, request, Response
import datetime
import os
from config import SystemConfig
from splitter import ImprovedTaskSplitter
from utils.process_manager import ProcessManager
from utils.file_utils import (
    get_trajectories_list,
    ensure_trajectory_dir,
    get_all_trajectory_summaries,
    load_trajectory_summary,
    load_trajectory_log,
)

# 创建蓝图
main_blueprint = Blueprint('main', __name__)
api_blueprint = Blueprint('api', __name__)

# 全局进程管理器
process_manager = ProcessManager()


@main_blueprint.route('/')
def index():
    """主页面"""
    ensure_trajectory_dir()
    dirs = get_trajectories_list()

    current_time = datetime.datetime.now().strftime("%H:%M:%S")

    return render_template(
        'index.html',
        trajs=sorted(dirs, reverse=True)[:15],
        current_time=current_time,
        config=SystemConfig
    )


@api_blueprint.route('/trajectories')
def get_trajectories():
    """获取轨迹列表（含摘要信息）"""
    summaries = get_all_trajectory_summaries()
    return jsonify({"trajs": summaries[:20]})


@api_blueprint.route('/trajectory/<traj_id>')
def get_trajectory_detail(traj_id):
    """获取单条轨迹的详细信息和日志"""
    summary = load_trajectory_summary(traj_id)
    log = load_trajectory_log(traj_id)
    return jsonify({
        "traj_id": traj_id,
        "summary": summary,
        "log": log,
    })


@api_blueprint.route('/optimize-prompt')
def optimize_prompt():
    """优化用户输入的提示词"""
    cmd_text = request.args.get('cmd', '')
    if not cmd_text:
        return jsonify({"optimized": "请输入指令"})

    # 使用简化拆分器
    splitter = ImprovedTaskSplitter()
    first_part, second_part, should_split = splitter.split_if_needed(cmd_text)

    # 构建优化后的显示文本
    if should_split and second_part:
        # 如果有拆分，显示两部分
        optimized = f"第一部分：{first_part}\n\n第二部分：{second_part}"
    else:
        # 没有拆分，只显示第一部分
        optimized = first_part

    return jsonify({"optimized": optimized})


@api_blueprint.route('/status')
def get_status():
    """获取当前执行状态"""
    return jsonify(process_manager.get_status())


@api_blueprint.route('/execute')
def execute():
    """执行命令"""
    cmd_text = request.args.get('cmd')

    if not cmd_text:
        def error_generator():
            yield "data: 错误：未提供指令\n\n"
            yield "data: [ERROR]\n\n"
        return Response(error_generator(), mimetype='text/event-stream')

    # 检查是否已经在执行
    if process_manager.is_running and process_manager.has_process:
        def already_running_generator():
            yield "data: 错误：已有任务正在执行，请先停止\n\n"
            yield "data: [ERROR]\n\n"
        return Response(already_running_generator(), mimetype='text/event-stream')

    # 使用简化拆分器
    splitter = ImprovedTaskSplitter()
    first_part, second_part, should_split = splitter.split_if_needed(cmd_text)

    # 构建任务列表 - 使用清洗后的任务
    task_parts_local = [splitter.sanitize_for_python(first_part)]
    if second_part:
        task_parts_local.append(splitter.sanitize_for_python(second_part))

    print(f"[原始指令] {cmd_text}")
    print(f"[任务拆分] 需要拆分: {should_split}, 任务数: {len(task_parts_local)}")
    for i, task in enumerate(task_parts_local):
        print(f"  任务{i+1}: {task[:80]}...")

    # 启动执行（传入原始指令用于轨迹记录）
    return Response(
        process_manager.execute_tasks(task_parts_local, original_command=cmd_text),
        mimetype='text/event-stream'
    )


@api_blueprint.route('/stop', methods=['POST'])
def stop_execution():
    """停止当前执行的命令"""
    return jsonify(process_manager.stop())


@api_blueprint.route('/stats')
def get_stats():
    """获取执行统计（基于真实轨迹数据）"""
    summaries = get_all_trajectory_summaries()

    # 只统计有 summary.json 的真实记录
    real = [s for s in summaries if not s.get("legacy")]
    total = len(real)
    successful = len([s for s in real if s.get("success")])

    # 平均用时：只统计成功的任务
    success_durations = [
        s.get("duration_seconds", 0)
        for s in real
        if s.get("success") and s.get("duration_seconds")
    ]
    avg_time = round(sum(success_durations) / len(success_durations), 1) if success_durations else 0

    return jsonify({
        "total_tasks": total,
        "successful_tasks": successful,
        "success_rate": round((successful / total * 100) if total > 0 else 0),
        "avg_time": avg_time,
        "traj_count": len(summaries),  # 含 legacy 的总轨迹数
    })
