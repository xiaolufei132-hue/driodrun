import re

# === 简化版提示词优化器 ===
class SimplePromptOptimizer:
    """简化版提示词优化器，只做最基础的优化"""
    
    @staticmethod
    def enhance_prompt(user_input):
        """基础优化：添加分步骤执行要求"""
        if not user_input.endswith("。"):
            user_input += "。"
        return user_input + "请分步骤执行，每一步都要确认操作成功。"

# === 改进版任务拆分器 ===
class ImprovedTaskSplitter:
    """改进版任务拆分器，记录所有识别词位置并选择最靠前的"""
    
    # 用于识别第二部分开始的动词
    SECOND_PART_VERBS = [
        "用", "给", "为", "向","帮","把",
        "查看", "检查", "浏览", "阅读",
        "设置", "配置", "调整", "修改", "更改", "设定",
        "发送", "分享", "转发", "发布", "传送",
        "点击", "按下", "触摸", "选择", "勾选", "单击",
        "搜索", "查找", "查询", "寻找",
        "添加", "创建", "新建", "编辑", "删除", "移除",
        "播放", "暂停", "停止", "继续", "录制",
        "下载", "上传", "安装", "卸载", "更新",
        "连接", "断开", "配对", "匹配",
        "清理", "清除", "优化", "整理",
        "测试", "检查", "验证", "确认",
        "回复", "评论", "点赞", "收藏",
        "购买", "支付", "下单", "订购","买",
        "导航", "定位", "规划",
    ]
    
    @classmethod
    def split_if_needed(cls, user_input):
        """
        改进方法：记录每个识别词出现的位置，选择最靠前的合适位置
        返回: (第一部分, 第二部分或None, 是否需要拆分)
        """
        # 1. 记录所有识别词出现的位置
        best_pos = -1
        best_verb = ""
        
        for verb in cls.SECOND_PART_VERBS:
            if verb in user_input:
                pos = user_input.index(verb)
                
                # 记录规则：位置 > 3，且比当前最佳位置更靠前
                if pos > 3:
                    if best_pos == -1 or pos < best_pos:
                        best_pos = pos
                        best_verb = verb
        
        # 2. 如果没有找到合适的拆分点
        if best_pos == -1:
            first_part_optimized = f"浏览所有页面和应用夹层找到并{user_input},完成后请返回：完成操作"
            return first_part_optimized, None, False
        
        # 3. 基于最佳位置进行拆分
        first_part = user_input[:best_pos].strip()
        second_part = user_input[best_pos:].strip()
        
        # 4. 清理第一部分末尾可能的分隔符
        for char in ["，", ",", "。", "、", "然后", "接着", "并"]:
            if first_part.endswith(char):
                first_part = first_part[:-len(char)].strip()
        
        # 5. 验证拆分是否合理
        if len(first_part) >= 4:
            # 优化第一部分：添加搜索优化和完成标志
            first_part_optimized = f"浏览所有页面和应用夹层找到并{first_part},完成后请返回:完成操作"
            # 第二部分：只加完成标志
            second_part_with_flag = f"在该软件里{second_part},完成后请返回:任务完成"
            
            # 调试信息
            print(f"[拆分器] 找到最佳拆分点:")
            print(f"  位置: {best_pos}")
            print(f"  动词: '{best_verb}'")
            print(f"  第一部分: {first_part}")
            print(f"  第二部分: {second_part}")
            
            return first_part_optimized, second_part_with_flag, True
        
        # 6. 如果拆分不合理，则不拆分
        first_part_optimized = f"浏览所有页面和应用夹层找到并{user_input},完成后请返回：'完成操作'"
        return first_part_optimized, None, False
    
    @staticmethod
    def sanitize_for_python(task):
        """为Python执行清洗任务文本"""
        import re
        
        # 替换所有中文标点为英文标点
        chinese_punctuation = {
            '。': '.', '，': ',', '：': ':', '；': ';',
            '？': '?', '！': '!', '（': '(', '）': ')',
            '【': '[', '】': ']', '《': '<', '》': '>',
            '、': ',', '；': ';', '：': ':', '「': '"',
            '」': '"', '『': '"', '』': '"'
        }
        
        for cn, en in chinese_punctuation.items():
            task = task.replace(cn, en)
        
        # 添加AI指令：只生成纯英文Python代码
        if not task.endswith('.'):
            task += '.'
        
        task += " IMPORTANT: Output ONLY Python code with English characters and punctuation. No Chinese text."
        
        return task