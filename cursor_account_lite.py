#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Account Lite Manager
精简版Cursor账号备份工具 - 只备份关键的账号信息文件
"""

import os
import sys
import shutil
import json
import time
from datetime import datetime
from pathlib import Path
import argparse

class CursorAccountLite:
    def __init__(self):
        self.appdata = os.environ.get('APPDATA', '')
        self.localappdata = os.environ.get('LOCALAPPDATA', '')
        self.userprofile = os.environ.get('USERPROFILE', '')

        # 定义关键文件列表 - 只备份账号相关的核心文件
        self.critical_files = [
            # 会话和认证信息
            {
                'source': os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json'),
                'target': 'sentry/session.json',
                'description': '用户会话信息'
            },
            {
                'source': os.path.join(self.appdata, 'Cursor', 'sentry', 'scope_v3.json'),
                'target': 'sentry/scope_v3.json',
                'description': '用户权限范围'
            },
            # 全局存储配置
            {
                'source': os.path.join(self.appdata, 'Cursor', 'User', 'globalStorage', 'storage.json'),
                'target': 'User/globalStorage/storage.json',
                'description': '全局用户存储'
            },
            # 状态数据库
            {
                'source': os.path.join(self.appdata, 'Cursor', 'User', 'globalStorage', 'state.vscdb'),
                'target': 'User/globalStorage/state.vscdb',
                'description': '用户状态数据库'
            },
            {
                'source': os.path.join(self.appdata, 'Cursor', 'User', 'globalStorage', 'state.vscdb.backup'),
                'target': 'User/globalStorage/state.vscdb.backup',
                'description': '状态数据库备份'
            },
            # 网络认证数据
            {
                'source': os.path.join(self.appdata, 'Cursor', 'Network', 'Cookies'),
                'target': 'Network/Cookies',
                'description': '登录Cookie'
            },
            {
                'source': os.path.join(self.appdata, 'Cursor', 'Network', 'Trust Tokens'),
                'target': 'Network/Trust Tokens',
                'description': '信任令牌'
            },
            {
                'source': os.path.join(self.appdata, 'Cursor', 'Network', 'Network Persistent State'),
                'target': 'Network/Network Persistent State',
                'description': '网络持久状态'
            },
            # 用户设置（可选，但很小）
            {
                'source': os.path.join(self.appdata, 'Cursor', 'User', 'settings.json'),
                'target': 'User/settings.json',
                'description': '用户设置'
            },
            {
                'source': os.path.join(self.appdata, 'Cursor', 'User', 'keybindings.json'),
                'target': 'User/keybindings.json',
                'description': '快捷键配置'
            }
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
            "INFO": "ℹ️",
            "SKIP": "⏭️"
        }
        symbol = status_symbols.get(status, "ℹ️")
        print(f"  {symbol} {message}")

    def get_file_size_str(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def check_cursor_running(self):
        """检查Cursor是否正在运行，返回进程列表"""
        try:
            import psutil
            cursor_processes = []
            current_pid = os.getpid()

            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    name = proc.info['name'].lower()
                    pid = proc.info['pid']

                    # 跳过当前Python进程
                    if pid == current_pid:
                        continue

                    # 跳过Python相关进程
                    if 'python' in name:
                        continue

                    # 检查是否是Cursor进程
                    if 'cursor' in name:
                        cursor_processes.append(proc)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return cursor_processes
        except ImportError:
            # 如果没有psutil，使用tasklist命令
            try:
                import subprocess
                result = subprocess.run(['tasklist'], capture_output=True, text=True)
                if 'cursor' in result.stdout.lower():
                    return True  # 简单返回True表示有Cursor进程
            except:
                pass
        return []

    def terminate_cursor(self):
        """安全地终结Cursor进程"""
        self.print_status("检查Cursor进程...", "INFO")
        cursor_processes = self.check_cursor_running()

        if not cursor_processes:
            self.print_status("未发现Cursor进程", "INFO")
            return True

        if isinstance(cursor_processes, bool):
            # 如果是使用tasklist的结果，使用taskkill
            try:
                import subprocess
                self.print_status("使用taskkill终结Cursor进程...", "INFO")
                result = subprocess.run(['taskkill', '/f', '/im', 'cursor.exe'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    self.print_status("Cursor进程已终结", "OK")
                    time.sleep(2)  # 等待系统稳定
                    return True
                else:
                    self.print_status("终结Cursor进程失败", "ERROR")
                    return False
            except Exception as e:
                self.print_status(f"终结Cursor进程失败: {e}", "ERROR")
                return False

        # 使用psutil终结进程
        terminated_count = 0
        for proc in cursor_processes:
            try:
                proc_name = proc.info['name']
                proc_pid = proc.info['pid']

                self.print_status(f"终结进程: {proc_name} (PID: {proc_pid})", "INFO")
                proc.terminate()

                # 等待进程终结
                try:
                    proc.wait(timeout=5)
                    terminated_count += 1
                except:
                    # 如果进程没有在5秒内终结，强制杀死
                    try:
                        proc.kill()
                        terminated_count += 1
                    except:
                        pass

            except Exception as e:
                self.print_status(f"终结进程失败: {e}", "WARN")
                continue

        if terminated_count > 0:
            self.print_status(f"成功终结 {terminated_count} 个Cursor进程", "OK")
            time.sleep(2)  # 等待系统稳定
            return True
        else:
            self.print_status("未能终结任何Cursor进程", "ERROR")
            return False

    def create_backup_dir(self):
        """创建备份目录"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"cursor_lite_backup_{timestamp}"

        try:
            os.makedirs(backup_dir, exist_ok=True)
            return backup_dir
        except Exception as e:
            self.print_status(f"创建备份目录失败: {e}", "ERROR")
            return None

    def backup_file(self, source, target_dir, target_path, description):
        """备份单个文件"""
        if not os.path.exists(source):
            self.print_status(f"{description} - 文件不存在", "SKIP")
            return False, 0

        try:
            # 创建目标目录
            target_full_path = os.path.join(target_dir, target_path)
            os.makedirs(os.path.dirname(target_full_path), exist_ok=True)

            # 复制文件
            shutil.copy2(source, target_full_path)

            # 获取文件大小
            file_size = os.path.getsize(target_full_path)
            size_str = self.get_file_size_str(file_size)

            self.print_status(f"{description} - 备份成功 ({size_str})", "OK")
            return True, file_size
        except Exception as e:
            self.print_status(f"{description} - 备份失败: {e}", "ERROR")
            return False, 0

    def create_backup_info(self, backup_dir, backup_results, total_size):
        """创建备份信息文件"""
        info = {
            "backup_time": datetime.now().isoformat(),
            "computer_name": os.environ.get('COMPUTERNAME', 'Unknown'),
            "username": os.environ.get('USERNAME', 'Unknown'),
            "backup_type": "lite",
            "total_size_bytes": total_size,
            "total_size_readable": self.get_file_size_str(total_size),
            "files_backed_up": len([r for r in backup_results if r['success']]),
            "files_total": len(backup_results),
            "backup_results": backup_results
        }

        info_file = os.path.join(backup_dir, "backup_info.json")
        try:
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, indent=2, ensure_ascii=False)

            # 创建可读的markdown文件
            md_file = os.path.join(backup_dir, "backup_info.md")
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f"# Cursor账号精简备份信息\n\n")
                f.write(f"**备份时间**: {info['backup_time']}\n")
                f.write(f"**计算机**: {info['computer_name']}\n")
                f.write(f"**用户**: {info['username']}\n")
                f.write(f"**备份类型**: 精简版 (只包含关键账号文件)\n")
                f.write(f"**总大小**: {info['total_size_readable']}\n")
                f.write(f"**文件数量**: {info['files_backed_up']}/{info['files_total']}\n\n")

                f.write(f"## 备份文件列表\n\n")
                for result in backup_results:
                    status = "✅" if result['success'] else "❌"
                    size = f" ({result['size_readable']})" if result['success'] else ""
                    f.write(f"- {status} {result['description']}{size}\n")

                f.write(f"\n## 快速恢复\n\n")
                f.write(f"```bash\n")
                f.write(f"python cursor_account_lite.py restore {backup_dir}\n")
                f.write(f"```\n\n")

                f.write(f"## 手动恢复步骤\n\n")
                f.write(f"1. 关闭Cursor程序\n")
                f.write(f"2. 将备份文件复制到对应位置:\n")
                for result in backup_results:
                    if result['success']:
                        f.write(f"   - `{result['target']}` → `{result['source']}`\n")
                f.write(f"3. 启动Cursor验证登录状态\n")

        except Exception as e:
            self.print_status(f"创建备份信息失败: {e}", "ERROR")

    def backup_account(self):
        """备份Cursor账号关键数据"""
        self.print_header("Cursor账号精简备份")

        # 自动终结Cursor进程以确保完整备份
        print("🔄 准备备份，自动终结Cursor进程...")
        if not self.terminate_cursor():
            print("⚠️  警告: 无法终结Cursor进程，可能影响备份完整性")
            response = input("是否继续备份? (y/N): ").strip().lower()
            if response != 'y':
                print("备份已取消")
                return False

        print()

        # 创建备份目录
        backup_dir = self.create_backup_dir()
        if not backup_dir:
            return False

        print(f"备份目录: {backup_dir}")
        print("只备份关键的账号信息文件，预计大小: < 1MB")
        print()

        # 执行备份
        backup_results = []
        total_size = 0
        successful = 0

        for i, file_info in enumerate(self.critical_files, 1):
            print(f"[{i}/{len(self.critical_files)}] {file_info['description']}...")
            success, size = self.backup_file(
                file_info['source'],
                backup_dir,
                file_info['target'],
                file_info['description']
            )

            backup_results.append({
                'source': file_info['source'],
                'target': file_info['target'],
                'description': file_info['description'],
                'success': success,
                'size_bytes': size,
                'size_readable': self.get_file_size_str(size) if success else "0 B"
            })

            if success:
                successful += 1
                total_size += size

        # 创建备份信息
        self.create_backup_info(backup_dir, backup_results, total_size)

        # 统计结果
        print()
        self.print_header("精简备份完成")
        print(f"成功备份: {successful}/{len(self.critical_files)} 个文件")
        print(f"总大小: {self.get_file_size_str(total_size)}")
        print(f"备份位置: {os.path.abspath(backup_dir)}")

        if successful > 0:
            print(f"\n🚀 快速恢复命令:")
            print(f"python {sys.argv[0]} restore {backup_dir}")

        return successful > 0

    def restore_file(self, source, target, description):
        """恢复单个文件"""
        if not os.path.exists(source):
            self.print_status(f"{description} - 备份文件不存在", "SKIP")
            return False

        try:
            # 创建目标目录
            os.makedirs(os.path.dirname(target), exist_ok=True)

            # 复制文件
            shutil.copy2(source, target)

            file_size = os.path.getsize(target)
            size_str = self.get_file_size_str(file_size)

            self.print_status(f"{description} - 恢复成功 ({size_str})", "OK")
            return True
        except Exception as e:
            self.print_status(f"{description} - 恢复失败: {e}", "ERROR")
            return False

    def restore_account(self, backup_dir):
        """恢复Cursor账号数据"""
        self.print_header("Cursor账号精简恢复")

        if not os.path.exists(backup_dir):
            self.print_status(f"备份目录不存在: {backup_dir}", "ERROR")
            return False

        # 读取备份信息
        info_file = os.path.join(backup_dir, "backup_info.json")
        if os.path.exists(info_file):
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    backup_info = json.load(f)
                print(f"备份时间: {backup_info.get('backup_time', 'Unknown')}")
                print(f"源计算机: {backup_info.get('computer_name', 'Unknown')}")
                print(f"备份大小: {backup_info.get('total_size_readable', 'Unknown')}")
                print()
            except:
                pass

        print("⚠️  警告: 这将覆盖现有的Cursor账号数据!")
        response = input("确定要继续恢复吗? (y/N): ").strip().lower()
        if response != 'y':
            print("恢复已取消")
            return False

        print()

        # 执行恢复
        successful = 0

        for i, file_info in enumerate(self.critical_files, 1):
            print(f"[{i}/{len(self.critical_files)}] {file_info['description']}...")
            source_path = os.path.join(backup_dir, file_info['target'])
            success = self.restore_file(
                source_path,
                file_info['source'],
                file_info['description']
            )

            if success:
                successful += 1

        # 统计结果
        print()
        self.print_header("精简恢复完成")
        print(f"成功恢复: {successful}/{len(self.critical_files)} 个文件")

        if successful > 0:
            print("\n🎉 现在可以启动Cursor并检查登录状态")
            print("如果登录成功，说明账号信息已成功迁移！")

        return successful > 0

    def list_backups(self):
        """列出当前目录下的精简备份"""
        self.print_header("可用的精简备份")

        backups = []
        for item in os.listdir('.'):
            if os.path.isdir(item) and item.startswith('cursor_lite_backup_'):
                info_file = os.path.join(item, 'backup_info.json')
                if os.path.exists(info_file):
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        backups.append((item, info))
                    except:
                        backups.append((item, {}))

        if not backups:
            print("未找到任何精简备份")
            return

        for backup_dir, info in backups:
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            size = info.get('total_size_readable', 'Unknown')
            files = info.get('files_backed_up', 0)
            print(f"📁 {backup_dir}")
            print(f"   时间: {backup_time}")
            print(f"   来源: {computer}")
            print(f"   大小: {size} ({files} 个文件)")
            print()

def main():
    parser = argparse.ArgumentParser(description='Cursor账号精简管理工具')
    parser.add_argument('action', choices=['backup', 'restore', 'list'],
                       help='操作类型: backup(备份), restore(恢复), list(列出备份)')
    parser.add_argument('backup_dir', nargs='?',
                       help='恢复时指定备份目录')

    args = parser.parse_args()

    manager = CursorAccountLite()

    if args.action == 'backup':
        success = manager.backup_account()
        sys.exit(0 if success else 1)

    elif args.action == 'restore':
        if not args.backup_dir:
            print("错误: 恢复操作需要指定备份目录")
            print("用法: python cursor_account_lite.py restore <backup_dir>")
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
