#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Account Manager
一个用于备份和恢复Cursor账号数据的Python工具
"""

import os
import sys
import shutil
import json
import time
from datetime import datetime
from pathlib import Path
import argparse

class CursorAccountManager:
    def __init__(self):
        self.appdata = os.environ.get('APPDATA', '')
        self.localappdata = os.environ.get('LOCALAPPDATA', '')
        self.userprofile = os.environ.get('USERPROFILE', '')
        
        # 定义需要备份的路径
        self.backup_paths = {
            'User': os.path.join(self.appdata, 'Cursor', 'User'),
            'Network': os.path.join(self.appdata, 'Cursor', 'Network'),
            'Session Storage': os.path.join(self.appdata, 'Cursor', 'Session Storage'),
            'sentry': os.path.join(self.appdata, 'Cursor', 'sentry'),
            'cursor-updater': os.path.join(self.localappdata, 'cursor-updater'),
            '.cursor': os.path.join(self.userprofile, '.cursor')
        }
        
        # 关键文件列表
        self.critical_files = [
            'session.json',
            'scope_v3.json', 
            'storage.json',
            'state.vscdb',
            'state.vscdb.backup'
        ]

    def print_header(self, title):
        """打印标题"""
        print("=" * 50)
        print(f"    {title}")
        print("=" * 50)
        print()

    def print_status(self, message, status="INFO"):
        """打印状态信息"""
        status_symbols = {
            "OK": "✅",
            "ERROR": "❌", 
            "WARN": "⚠️",
            "INFO": "ℹ️"
        }
        symbol = status_symbols.get(status, "ℹ️")
        print(f"  {symbol} {message}")

    def check_cursor_running(self):
        """检查Cursor是否正在运行"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                if 'cursor' in proc.info['name'].lower():
                    return True
        except ImportError:
            # 如果没有psutil，使用tasklist命令
            try:
                import subprocess
                result = subprocess.run(['tasklist'], capture_output=True, text=True)
                return 'cursor' in result.stdout.lower()
            except:
                pass
        return False

    def create_backup_dir(self):
        """创建备份目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"cursor_account_backup_{timestamp}"
        
        try:
            os.makedirs(backup_dir, exist_ok=True)
            return backup_dir
        except Exception as e:
            self.print_status(f"创建备份目录失败: {e}", "ERROR")
            return None

    def backup_directory(self, src, dst, name):
        """备份目录"""
        if not os.path.exists(src):
            self.print_status(f"{name} 目录不存在: {src}", "WARN")
            return False
            
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            
            # 计算文件数量
            file_count = sum([len(files) for r, d, files in os.walk(dst)])
            self.print_status(f"{name} 备份成功 ({file_count} 个文件)", "OK")
            return True
        except Exception as e:
            self.print_status(f"{name} 备份失败: {e}", "ERROR")
            return False

    def create_backup_info(self, backup_dir, backup_results):
        """创建备份信息文件"""
        info = {
            "backup_time": datetime.now().isoformat(),
            "computer_name": os.environ.get('COMPUTERNAME', 'Unknown'),
            "username": os.environ.get('USERNAME', 'Unknown'),
            "backup_paths": self.backup_paths,
            "backup_results": backup_results,
            "critical_files": self.critical_files
        }
        
        info_file = os.path.join(backup_dir, "backup_info.json")
        try:
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)
            
            # 创建可读的markdown文件
            md_file = os.path.join(backup_dir, "backup_info.md")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# Cursor账号备份信息\n\n")
                f.write(f"**备份时间**: {info['backup_time']}\n")
                f.write(f"**计算机**: {info['computer_name']}\n")
                f.write(f"**用户**: {info['username']}\n\n")
                f.write(f"## 备份结果\n\n")
                for name, result in backup_results.items():
                    status = "✅ 成功" if result else "❌ 失败"
                    f.write(f"- {name}: {status}\n")
                f.write(f"\n## 恢复说明\n\n")
                f.write(f"1. 在目标机器上安装相同版本的Cursor\n")
                f.write(f"2. 关闭Cursor程序\n")
                f.write(f"3. 运行: `python cursor_account_manager.py restore {backup_dir}`\n")
                f.write(f"4. 启动Cursor验证登录状态\n")
                
        except Exception as e:
            self.print_status(f"创建备份信息失败: {e}", "ERROR")

    def backup_account(self):
        """备份Cursor账号数据"""
        self.print_header("Cursor账号数据备份")
        
        # 检查Cursor是否在运行
        if self.check_cursor_running():
            self.print_status("检测到Cursor正在运行，建议先关闭Cursor", "WARN")
            response = input("是否继续备份? (y/N): ").strip().lower()
            if response != 'y':
                print("备份已取消")
                return False
        
        # 创建备份目录
        backup_dir = self.create_backup_dir()
        if not backup_dir:
            return False
            
        print(f"备份目录: {backup_dir}")
        print()
        
        # 执行备份
        backup_results = {}
        total_paths = len(self.backup_paths)
        
        for i, (name, src_path) in enumerate(self.backup_paths.items(), 1):
            print(f"[{i}/{total_paths}] 备份 {name}...")
            dst_path = os.path.join(backup_dir, name)
            result = self.backup_directory(src_path, dst_path, name)
            backup_results[name] = result
        
        # 创建备份信息
        self.create_backup_info(backup_dir, backup_results)
        
        # 统计结果
        successful = sum(backup_results.values())
        print()
        self.print_header("备份完成")
        print(f"成功备份: {successful}/{total_paths} 个目录")
        print(f"备份位置: {os.path.abspath(backup_dir)}")
        
        if successful > 0:
            print("\n恢复方法:")
            print(f"python {sys.argv[0]} restore {backup_dir}")
        
        return successful > 0

    def restore_directory(self, src, dst, name):
        """恢复目录"""
        if not os.path.exists(src):
            self.print_status(f"{name} 备份不存在: {src}", "WARN")
            return False
            
        try:
            # 创建目标目录的父目录
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            
            # 如果目标目录存在，先删除
            if os.path.exists(dst):
                shutil.rmtree(dst)
                
            shutil.copytree(src, dst)
            
            # 计算文件数量
            file_count = sum([len(files) for r, d, files in os.walk(dst)])
            self.print_status(f"{name} 恢复成功 ({file_count} 个文件)", "OK")
            return True
        except Exception as e:
            self.print_status(f"{name} 恢复失败: {e}", "ERROR")
            return False

    def restore_account(self, backup_dir):
        """恢复Cursor账号数据"""
        self.print_header("Cursor账号数据恢复")
        
        if not os.path.exists(backup_dir):
            self.print_status(f"备份目录不存在: {backup_dir}", "ERROR")
            return False
        
        # 检查Cursor是否在运行
        if self.check_cursor_running():
            self.print_status("检测到Cursor正在运行，必须先关闭Cursor!", "ERROR")
            return False
        
        # 读取备份信息
        info_file = os.path.join(backup_dir, "backup_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                print(f"备份时间: {backup_info.get('backup_time', 'Unknown')}")
                print(f"源计算机: {backup_info.get('computer_name', 'Unknown')}")
                print()
            except:
                pass
        
        print("⚠️  警告: 这将覆盖现有的Cursor数据!")
        response = input("确定要继续恢复吗? (y/N): ").strip().lower()
        if response != 'y':
            print("恢复已取消")
            return False
        
        print()
        
        # 执行恢复
        restore_results = {}
        available_backups = []
        
        # 检查哪些备份可用
        for name in self.backup_paths.keys():
            backup_path = os.path.join(backup_dir, name)
            if os.path.exists(backup_path):
                available_backups.append((name, backup_path))
        
        total_paths = len(available_backups)
        
        for i, (name, backup_path) in enumerate(available_backups, 1):
            print(f"[{i}/{total_paths}] 恢复 {name}...")
            dst_path = self.backup_paths[name]
            result = self.restore_directory(backup_path, dst_path, name)
            restore_results[name] = result
        
        # 统计结果
        successful = sum(restore_results.values())
        print()
        self.print_header("恢复完成")
        print(f"成功恢复: {successful}/{total_paths} 个目录")
        
        if successful > 0:
            print("\n现在可以启动Cursor并检查登录状态")
        
        return successful > 0

    def list_backups(self):
        """列出当前目录下的备份"""
        self.print_header("可用的备份")
        
        backups = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and item.startswith('cursor_account_backup_'):
                info_file = os.path.join(item, 'backup_info.json')
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        backups.append((item, info))
                    except:
                        backups.append((item, {}))
        
        if not backups:
            print("未找到任何备份")
            return
        
        for backup_dir, info in backups:
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            print(f"📁 {backup_dir}")
            print(f"   时间: {backup_time}")
            print(f"   来源: {computer}")
            print()

def main():
    parser = argparse.ArgumentParser(description='Cursor账号管理工具')
    parser.add_argument('action', choices=['backup', 'restore', 'list'], 
                       help='操作类型: backup(备份), restore(恢复), list(列出备份)')
    parser.add_argument('backup_dir', nargs='?', 
                       help='恢复时指定备份目录')
    
    args = parser.parse_args()
    
    manager = CursorAccountManager()
    
    if args.action == 'backup':
        success = manager.backup_account()
        sys.exit(0 if success else 1)
        
    elif args.action == 'restore':
        if not args.backup_dir:
            print("错误: 恢复操作需要指定备份目录")
            print("用法: python cursor_account_manager.py restore <backup_dir>")
            sys.exit(1)
        success = manager.restore_account(args.backup_dir)
        sys.exit(0 if success else 1)
        
    elif args.action == 'list':
        manager.list_backups()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)
