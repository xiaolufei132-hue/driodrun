import os
import json
from config import SystemConfig


def ensure_trajectory_dir():
    """确保轨迹目录存在"""
    if not os.path.exists(SystemConfig.TRAJ_BASE_PATH):
        os.makedirs(SystemConfig.TRAJ_BASE_PATH)


def get_trajectories_list():
    """获取轨迹目录列表（只返回有内容的目录）"""
    ensure_trajectory_dir()
    dirs = []
    for d in os.listdir(SystemConfig.TRAJ_BASE_PATH):
        traj_dir = os.path.join(SystemConfig.TRAJ_BASE_PATH, d)
        if not os.path.isdir(traj_dir):
            continue
        # 跳过空目录 — 只保留有文件的轨迹
        if _count_files(traj_dir) == 0:
            continue
        dirs.append(d)
    return dirs


def _count_files(directory):
    """递归统计目录下所有文件数量"""
    count = 0
    try:
        for root, dirs, files in os.walk(directory):
            count += len(files)
    except Exception:
        pass
    return count


def save_trajectory_summary(traj_id, summary_data):
    """保存轨迹摘要到 JSON 文件"""
    ensure_trajectory_dir()
    traj_dir = os.path.join(SystemConfig.TRAJ_BASE_PATH, traj_id)
    if not os.path.exists(traj_dir):
        os.makedirs(traj_dir)

    summary_path = os.path.join(traj_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    return summary_path


def save_trajectory_log(traj_id, log_lines):
    """保存完整执行日志"""
    ensure_trajectory_dir()
    traj_dir = os.path.join(SystemConfig.TRAJ_BASE_PATH, traj_id)
    if not os.path.exists(traj_dir):
        os.makedirs(traj_dir)

    log_path = os.path.join(traj_dir, "log.txt")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n".join(log_lines))
    return log_path


def load_trajectory_summary(traj_id):
    """读取单条轨迹的摘要"""
    summary_path = os.path.join(SystemConfig.TRAJ_BASE_PATH, traj_id, "summary.json")
    if not os.path.exists(summary_path):
        return None
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_trajectory_log(traj_id):
    """读取单条轨迹的完整日志"""
    log_path = os.path.join(SystemConfig.TRAJ_BASE_PATH, traj_id, "log.txt")
    if not os.path.exists(log_path):
        return ""
    with open(log_path, "r", encoding="utf-8") as f:
        return f.read()


def get_all_trajectory_summaries():
    """获取所有轨迹的摘要信息列表（按时间倒序，跳过空目录）"""
    ensure_trajectory_dir()
    results = []
    for d in sorted(os.listdir(SystemConfig.TRAJ_BASE_PATH), reverse=True):
        traj_dir = os.path.join(SystemConfig.TRAJ_BASE_PATH, d)
        if not os.path.isdir(traj_dir):
            continue
        if _count_files(traj_dir) == 0:
            # 跳过空目录（droidrun 残骸或未完成的轨迹）
            continue
        summary = load_trajectory_summary(d)
        if summary:
            summary["traj_id"] = d
            results.append(summary)
        else:
            results.append({"traj_id": d, "legacy": True})
    return results
