#!/usr/bin/env python3
"""
启动脚本 - 前端开发服务器（修复版）
使用正确的 Node.js 路径查找和命令执行
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def find_node_installation():
    """查找系统中安装的 Node.js"""
    
    # 根据操作系统选择查找命令
    find_cmd = "which" if sys.platform != "win32" else "where"
    
    try:
        result = subprocess.run(
            [find_cmd, "node"], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            node_path = result.stdout.strip().split('\n')[0]
            node_dir = os.path.dirname(node_path)
            return node_dir
    except Exception as e:
        print(f"ℹ️ {find_cmd} 命令查找失败: {e}")
    
    return None

def setup_environment():
    """设置正确的环境变量"""
    env = os.environ.copy()
    
    # 查找 Node.js 安装目录
    node_dir = find_node_installation()
    
    if node_dir:
        # 根据操作系统选择 PATH 分隔符
        path_sep = ":" if sys.platform != "win32" else ";"
        # 将 Node.js 目录添加到 PATH 最前面
        env["PATH"] = node_dir + path_sep + env["PATH"]
    else:
        print("⚠️ 未找到 Node.js 安装，使用系统 PATH")
    
    return env

def start_dev_server(frontend_dir, env):
    """启动开发服务器"""
    print(f"\n🚀 启动前端开发服务器...")
    
    # 尝试启动开发服务器
    try:
        # Linux 下不需要 shell=True，Windows 下需要
        use_shell = sys.platform == "win32"
        process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir,
            env=env,
            shell=use_shell
        )
        # 等待进程结束
        process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断，停止前端服务...")
        if 'process' in locals():
            process.terminate()
    except Exception as e:
        print(f"❌ 开发服务器启动失败: {e}")
        return False
    
    return True

def start_frontend():
    """主启动函数"""
    
    # 检查前端目录
    frontend_dir = Path(__file__).parent / "frontend"
    if not frontend_dir.exists():
        print(f"❌ 前端目录不存在: {frontend_dir}")
        print("💡 请确保 frontend/ 目录存在")
        return False
    
    # 设置环境
    env = setup_environment()
    
    # 切换到前端目录
    original_dir = os.getcwd()
    try:
        os.chdir(frontend_dir)
        # 启动开发服务器
        return start_dev_server(frontend_dir, env)
        
    except Exception as e:
        print(f"❌ 启动过程中发生错误: {e}")
        return False
    finally:
        os.chdir(original_dir)

def start_backend():
    """启动后端服务"""
    try:
        # 确保使用新的认证后端
        use_shell = sys.platform == "win32"
        subprocess.Popen(
            ["python", "backend/main.py"],
            cwd=Path(__file__).parent,
            shell=use_shell
        )
    except Exception as e:
        print(f"❌ 后端启动失败: {e}")

if __name__ == "__main__":
    # 首先尝试启动主前端
    success = start_frontend()
    
    if not success:
        print("\n" + "=" * 50)
        print("前端启动失败")