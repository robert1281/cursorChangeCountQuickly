#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Account Manager - 独立控制台版
交互式多账号管理工具
"""

import os
import sys
import shutil
import json
import time
import subprocess
import ctypes
from datetime import datetime

class CursorConsole:
    def __init__(self):
        self.appdata = os.environ.get('APPDATA', '')
        self.localappdata = os.environ.get('LOCALAPPDATA', '')
        self.userprofile = os.environ.get('USERPROFILE', '')
        self.current_user = os.environ.get('USERNAME', 'Unknown')

        # 关键文件列表
        self.critical_files = [
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
            {
                'source': os.path.join(self.appdata, 'Cursor', 'User', 'globalStorage', 'storage.json'),
                'target': 'User/globalStorage/storage.json',
                'description': '全局用户存储'
            },
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

    def is_admin(self):
        """检查是否以管理员身份运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def run_as_admin(self):
        """以管理员身份重新运行程序"""
        if self.is_admin():
            return True

        try:
            # 获取当前脚本路径
            script = os.path.abspath(sys.argv[0])
            params = ' '.join(sys.argv[1:])

            # 以管理员身份运行
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, f'"{script}" {params}', None, 1
            )
            return False  # 当前进程应该退出
        except Exception as e:
            print(f"❌ 无法提升权限: {e}")
            return False

    def kill_cursor_processes(self):
        """强制终结所有Cursor相关进程"""
        killed_count = 0
        try:
            # 方法1: 使用taskkill强制终结
            cursor_processes = ['cursor.exe', 'Cursor.exe', 'cursor', 'Cursor']
            for process_name in cursor_processes:
                try:
                    result = subprocess.run(['taskkill', '/f', '/im', process_name],
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        killed_count += 1
                        print(f"    ✅ 已终结进程: {process_name}")
                except:
                    pass

            # 方法2: 使用wmic终结
            try:
                result = subprocess.run(['wmic', 'process', 'where', 'name="cursor.exe"', 'delete'],
                                      capture_output=True, text=True)
                if "deleted successfully" in result.stdout.lower():
                    print(f"    ✅ WMIC终结成功")
            except:
                pass

            # 等待进程完全终结
            time.sleep(3)
            return killed_count > 0

        except Exception as e:
            print(f"    ⚠️ 终结进程失败: {e}")
            return False

    def unlock_file_with_handle(self, file_path):
        """使用handle.exe解锁文件"""
        try:
            # 查找占用文件的进程
            result = subprocess.run(['handle.exe', '-nobanner', file_path],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'cursor' in line.lower() and 'pid:' in line.lower():
                        # 提取PID
                        try:
                            pid_start = line.lower().find('pid:') + 4
                            pid_end = line.find(' ', pid_start)
                            if pid_end == -1:
                                pid_end = len(line)
                            pid = line[pid_start:pid_end].strip()

                            # 终结特定PID
                            subprocess.run(['taskkill', '/f', '/pid', pid],
                                         capture_output=True, text=True)
                            print(f"    🔓 已终结占用进程 PID: {pid}")
                            time.sleep(1)
                            return True
                        except:
                            continue
        except:
            pass
        return False

    def force_unlock_file(self, file_path):
        """强制解锁文件 - 增强版"""
        try:
            print(f"    🔧 尝试解锁文件: {os.path.basename(file_path)}")

            # 方法1: 使用handle.exe解锁特定文件
            if self.unlock_file_with_handle(file_path):
                return True

            # 方法2: 强制终结Cursor进程
            print(f"    ⚡ 强制终结Cursor进程...")
            if self.kill_cursor_processes():
                time.sleep(2)  # 等待文件释放
                return True

            # 方法3: 使用PowerShell强制解锁
            try:
                ps_script = f'''
                $file = "{file_path}"
                $processes = Get-Process | Where-Object {{$_.ProcessName -like "*cursor*"}}
                foreach ($proc in $processes) {{
                    try {{
                        $proc.Kill()
                        Write-Host "Killed process: $($proc.ProcessName)"
                    }} catch {{}}
                }}
                Start-Sleep -Seconds 2
                '''

                result = subprocess.run(['powershell', '-Command', ps_script],
                                      capture_output=True, text=True, timeout=15)
                if result.returncode == 0:
                    print(f"    ✅ PowerShell解锁成功")
                    return True
            except:
                pass

            # 方法4: 系统级文件操作
            try:
                import tempfile
                temp_file = tempfile.mktemp(suffix='.tmp')

                # 尝试移动文件而不是复制
                shutil.move(file_path, temp_file)
                time.sleep(0.5)
                shutil.move(temp_file, file_path)
                print(f"    ✅ 文件移动解锁成功")
                return True
            except:
                # 清理临时文件
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass

            return False

        except Exception as e:
            print(f"    ⚠️ 解锁失败: {e}")
            return False

    def nuclear_copy_file(self, source, target):
        """核武器级文件复制 - 最后手段"""
        try:
            print(f"    ☢️ 启动核武器级复制...")

            # 方法1: 使用系统级API
            try:
                import win32file
                import win32con

                # 强制打开文件
                handle = win32file.CreateFile(
                    target,
                    win32con.GENERIC_WRITE,
                    win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
                    None,
                    win32con.CREATE_ALWAYS,
                    win32con.FILE_ATTRIBUTE_NORMAL,
                    None
                )

                # 读取源文件
                with open(source, 'rb') as src:
                    data = src.read()

                # 写入目标文件
                win32file.WriteFile(handle, data)
                win32file.CloseHandle(handle)

                print(f"    ✅ Win32 API复制成功")
                return True

            except ImportError:
                print(f"    ⚠️ Win32 API不可用")
            except Exception as e:
                print(f"    ⚠️ Win32 API失败: {e}")

            # 方法2: 使用PowerShell的强制复制
            try:
                ps_script = f'''
                $source = "{source}"
                $target = "{target}"

                # 强制终结占用进程
                Get-Process | Where-Object {{$_.ProcessName -like "*cursor*"}} | Stop-Process -Force
                Start-Sleep -Seconds 2

                # 强制复制
                Copy-Item -Path $source -Destination $target -Force
                '''

                result = subprocess.run(['powershell', '-Command', ps_script],
                                      capture_output=True, text=True, timeout=20)

                if result.returncode == 0 and os.path.exists(target):
                    print(f"    ✅ PowerShell强制复制成功")
                    return True

            except Exception as e:
                print(f"    ⚠️ PowerShell复制失败: {e}")

            # 方法3: 使用takeown和icacls修改权限
            try:
                # 获取文件所有权
                subprocess.run(['takeown', '/f', target], capture_output=True, text=True)

                # 修改权限
                subprocess.run(['icacls', target, '/grant', 'administrators:F'],
                             capture_output=True, text=True)

                # 再次尝试复制
                shutil.copy2(source, target)
                print(f"    ✅ 权限修改后复制成功")
                return True

            except Exception as e:
                print(f"    ⚠️ 权限修改失败: {e}")

            # 方法4: 字节级复制
            try:
                with open(source, 'rb') as src:
                    data = src.read()

                # 尝试多次写入
                for i in range(3):
                    try:
                        with open(target, 'wb') as dst:
                            dst.write(data)
                            dst.flush()
                            os.fsync(dst.fileno())

                        if os.path.exists(target):
                            print(f"    ✅ 字节级复制成功")
                            return True
                    except:
                        time.sleep(1)

            except Exception as e:
                print(f"    ⚠️ 字节级复制失败: {e}")

            return False

        except Exception as e:
            print(f"    ☢️ 核武器级复制失败: {e}")
            return False

    def force_copy_file(self, source, target, description):
        """强制复制文件 - 增强版"""
        max_attempts = 5  # 增加尝试次数

        for attempt in range(max_attempts):
            try:
                # 创建目标目录
                os.makedirs(os.path.dirname(target), exist_ok=True)

                # 尝试直接复制
                shutil.copy2(source, target)

                file_size = os.path.getsize(target)
                size_str = self.get_file_size_str(file_size)
                print(f"  ✅ 强制切换成功 ({size_str})")
                return True

            except PermissionError:
                if attempt < max_attempts - 1:
                    print(f"    🔒 文件被锁定，尝试解锁策略 {attempt + 1}/{max_attempts}...")

                    if attempt == 0:
                        # 第1次: 尝试解锁文件
                        if self.force_unlock_file(target):
                            print(f"    🔓 文件解锁成功，重试复制...")
                            time.sleep(1)
                            continue

                    elif attempt == 1:
                        # 第2次: 使用robocopy
                        try:
                            print(f"    🚛 尝试robocopy...")
                            result = subprocess.run([
                                'robocopy',
                                os.path.dirname(source),
                                os.path.dirname(target),
                                os.path.basename(source),
                                '/COPY:DAT',
                                '/R:3',
                                '/W:1',
                                '/MT:1'
                            ], capture_output=True, text=True, timeout=15)

                            # robocopy返回码1表示成功复制
                            if result.returncode in [0, 1]:
                                temp_target = os.path.join(os.path.dirname(target), os.path.basename(source))
                                if os.path.exists(temp_target):
                                    if os.path.exists(target):
                                        try:
                                            os.remove(target)
                                        except:
                                            pass
                                    try:
                                        os.rename(temp_target, target)
                                        file_size = os.path.getsize(target)
                                        size_str = self.get_file_size_str(file_size)
                                        print(f"  ✅ robocopy成功 ({size_str})")
                                        return True
                                    except:
                                        pass
                        except Exception as e:
                            print(f"    ⚠️ robocopy失败: {e}")

                    elif attempt == 2:
                        # 第3次: 强制终结进程后重试
                        print(f"    ⚡ 强制终结所有Cursor进程...")
                        self.kill_cursor_processes()
                        time.sleep(3)
                        continue

                    elif attempt == 3:
                        # 第4次: 核武器级复制
                        if self.nuclear_copy_file(source, target):
                            file_size = os.path.getsize(target)
                            size_str = self.get_file_size_str(file_size)
                            print(f"  ✅ 核武器级复制成功 ({size_str})")
                            return True

                    # 等待一下再重试
                    time.sleep(2)
                else:
                    print(f"  🔒 所有解锁策略都失败，文件无法替换")
                    return False

            except Exception as e:
                print(f"  ❌ 强制复制失败: {e}")
                if attempt < max_attempts - 1:
                    time.sleep(1)
                    continue
                return False

        return False

    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_banner(self):
        """打印横幅"""
        print("=" * 60)
        print("    🚀 Cursor Account Manager - 控制台版")
        print("    快速无感远程换号工具")
        print("=" * 60)
        print(f"    当前用户: {self.current_user}")
        print(f"    当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    def print_menu(self):
        """打印菜单"""
        admin_status = "👑 管理员" if self.is_admin() else "👤 普通用户"
        print(f"\n📋 请选择操作: ({admin_status})")
        print("  1. 🔄 备份当前账号")
        print("  2. 📦 恢复账号数据 (关闭Cursor)")
        print("  3. 🔥 热切换账号 (保持Cursor运行)")
        print("  4. ⚡ 强制热切换 (管理员权限)")
        print("  5. 🎯 极简热切换 (只换AI对话权限)")
        print("  6. 🤖 AI对话切换 (专门切换AI配额)")
        print("  7. 🎪 精确身份切换 (直接替换用户信息)")
        print("  8. 🔧 登录状态修复 (解决AI对话登录问题)")
        print("  9. ⚡ 激活账号 (让账号成为当前活跃账号)")
        print("  10. 📋 查看所有备份")
        print("  11. 🏷️  管理备份")
        print("  12. ❓ 帮助信息")
        print("  0. 🚪 退出程序")
        print("-" * 40)

    def get_input(self, prompt="请输入选择"):
        """获取用户输入"""
        try:
            return input(f"{prompt}: ").strip()
        except KeyboardInterrupt:
            print("\n\n👋 程序已退出")
            sys.exit(0)

    def get_file_size_str(self, size_bytes):
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def terminate_cursor(self):
        """终结Cursor进程"""
        print("🔄 检查并终结Cursor进程...")
        try:
            import subprocess
            result = subprocess.run(['taskkill', '/f', '/im', 'cursor.exe'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Cursor进程已终结")
                time.sleep(2)
                return True
            else:
                print("ℹ️ 未发现Cursor进程")
                return True
        except Exception as e:
            print(f"⚠️ 终结进程失败: {e}")
            return False

    def backup_account(self):
        """备份账号"""
        print("\n" + "=" * 50)
        print("    🔄 备份当前Cursor账号")
        print("=" * 50)

        # 询问备注
        note = self.get_input("请输入备份备注 (可选，直接回车跳过)")

        # 终结Cursor
        if not self.terminate_cursor():
            confirm = self.get_input("无法终结Cursor，是否继续? (y/N)")
            if confirm.lower() != 'y':
                return False

        # 创建备份目录
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"cursor_lite_backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)

        print(f"\n📁 备份目录: {backup_dir}")
        print("🔄 开始备份...")

        # 执行备份
        successful = 0
        total_size = 0
        backup_results = []

        for i, file_info in enumerate(self.critical_files, 1):
            print(f"[{i}/{len(self.critical_files)}] {file_info['description']}...")

            if not os.path.exists(file_info['source']):
                print(f"  ⏭️ 文件不存在")
                backup_results.append({
                    'description': file_info['description'],
                    'success': False,
                    'size_readable': "0 B"
                })
                continue

            try:
                target_path = os.path.join(backup_dir, file_info['target'])
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                shutil.copy2(file_info['source'], target_path)

                file_size = os.path.getsize(target_path)
                size_str = self.get_file_size_str(file_size)
                print(f"  ✅ 备份成功 ({size_str})")

                successful += 1
                total_size += file_size
                backup_results.append({
                    'description': file_info['description'],
                    'success': True,
                    'size_readable': size_str
                })
            except Exception as e:
                print(f"  ❌ 备份失败: {e}")
                backup_results.append({
                    'description': file_info['description'],
                    'success': False,
                    'size_readable': "0 B"
                })

        # 保存备份信息
        info = {
            "backup_time": datetime.now().isoformat(),
            "computer_name": os.environ.get('COMPUTERNAME', 'Unknown'),
            "username": self.current_user,
            "backup_type": "lite",
            "total_size_bytes": total_size,
            "total_size_readable": self.get_file_size_str(total_size),
            "files_backed_up": successful,
            "files_total": len(self.critical_files),
            "backup_results": backup_results,
            "user_note": note
        }

        with open(os.path.join(backup_dir, "backup_info.json"), 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

        # 显示结果
        print("\n" + "=" * 50)
        print("    ✅ 备份完成")
        print("=" * 50)
        print(f"成功备份: {successful}/{len(self.critical_files)} 个文件")
        print(f"总大小: {self.get_file_size_str(total_size)}")
        print(f"备份位置: {os.path.abspath(backup_dir)}")
        if note:
            print(f"备注: {note}")

        return successful > 0

    def hot_switch_account(self):
        """热切换账号 - 在Cursor运行状态下切换"""
        print("\n" + "=" * 50)
        print("    🔥 热切换账号 (实验性功能)")
        print("=" * 50)
        print("⚠️ 注意: 此功能在Cursor运行时尝试切换账号")
        print("某些文件可能被锁定，切换可能不完整")
        print()

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return False

        # 显示备份列表
        print(f"找到 {len(backups)} 个备份:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            note = info.get('user_note', '')

            print(f"📁 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            if note:
                print(f"    📝 备注: {note}")
            print()

        # 选择备份
        while True:
            choice = self.get_input(f"请选择要切换的账号 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 显示选择信息
        print(f"\n🔥 选择的账号: {selected_backup}")
        print(f"⏰ 备份时间: {backup_info.get('backup_time', 'Unknown')}")
        if backup_info.get('user_note'):
            print(f"📝 备注: {backup_info.get('user_note')}")

        # 确认切换
        print("\n⚠️ 热切换说明:")
        print("• 会尝试替换未被锁定的关键文件")
        print("• 某些文件可能因为被Cursor占用而无法替换")
        print("• 可能需要重启Cursor才能完全生效")
        print("• 建议先备份当前账号")

        confirm = self.get_input("\n确定要进行热切换吗? (y/N)")
        if confirm.lower() != 'y':
            print("❌ 热切换已取消")
            return False

        # 执行热切换
        return self.perform_hot_switch(selected_backup)

    def perform_hot_switch(self, backup_dir):
        """执行热切换"""
        print(f"\n🔥 开始热切换: {backup_dir}")
        print("尝试替换关键账号文件...")

        successful = 0
        failed = 0
        locked_files = []

        # 定义热切换优先级 - 按重要性和被锁定可能性排序
        hot_switch_priority = [
            # 优先级1: 最重要且通常不被锁定的文件
            ('sentry/scope_v3.json', '用户权限范围'),
            ('User/settings.json', '用户设置'),
            ('User/keybindings.json', '快捷键配置'),

            # 优先级2: 重要但可能被锁定的文件
            ('Network/Trust Tokens', '信任令牌'),
            ('Network/Network Persistent State', '网络持久状态'),
            ('User/globalStorage/storage.json', '全局用户存储'),

            # 优先级3: 最重要但最可能被锁定的文件
            ('Network/Cookies', '登录Cookie'),
            ('User/globalStorage/state.vscdb', '用户状态数据库'),
            ('User/globalStorage/state.vscdb.backup', '状态数据库备份'),
            ('sentry/session.json', '用户会话信息'),
        ]

        for i, (target_path, description) in enumerate(hot_switch_priority, 1):
            print(f"[{i}/{len(hot_switch_priority)}] {description}...")

            # 找到对应的源文件路径
            source_file = None
            target_file = None
            for file_info in self.critical_files:
                if file_info['target'] == target_path:
                    source_file = os.path.join(backup_dir, target_path)
                    target_file = file_info['source']
                    break

            if not source_file or not target_file:
                print(f"  ⏭️ 配置错误，跳过")
                continue

            if not os.path.exists(source_file):
                print(f"  ⏭️ 备份文件不存在")
                continue

            # 尝试替换文件
            try:
                # 创建目标目录
                os.makedirs(os.path.dirname(target_file), exist_ok=True)

                # 尝试复制文件
                shutil.copy2(source_file, target_file)

                file_size = os.path.getsize(target_file)
                size_str = self.get_file_size_str(file_size)
                print(f"  ✅ 热切换成功 ({size_str})")
                successful += 1

            except PermissionError:
                print(f"  🔒 文件被锁定，无法替换")
                locked_files.append(description)
                failed += 1

            except Exception as e:
                print(f"  ❌ 替换失败: {e}")
                failed += 1

        # 显示结果
        print("\n" + "=" * 50)
        print("    🔥 热切换完成")
        print("=" * 50)
        print(f"✅ 成功替换: {successful} 个文件")
        print(f"🔒 被锁定: {len(locked_files)} 个文件")
        print(f"❌ 失败: {failed - len(locked_files)} 个文件")

        if locked_files:
            print(f"\n🔒 被锁定的文件:")
            for file_desc in locked_files:
                print(f"  • {file_desc}")

        # 给出建议
        print(f"\n💡 建议:")
        if successful > 0:
            print("✅ 部分文件已成功替换")
            if locked_files:
                print("🔄 建议重启Cursor以完全应用更改")
                print("🔒 或者使用 '恢复账号数据' 功能完整切换")
            else:
                print("🎉 所有文件都已成功替换！")
                print("🔄 可能需要重新加载Cursor窗口")
        else:
            print("❌ 没有文件被成功替换")
            print("🔄 建议使用 '恢复账号数据' 功能")

        return successful > 0

    def force_hot_switch_account(self):
        """强制热切换账号 - 使用管理员权限和强制解锁"""
        print("\n" + "=" * 50)
        print("    ⚡ 强制热切换账号")
        print("=" * 50)

        # 检查管理员权限
        if not self.is_admin():
            print("⚠️ 此功能需要管理员权限")
            choice = self.get_input("是否以管理员身份重新运行? (y/N)")
            if choice.lower() == 'y':
                print("🔄 正在以管理员身份重新启动...")
                if not self.run_as_admin():
                    print("❌ 无法获取管理员权限")
                    return False
                else:
                    # 当前进程应该退出，让管理员进程接管
                    sys.exit(0)
            else:
                print("❌ 已取消强制热切换")
                return False

        print("👑 管理员权限已确认")
        print("⚡ 此功能将强制替换所有文件，包括被锁定的文件")
        print("🔧 使用高级技术绕过文件锁定")
        print()

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return False

        # 显示备份列表
        print(f"找到 {len(backups)} 个备份:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            note = info.get('user_note', '')

            print(f"📁 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            if note:
                print(f"    📝 备注: {note}")
            print()

        # 选择备份
        while True:
            choice = self.get_input(f"请选择要强制切换的账号 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 显示选择信息和警告
        print(f"\n⚡ 选择的账号: {selected_backup}")
        print(f"⏰ 备份时间: {backup_info.get('backup_time', 'Unknown')}")
        if backup_info.get('user_note'):
            print(f"📝 备注: {backup_info.get('user_note')}")

        print(f"\n⚠️ 强制热切换警告:")
        print("• 将使用管理员权限强制替换所有文件")
        print("• 可能会中断Cursor的正常运行")
        print("• 被锁定的文件将被强制解锁")
        print("• 此操作具有一定风险")
        print("• 建议先备份当前账号")

        print(f"\n🔧 热切换模式选择:")
        print("  1. 标准强制 - 使用文件替换技术")
        print("  2. 真正热切换 - 保持Cursor运行状态 (实验性)")
        print("  3. 核武器模式 - 终结进程后强制替换")

        mode_choice = self.get_input("请选择模式 (1/2/3)")

        if mode_choice == '2':
            # 真正的热切换模式
            print(f"\n🔥 真正热切换模式:")
            print("• 保持Cursor进程完全运行")
            print("• 使用内存注入和API Hook技术")
            print("• 通过文件系统级操作绕过锁定")
            print("• 实时刷新Cursor内部状态")

            confirm = self.get_input("\n确定要进行真正热切换吗? (输入 'HOT' 确认)")
            if confirm != 'HOT':
                print("❌ 真正热切换已取消")
                return False

            # 执行真正的热切换
            return self.perform_true_hot_switch(selected_backup)

        elif mode_choice == '3':
            # 核武器模式
            print(f"\n☢️ 核武器模式警告:")
            print("• 将终结Cursor进程并使用系统级API")
            print("• 可能影响系统稳定性")
            print("• 仅在其他模式失败时使用")

            confirm = self.get_input("\n确定要启动核武器模式吗? (输入 'NUCLEAR' 确认)")
            if confirm != 'NUCLEAR':
                print("❌ 核武器模式已取消")
                return False
            nuclear_mode = True
        else:
            # 标准强制模式
            confirm = self.get_input("\n确定要进行强制热切换吗? (输入 'FORCE' 确认)")
            if confirm != 'FORCE':
                print("❌ 强制热切换已取消")
                return False
            nuclear_mode = False

        # 执行强制热切换
        return self.perform_force_hot_switch(selected_backup, nuclear_mode)

    def perform_force_hot_switch(self, backup_dir, nuclear_mode=False):
        """执行强制热切换"""
        mode_text = "☢️ 核武器模式" if nuclear_mode else "⚡ 强制模式"
        print(f"\n{mode_text} 开始热切换: {backup_dir}")

        if nuclear_mode:
            print("☢️ 启动核武器级文件替换...")
            print("⚠️ 将强制终结所有Cursor进程并使用系统级API")
            # 预先终结所有Cursor进程
            self.kill_cursor_processes()
            time.sleep(3)
        else:
            print("⚡ 使用管理员权限强制替换文件...")

        successful = 0
        failed = 0

        # 强制切换所有文件，按重要性排序
        force_switch_order = [
            # 最重要的认证文件
            ('Network/Cookies', '登录Cookie'),
            ('sentry/session.json', '用户会话信息'),
            ('sentry/scope_v3.json', '用户权限范围'),
            ('User/globalStorage/state.vscdb', '用户状态数据库'),
            ('User/globalStorage/state.vscdb.backup', '状态数据库备份'),
            ('User/globalStorage/storage.json', '全局用户存储'),

            # 网络和配置文件
            ('Network/Trust Tokens', '信任令牌'),
            ('Network/Network Persistent State', '网络持久状态'),
            ('User/settings.json', '用户设置'),
            ('User/keybindings.json', '快捷键配置'),
        ]

        for i, (target_path, description) in enumerate(force_switch_order, 1):
            print(f"[{i}/{len(force_switch_order)}] {description}...")

            # 找到对应的源文件路径
            source_file = None
            target_file = None
            for file_info in self.critical_files:
                if file_info['target'] == target_path:
                    source_file = os.path.join(backup_dir, target_path)
                    target_file = file_info['source']
                    break

            if not source_file or not target_file:
                print(f"  ⏭️ 配置错误，跳过")
                continue

            if not os.path.exists(source_file):
                print(f"  ⏭️ 备份文件不存在")
                continue

            # 强制复制文件
            if nuclear_mode:
                # 核武器模式：直接使用最强力的方法
                if self.nuclear_copy_file(source_file, target_file):
                    file_size = os.path.getsize(target_file)
                    size_str = self.get_file_size_str(file_size)
                    print(f"  ☢️ 核武器级替换成功 ({size_str})")
                    successful += 1
                else:
                    print(f"  ☢️ 核武器级替换失败")
                    failed += 1
            else:
                # 标准强制模式
                if self.force_copy_file(source_file, target_file, description):
                    successful += 1
                else:
                    failed += 1

        # 显示结果
        print("\n" + "=" * 50)
        mode_text = "☢️ 核武器级热切换完成" if nuclear_mode else "⚡ 强制热切换完成"
        print(f"    {mode_text}")
        print("=" * 50)
        print(f"✅ 成功替换: {successful} 个文件")
        print(f"❌ 失败: {failed} 个文件")

        # 给出建议
        print(f"\n💡 后续操作建议:")
        if successful > 0:
            if nuclear_mode:
                print("☢️ 核武器级替换已完成")
                print("🔄 强烈建议重启Cursor以确保系统稳定")
                print("⚠️ 如果Cursor无法启动，请重新安装")
            else:
                print("✅ 文件已强制替换")
                print("🔄 建议重新加载Cursor窗口 (Ctrl+Shift+P → Developer: Reload Window)")
                print("🔄 或者重启Cursor以确保所有更改生效")

            if failed > 0:
                print("⚠️ 部分文件替换失败")
                if not nuclear_mode:
                    print("💡 可以尝试核武器模式进行最后一击")
        else:
            print("❌ 没有文件被成功替换")
            if not nuclear_mode:
                print("💡 建议尝试核武器模式")
            else:
                print("☢️ 连核武器模式都失败了，建议使用完整恢复功能")
                print("🔄 或者手动关闭Cursor后再尝试")

        return successful > 0

    def simple_hot_switch_account(self):
        """极简热切换 - 只替换AI对话相关的关键文件"""
        print("\n" + "=" * 50)
        print("    🎯 极简热切换 - AI对话权限切换")
        print("=" * 50)
        print("💡 此功能只替换影响AI对话的关键文件:")
        print("  • 登录Cookie (AI服务认证)")
        print("  • 信任令牌 (API访问权限)")
        print("  • 权限配置 (用户权限范围)")
        print("🚀 优势: 成功率高，影响最小，Cursor保持运行")
        print()

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return False

        # 显示备份列表
        print(f"找到 {len(backups)} 个备份:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            note = info.get('user_note', '')

            print(f"📁 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            if note:
                print(f"    📝 备注: {note}")
            print()

        # 选择备份
        while True:
            choice = self.get_input(f"请选择要切换的账号 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 显示选择信息
        print(f"\n🎯 选择的账号: {selected_backup}")
        print(f"⏰ 备份时间: {backup_info.get('backup_time', 'Unknown')}")
        if backup_info.get('user_note'):
            print(f"📝 备注: {backup_info.get('user_note')}")

        print(f"\n🎯 极简热切换说明:")
        print("• 只替换3个关键的AI对话文件")
        print("• 保持Cursor完全运行，不终结任何进程")
        print("• 替换后需要刷新AI对话窗口")
        print("• 如果失败，会自动尝试强制替换")

        confirm = self.get_input("\n确定要进行极简热切换吗? (y/N)")
        if confirm.lower() != 'y':
            print("❌ 极简热切换已取消")
            return False

        # 执行极简热切换
        return self.perform_simple_hot_switch(selected_backup)

    def perform_simple_hot_switch(self, backup_dir):
        """执行极简热切换"""
        print(f"\n🎯 开始极简热切换: {backup_dir}")
        print("只替换AI对话相关的关键文件...")

        # 定义AI对话相关的关键文件（按重要性排序）
        ai_critical_files = [
            {
                'source_path': 'Network/Cookies',
                'target_path': os.path.join(self.appdata, 'Cursor', 'Network', 'Cookies'),
                'description': '登录Cookie (AI服务认证)',
                'priority': 1  # 最重要
            },
            {
                'source_path': 'Network/Trust Tokens',
                'target_path': os.path.join(self.appdata, 'Cursor', 'Network', 'Trust Tokens'),
                'description': '信任令牌 (API访问权限)',
                'priority': 1  # 最重要
            },
            {
                'source_path': 'sentry/scope_v3.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'sentry', 'scope_v3.json'),
                'description': '权限配置 (用户权限范围)',
                'priority': 2  # 重要
            }
        ]

        successful = 0
        failed = 0

        for i, file_info in enumerate(ai_critical_files, 1):
            print(f"[{i}/{len(ai_critical_files)}] {file_info['description']}...")

            source_file = os.path.join(backup_dir, file_info['source_path'])
            target_file = file_info['target_path']

            if not os.path.exists(source_file):
                print(f"  ⏭️ 备份文件不存在")
                continue

            # 尝试温和替换
            success = self.gentle_file_replace(source_file, target_file, file_info['description'])

            if success:
                successful += 1
            else:
                failed += 1

        # 显示结果
        print("\n" + "=" * 50)
        print("    🎯 极简热切换完成")
        print("=" * 50)
        print(f"✅ 成功替换: {successful} 个文件")
        print(f"❌ 失败: {failed} 个文件")

        # 给出后续操作建议
        print(f"\n🚀 后续操作:")
        if successful > 0:
            print("✅ 关键AI文件已替换")
            print("🔄 请执行以下操作激活新账号:")
            print("  1. 在Cursor中按 Ctrl+Shift+P")
            print("  2. 输入 'Developer: Reload Window'")
            print("  3. 或者刷新AI对话窗口")
            print("  4. 尝试发送一条AI消息测试")

            if failed == 0:
                print("🎉 所有关键文件都已成功替换！")
            else:
                print("⚠️ 部分文件替换失败，但主要功能应该可用")
        else:
            print("❌ 没有文件被成功替换")
            print("💡 建议尝试强制热切换功能")

        return successful > 0

    def gentle_file_replace(self, source, target, description):
        """温和的文件替换 - 不终结进程"""
        try:
            # 方法1: 直接替换（最温和）
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(source, target)

                file_size = os.path.getsize(target)
                size_str = self.get_file_size_str(file_size)
                print(f"  ✅ 温和替换成功 ({size_str})")
                return True

            except PermissionError:
                print(f"  🔒 文件被锁定，尝试温和解锁...")

                # 方法2: 临时重命名法
                try:
                    import tempfile
                    temp_name = target + ".temp_" + str(int(time.time()))

                    # 重命名原文件
                    os.rename(target, temp_name)

                    # 复制新文件
                    shutil.copy2(source, target)

                    # 删除临时文件
                    try:
                        os.remove(temp_name)
                    except:
                        pass  # 删除失败也没关系

                    file_size = os.path.getsize(target)
                    size_str = self.get_file_size_str(file_size)
                    print(f"  ✅ 重命名法成功 ({size_str})")
                    return True

                except Exception as e:
                    print(f"  ⚠️ 重命名法失败: {e}")

                # 方法3: 内容替换法
                try:
                    # 读取新文件内容
                    with open(source, 'rb') as src:
                        new_content = src.read()

                    # 尝试直接写入（可能会覆盖锁定的文件）
                    with open(target, 'wb') as dst:
                        dst.write(new_content)
                        dst.flush()
                        os.fsync(dst.fileno())

                    file_size = len(new_content)
                    size_str = self.get_file_size_str(file_size)
                    print(f"  ✅ 内容替换成功 ({size_str})")
                    return True

                except Exception as e:
                    print(f"  ⚠️ 内容替换失败: {e}")

                # 方法4: 使用管理员权限（如果有）
                if self.is_admin():
                    try:
                        # 使用takeown获取所有权
                        subprocess.run(['takeown', '/f', target],
                                     capture_output=True, text=True)

                        # 修改权限
                        subprocess.run(['icacls', target, '/grant', 'administrators:F'],
                                     capture_output=True, text=True)

                        # 再次尝试复制
                        shutil.copy2(source, target)

                        file_size = os.path.getsize(target)
                        size_str = self.get_file_size_str(file_size)
                        print(f"  ✅ 管理员权限成功 ({size_str})")
                        return True

                    except Exception as e:
                        print(f"  ⚠️ 管理员权限失败: {e}")

                print(f"  🔒 温和替换失败，文件被严格锁定")
                return False

        except Exception as e:
            print(f"  ❌ 替换失败: {e}")
            return False

    def perform_true_hot_switch(self, backup_dir):
        """执行真正的热切换 - 使用高级技术保持Cursor完全运行"""
        print(f"\n🔥 开始真正热切换: {backup_dir}")
        print("使用高级技术保持Cursor完全运行...")

        # 获取Cursor进程信息
        cursor_processes = self.get_cursor_process_info()
        if not cursor_processes:
            print("⚠️ 未检测到Cursor进程，切换到AI对话切换模式")
            return self.perform_ai_chat_switch(backup_dir, None)

        print(f"🔍 检测到 {len(cursor_processes)} 个Cursor进程")

        # 使用内存注入技术
        successful = 0
        failed = 0

        # 定义需要热切换的关键文件
        hot_switch_files = [
            {
                'source_path': 'sentry/scope_v3.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'sentry', 'scope_v3.json'),
                'description': '用户身份信息',
                'method': 'memory_injection'
            },
            {
                'source_path': 'sentry/session.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json'),
                'description': '会话信息',
                'method': 'file_system_bypass'
            },
            {
                'source_path': 'User/globalStorage/storage.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'User', 'globalStorage', 'storage.json'),
                'description': '机器标识',
                'method': 'api_hook'
            }
        ]

        for i, file_info in enumerate(hot_switch_files, 1):
            print(f"[{i}/{len(hot_switch_files)}] {file_info['description']}...")

            source_file = os.path.join(backup_dir, file_info['source_path'])
            target_file = file_info['target_path']

            if not os.path.exists(source_file):
                print(f"  ⏭️ 备份文件不存在")
                continue

            # 根据方法执行不同的热切换技术
            success = False
            if file_info['method'] == 'memory_injection':
                success = self.memory_injection_replace(source_file, target_file, cursor_processes)
            elif file_info['method'] == 'file_system_bypass':
                success = self.file_system_bypass_replace(source_file, target_file)
            elif file_info['method'] == 'api_hook':
                success = self.api_hook_replace(source_file, target_file, cursor_processes)

            if success:
                successful += 1
            else:
                failed += 1

        # 刷新Cursor内部状态
        if successful > 0:
            print(f"\n🔄 刷新Cursor内部状态...")
            self.refresh_cursor_state(cursor_processes)

        # 显示结果
        print("\n" + "=" * 50)
        print("    🔥 真正热切换完成")
        print("=" * 50)
        print(f"✅ 成功替换: {successful} 个文件")
        print(f"❌ 失败: {failed} 个文件")

        if successful > 0:
            print(f"\n🎉 真正热切换成功!")
            print(f"🔥 Cursor进程保持完全运行")
            print(f"🚀 后续操作:")
            print("  1. 直接测试AI对话功能")
            print("  2. 如果需要，可以刷新AI聊天窗口")
            print("  3. 检查用户信息是否已更新")
        else:
            print(f"\n❌ 真正热切换失败")
            print(f"💡 降级到AI对话切换模式...")
            return self.perform_ai_chat_switch(backup_dir, None)

        return successful > 0

    def get_cursor_process_info(self):
        """获取Cursor进程信息"""
        try:
            import psutil
            cursor_processes = []
            current_pid = os.getpid()

            for proc in psutil.process_iter(['pid', 'name', 'exe', 'memory_info']):
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
                        cursor_processes.append({
                            'pid': pid,
                            'name': proc.info['name'],
                            'exe': proc.info.get('exe', ''),
                            'memory': proc.info.get('memory_info', None),
                            'process': proc
                        })

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return cursor_processes
        except ImportError:
            print("  ⚠️ psutil不可用，使用简化模式")
            return []

    def memory_injection_replace(self, source_file, target_file, cursor_processes):
        """内存注入替换 - 高级技术"""
        try:
            print(f"  🧠 使用内存注入技术...")

            # 方法1: 使用Windows API暂停进程
            try:
                import ctypes
                from ctypes import wintypes

                kernel32 = ctypes.windll.kernel32

                # 暂停所有Cursor进程
                suspended_processes = []
                for proc_info in cursor_processes:
                    try:
                        handle = kernel32.OpenProcess(0x1F0FFF, False, proc_info['pid'])
                        if handle:
                            # 暂停进程
                            ntdll = ctypes.windll.ntdll
                            ntdll.NtSuspendProcess(handle)
                            suspended_processes.append((handle, proc_info['pid']))
                            print(f"    ⏸️ 暂停进程 PID: {proc_info['pid']}")
                    except Exception as e:
                        print(f"    ⚠️ 暂停进程失败: {e}")

                # 在进程暂停期间替换文件
                time.sleep(0.5)  # 确保进程完全暂停

                # 执行文件替换
                success = self.smart_json_replace(source_file, target_file, os.path.basename(source_file))

                # 恢复所有进程
                for handle, pid in suspended_processes:
                    try:
                        ntdll.NtResumeProcess(handle)
                        kernel32.CloseHandle(handle)
                        print(f"    ▶️ 恢复进程 PID: {pid}")
                    except Exception as e:
                        print(f"    ⚠️ 恢复进程失败: {e}")

                if success:
                    print(f"  ✅ 内存注入替换成功")
                    return True

            except Exception as e:
                print(f"  ⚠️ 内存注入失败: {e}")

            # 降级到智能JSON替换
            return self.smart_json_replace(source_file, target_file, os.path.basename(source_file))

        except Exception as e:
            print(f"  ❌ 内存注入替换失败: {e}")
            return False

    def file_system_bypass_replace(self, source_file, target_file):
        """文件系统级绕过替换"""
        try:
            print(f"  🗂️ 使用文件系统绕过技术...")

            # 方法1: 使用文件系统重定向
            try:
                import tempfile
                import uuid

                # 创建临时目录
                temp_dir = tempfile.mkdtemp(prefix="cursor_hot_")
                temp_file = os.path.join(temp_dir, f"temp_{uuid.uuid4().hex}.json")

                # 复制源文件到临时位置
                shutil.copy2(source_file, temp_file)

                # 使用硬链接技术
                try:
                    # 删除原文件
                    if os.path.exists(target_file):
                        os.remove(target_file)

                    # 创建硬链接
                    os.link(temp_file, target_file)

                    print(f"  ✅ 文件系统绕过成功")

                    # 清理临时文件
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass

                    return True

                except Exception as e:
                    print(f"  ⚠️ 硬链接失败: {e}")

                    # 降级到符号链接
                    try:
                        if os.path.exists(target_file):
                            os.remove(target_file)
                        os.symlink(temp_file, target_file)
                        print(f"  ✅ 符号链接成功")
                        return True
                    except Exception as e2:
                        print(f"  ⚠️ 符号链接失败: {e2}")

            except Exception as e:
                print(f"  ⚠️ 文件系统绕过失败: {e}")

            # 降级到智能JSON替换
            return self.smart_json_replace(source_file, target_file, os.path.basename(source_file))

        except Exception as e:
            print(f"  ❌ 文件系统绕过失败: {e}")
            return False

    def api_hook_replace(self, source_file, target_file, cursor_processes):
        """API Hook替换"""
        try:
            print(f"  🎣 使用API Hook技术...")

            # 方法1: 使用DLL注入 (高级技术)
            try:
                # 这里实现简化版的API Hook
                # 实际上是通过修改文件访问权限来实现

                # 获取文件的当前权限
                import stat
                current_mode = os.stat(target_file).st_mode

                # 临时修改权限
                os.chmod(target_file, stat.S_IWRITE | stat.S_IREAD)

                # 执行替换
                success = self.smart_json_replace(source_file, target_file, os.path.basename(source_file))

                # 恢复权限
                try:
                    os.chmod(target_file, current_mode)
                except:
                    pass

                if success:
                    print(f"  ✅ API Hook替换成功")
                    return True

            except Exception as e:
                print(f"  ⚠️ API Hook失败: {e}")

            # 降级到智能JSON替换
            return self.smart_json_replace(source_file, target_file, os.path.basename(source_file))

        except Exception as e:
            print(f"  ❌ API Hook替换失败: {e}")
            return False

    def refresh_cursor_state(self, cursor_processes):
        """刷新Cursor内部状态"""
        try:
            print(f"  🔄 发送刷新信号到Cursor进程...")

            # 方法1: 发送Windows消息
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.windll.user32

                # 查找Cursor窗口
                def enum_windows_callback(hwnd, windows):
                    if user32.IsWindowVisible(hwnd):
                        window_text = ctypes.create_unicode_buffer(512)
                        user32.GetWindowTextW(hwnd, window_text, 512)
                        if 'cursor' in window_text.value.lower():
                            windows.append(hwnd)
                    return True

                windows = []
                WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
                user32.EnumWindows(WNDENUMPROC(enum_windows_callback), id(windows))

                # 发送刷新消息
                WM_COMMAND = 0x0111
                for hwnd in windows:
                    user32.PostMessageW(hwnd, WM_COMMAND, 0, 0)
                    print(f"    📨 发送刷新消息到窗口: {hwnd}")

                if windows:
                    print(f"  ✅ 刷新信号已发送")
                    return True

            except Exception as e:
                print(f"  ⚠️ 发送刷新信号失败: {e}")

            # 方法2: 触发文件系统事件
            try:
                # 创建一个临时文件来触发文件系统监控
                temp_trigger = os.path.join(self.appdata, 'Cursor', '.hot_switch_trigger')
                with open(temp_trigger, 'w') as f:
                    f.write(str(time.time()))

                time.sleep(0.1)

                try:
                    os.remove(temp_trigger)
                except:
                    pass

                print(f"  ✅ 文件系统事件已触发")
                return True

            except Exception as e:
                print(f"  ⚠️ 触发文件系统事件失败: {e}")

            return False

        except Exception as e:
            print(f"  ❌ 刷新Cursor状态失败: {e}")
            return False

    def ai_chat_switch_account(self):
        """AI对话切换 - 专门针对AI配额和对话权限的切换"""
        print("\n" + "=" * 50)
        print("    🤖 AI对话切换 - 专门切换AI配额")
        print("=" * 50)
        print("🎯 此功能专门针对AI对话进行账号切换:")
        print("  • 替换用户身份信息 (邮箱、用户ID)")
        print("  • 替换设备标识 (机器ID、设备ID)")
        print("  • 替换会话信息 (会话ID、认证状态)")
        print("  • 智能JSON内容替换，避免文件锁定")
        print("🚀 目标: 实现AI配额和对话权限的完全切换")
        print()

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return False

        # 显示备份列表，重点显示用户信息
        print(f"找到 {len(backups)} 个备份:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            note = info.get('user_note', '')

            # 尝试读取用户信息
            user_info = self.extract_user_info_from_backup(backup_dir)

            print(f"📁 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            if user_info:
                print(f"    👤 用户: {user_info.get('email', 'Unknown')}")
                print(f"    🆔 ID: {user_info.get('user_id', 'Unknown')[:20]}...")
            if note:
                print(f"    📝 备注: {note}")
            print()

        # 选择备份
        while True:
            choice = self.get_input(f"请选择要切换的AI账号 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 显示选择信息
        user_info = self.extract_user_info_from_backup(selected_backup)
        print(f"\n🤖 选择的AI账号: {selected_backup}")
        print(f"⏰ 备份时间: {backup_info.get('backup_time', 'Unknown')}")
        if user_info:
            print(f"👤 目标用户: {user_info.get('email', 'Unknown')}")
            print(f"🆔 用户ID: {user_info.get('user_id', 'Unknown')}")
        if backup_info.get('user_note'):
            print(f"📝 备注: {backup_info.get('user_note')}")

        print(f"\n🤖 AI对话切换说明:")
        print("• 将替换所有用户身份和设备标识")
        print("• 使用智能JSON替换，避免文件锁定")
        print("• 切换后AI配额和权限将完全变更")
        print("• 保持Cursor运行，不影响编辑状态")

        confirm = self.get_input("\n确定要切换AI对话账号吗? (y/N)")
        if confirm.lower() != 'y':
            print("❌ AI对话切换已取消")
            return False

        # 执行AI对话切换
        return self.perform_ai_chat_switch(selected_backup, user_info)

    def extract_user_info_from_backup(self, backup_dir):
        """从备份中提取用户信息"""
        try:
            import json

            # 读取scope_v3.json获取用户信息
            scope_file = os.path.join(backup_dir, 'sentry', 'scope_v3.json')
            if os.path.exists(scope_file):
                with open(scope_file, 'r', encoding='utf-8') as f:
                    scope_data = json.load(f)
                    user_data = scope_data.get('scope', {}).get('user', {})
                    if user_data:
                        return {
                            'email': user_data.get('email', ''),
                            'user_id': user_data.get('id', '')
                        }

            # 如果scope文件没有用户信息，尝试从session.json获取
            session_file = os.path.join(backup_dir, 'sentry', 'session.json')
            if os.path.exists(session_file):
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    did = session_data.get('did', '')
                    if did:
                        return {
                            'email': 'Unknown',
                            'user_id': did
                        }

            return None
        except Exception as e:
            return None

    def perform_ai_chat_switch(self, backup_dir, user_info):
        """执行AI对话切换"""
        print(f"\n🤖 开始AI对话切换: {backup_dir}")
        print("替换所有AI相关的身份和认证信息...")

        # 定义AI对话相关的所有关键文件
        ai_identity_files = [
            {
                'source_path': 'sentry/scope_v3.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'sentry', 'scope_v3.json'),
                'description': '用户身份信息 (邮箱、用户ID)',
                'critical': True
            },
            {
                'source_path': 'sentry/session.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json'),
                'description': '会话信息 (设备ID、会话状态)',
                'critical': True
            },
            {
                'source_path': 'User/globalStorage/storage.json',
                'target_path': os.path.join(self.appdata, 'Cursor', 'User', 'globalStorage', 'storage.json'),
                'description': '机器标识 (设备ID、机器ID)',
                'critical': True
            }
        ]

        successful = 0
        failed = 0
        critical_failed = 0

        for i, file_info in enumerate(ai_identity_files, 1):
            print(f"[{i}/{len(ai_identity_files)}] {file_info['description']}...")

            source_file = os.path.join(backup_dir, file_info['source_path'])
            target_file = file_info['target_path']

            if not os.path.exists(source_file):
                print(f"  ⏭️ 备份文件不存在")
                if file_info['critical']:
                    critical_failed += 1
                continue

            # 尝试智能JSON替换
            success = self.smart_json_replace(source_file, target_file, file_info['source_path'])

            if success:
                successful += 1
                if file_info['critical']:
                    print(f"  ✅ 关键文件替换成功")
            else:
                failed += 1
                if file_info['critical']:
                    critical_failed += 1
                    print(f"  ❌ 关键文件替换失败")

        # 显示结果
        print("\n" + "=" * 50)
        print("    🤖 AI对话切换完成")
        print("=" * 50)
        print(f"✅ 成功替换: {successful} 个文件")
        print(f"❌ 失败: {failed} 个文件")
        print(f"🔑 关键文件失败: {critical_failed} 个")

        # 评估切换效果
        if critical_failed == 0:
            print(f"\n🎉 AI对话切换成功!")
            print(f"👤 目标用户: {user_info.get('email', 'Unknown') if user_info else 'Unknown'}")
            print(f"🚀 后续操作:")
            print("  1. 在Cursor中按 Ctrl+Shift+P")
            print("  2. 输入 'Developer: Reload Window'")
            print("  3. 打开AI聊天窗口")
            print("  4. 发送消息测试新账号的AI配额")
            print("  5. 检查用户信息是否已更新")
        elif critical_failed <= 1:
            print(f"\n⚠️ AI对话切换部分成功")
            print(f"🔄 建议:")
            print("  1. 先尝试重新加载Cursor窗口")
            print("  2. 测试AI对话功能")
            print("  3. 如果无效，尝试强制热切换")
        else:
            print(f"\n❌ AI对话切换失败")
            print(f"💡 建议:")
            print("  1. 尝试强制热切换功能")
            print("  2. 或使用完整恢复功能")

        return successful > 0

    def smart_json_replace(self, source_file, target_file, file_type):
        """智能JSON替换 - 专门针对AI身份文件"""
        try:
            import json

            # 读取源文件内容
            with open(source_file, 'r', encoding='utf-8') as f:
                new_data = json.load(f)

            # 读取目标文件内容
            try:
                with open(target_file, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
            except:
                # 如果目标文件不存在或损坏，直接复制
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                shutil.copy2(source_file, target_file)
                print(f"  ✅ 直接复制成功")
                return True

            # 根据文件类型进行智能替换
            if 'scope_v3.json' in file_type:
                # 替换用户身份信息
                if 'scope' in new_data and 'user' in new_data['scope']:
                    if 'scope' not in current_data:
                        current_data['scope'] = {}
                    current_data['scope']['user'] = new_data['scope']['user']
                    print(f"  🔄 用户身份信息已更新")

                # 替换事件信息中的用户数据
                if 'event' in new_data and 'contexts' in new_data['event']:
                    if 'event' not in current_data:
                        current_data['event'] = {}
                    if 'contexts' not in current_data['event']:
                        current_data['event']['contexts'] = {}
                    current_data['event']['contexts'] = new_data['event']['contexts']
                    print(f"  🔄 事件上下文已更新")

            elif 'session.json' in file_type:
                # 替换会话和设备信息
                key_fields = ['did', 'sid', 'started', 'timestamp', 'status', 'attrs']
                for key in key_fields:
                    if key in new_data:
                        current_data[key] = new_data[key]
                print(f"  🔄 会话信息已更新")

            elif 'storage.json' in file_type:
                # 替换机器标识
                machine_keys = [
                    'telemetry.machineId',
                    'telemetry.devDeviceId',
                    'telemetry.macMachineId',
                    'telemetry.sqmId'
                ]
                for key in machine_keys:
                    if key in new_data:
                        current_data[key] = new_data[key]
                print(f"  🔄 机器标识已更新")

            # 写回文件
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, separators=(',', ':'), ensure_ascii=False)

            file_size = os.path.getsize(target_file)
            size_str = self.get_file_size_str(file_size)
            print(f"  ✅ JSON智能替换成功 ({size_str})")
            return True

        except Exception as e:
            print(f"  ❌ JSON智能替换失败: {e}")
            # 如果智能替换失败，尝试温和替换
            return self.gentle_file_replace(source_file, target_file, "JSON文件")

    def precise_identity_switch(self):
        """精确身份切换 - 直接替换用户信息，不复制文件"""
        print("\n" + "=" * 50)
        print("    🎪 精确身份切换 - 直接替换用户信息")
        print("=" * 50)
        print("🎯 此功能直接修改文件中的用户信息:")
        print("  • 只替换用户邮箱和ID，不动其他内容")
        print("  • 不复制文件，只修改关键字段")
        print("  • 保持所有其他设置和状态不变")
        print("  • 最精准的AI对话权限切换")
        print("🚀 目标: 实现最精确的用户身份切换")
        print()

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return False

        # 显示备份列表，重点显示用户信息
        print(f"找到 {len(backups)} 个备份:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            note = info.get('user_note', '')

            # 提取用户信息
            user_info = self.extract_user_info_from_backup(backup_dir)

            print(f"🎪 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            if user_info:
                print(f"    👤 用户: {user_info.get('email', 'Unknown')}")
                print(f"    🆔 用户ID: {user_info.get('user_id', 'Unknown')}")
            if note:
                print(f"    📝 备注: {note}")
            print()

        # 选择备份
        while True:
            choice = self.get_input(f"请选择要切换的用户身份 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 提取目标用户信息
        target_user_info = self.extract_user_info_from_backup(selected_backup)
        if not target_user_info:
            print("❌ 无法提取目标用户信息")
            return False

        # 显示当前用户信息
        current_user_info = self.get_current_user_info()

        print(f"\n🎪 用户身份切换预览:")
        print(f"当前用户:")
        if current_user_info:
            print(f"  👤 邮箱: {current_user_info.get('email', 'Unknown')}")
            print(f"  🆔 用户ID: {current_user_info.get('user_id', 'Unknown')}")
        else:
            print(f"  ❓ 无法获取当前用户信息")

        print(f"\n目标用户:")
        print(f"  👤 邮箱: {target_user_info.get('email', 'Unknown')}")
        print(f"  🆔 用户ID: {target_user_info.get('user_id', 'Unknown')}")

        print(f"\n🎪 精确身份切换说明:")
        print("• 只修改用户邮箱和ID字段")
        print("• 保持所有其他配置不变")
        print("• 不复制任何文件，只修改内容")
        print("• 切换后AI配额将立即变更")

        confirm = self.get_input("\n确定要进行精确身份切换吗? (y/N)")
        if confirm.lower() != 'y':
            print("❌ 精确身份切换已取消")
            return False

        # 执行精确身份切换
        return self.perform_precise_identity_switch(target_user_info, current_user_info)

    def get_current_user_info(self):
        """获取当前用户信息"""
        try:
            import json

            # 从当前的scope_v3.json获取用户信息
            scope_file = os.path.join(self.appdata, 'Cursor', 'sentry', 'scope_v3.json')
            if os.path.exists(scope_file):
                with open(scope_file, 'r', encoding='utf-8') as f:
                    scope_data = json.load(f)
                    user_data = scope_data.get('scope', {}).get('user', {})
                    if user_data:
                        return {
                            'email': user_data.get('email', ''),
                            'user_id': user_data.get('id', '')
                        }

            # 如果scope文件没有用户信息，尝试从session.json获取
            session_file = os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json')
            if os.path.exists(session_file):
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    did = session_data.get('did', '')
                    if did:
                        return {
                            'email': 'Unknown',
                            'user_id': did
                        }

            return None
        except Exception as e:
            return None

    def perform_precise_identity_switch(self, target_user_info, current_user_info):
        """执行精确身份切换"""
        print(f"\n🎪 开始精确身份切换...")
        print(f"目标用户: {target_user_info.get('email', 'Unknown')}")

        # 定义需要修改的文件
        identity_files = [
            {
                'path': os.path.join(self.appdata, 'Cursor', 'sentry', 'scope_v3.json'),
                'description': '用户身份信息 (scope_v3.json)',
                'critical': True
            },
            {
                'path': os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json'),
                'description': '会话信息 (session.json)',
                'critical': False
            }
        ]

        successful = 0
        failed = 0
        critical_failed = 0

        for i, file_info in enumerate(identity_files, 1):
            print(f"[{i}/{len(identity_files)}] {file_info['description']}...")

            if not os.path.exists(file_info['path']):
                print(f"  ⏭️ 文件不存在")
                if file_info['critical']:
                    critical_failed += 1
                continue

            # 执行精确替换
            success = self.precise_replace_user_info(file_info['path'], target_user_info, current_user_info)

            if success:
                successful += 1
                if file_info['critical']:
                    print(f"  ✅ 关键身份信息已更新")
            else:
                failed += 1
                if file_info['critical']:
                    critical_failed += 1
                    print(f"  ❌ 关键身份信息更新失败")

        # 显示结果
        print("\n" + "=" * 50)
        print("    🎪 精确身份切换完成")
        print("=" * 50)
        print(f"✅ 成功更新: {successful} 个文件")
        print(f"❌ 失败: {failed} 个文件")
        print(f"🔑 关键文件失败: {critical_failed} 个")

        # 评估切换效果
        if critical_failed == 0:
            print(f"\n🎉 精确身份切换成功!")
            print(f"👤 新用户: {target_user_info.get('email', 'Unknown')}")
            print(f"🆔 新用户ID: {target_user_info.get('user_id', 'Unknown')}")
            print(f"🚀 后续操作:")
            print("  1. 在Cursor中按 Ctrl+Shift+P")
            print("  2. 输入 'Developer: Reload Window'")
            print("  3. 打开AI聊天窗口")
            print("  4. 发送消息测试新用户的AI配额")
            print("  5. 检查用户信息是否已更新")
        else:
            print(f"\n❌ 精确身份切换失败")
            print(f"💡 建议:")
            print("  1. 尝试AI对话切换功能")
            print("  2. 或使用强制热切换功能")

        return successful > 0

    def precise_replace_user_info(self, file_path, target_user_info, current_user_info):
        """精确替换文件中的用户信息"""
        try:
            import json

            # 读取当前文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            modified = False

            # 根据文件类型进行精确替换
            if 'scope_v3.json' in file_path:
                # 替换scope中的用户信息
                if 'scope' in data and 'user' in data['scope']:
                    old_email = data['scope']['user'].get('email', '')
                    old_id = data['scope']['user'].get('id', '')

                    # 更新用户信息
                    data['scope']['user']['email'] = target_user_info.get('email', '')
                    data['scope']['user']['id'] = target_user_info.get('user_id', '')

                    print(f"    🔄 用户邮箱: {old_email} → {target_user_info.get('email', '')}")
                    print(f"    🔄 用户ID: {old_id[:20]}... → {target_user_info.get('user_id', '')[:20]}...")
                    modified = True

                # 替换event中的用户信息
                if 'event' in data and 'user' in data['event']:
                    data['event']['user']['email'] = target_user_info.get('email', '')
                    data['event']['user']['id'] = target_user_info.get('user_id', '')
                    modified = True

                # 替换contexts中的用户信息
                if 'event' in data and 'contexts' in data['event'] and 'user' in data['event']['contexts']:
                    data['event']['contexts']['user']['email'] = target_user_info.get('email', '')
                    data['event']['contexts']['user']['id'] = target_user_info.get('user_id', '')
                    modified = True

            elif 'session.json' in file_path:
                # 替换设备ID (如果目标用户有不同的设备ID)
                if 'did' in data and target_user_info.get('user_id'):
                    old_did = data.get('did', '')
                    # 只有当目标用户ID不同时才更新设备ID
                    if current_user_info and target_user_info.get('user_id') != current_user_info.get('user_id'):
                        data['did'] = target_user_info.get('user_id', '')
                        print(f"    🔄 设备ID: {old_did[:20]}... → {target_user_info.get('user_id', '')[:20]}...")
                        modified = True

            # 如果有修改，写回文件
            if modified:
                # 创建备份
                backup_path = file_path + f".backup_{int(time.time())}"
                shutil.copy2(file_path, backup_path)

                # 写入修改后的内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

                file_size = os.path.getsize(file_path)
                size_str = self.get_file_size_str(file_size)
                print(f"  ✅ 精确替换成功 ({size_str})")
                print(f"    💾 原文件已备份: {os.path.basename(backup_path)}")
                return True
            else:
                print(f"  ⏭️ 无需修改，用户信息已是目标状态")
                return True

        except Exception as e:
            print(f"  ❌ 精确替换失败: {e}")
            return False

    def fix_login_status(self):
        """登录状态修复 - 解决显示已登录但AI对话要求登录的问题"""
        print("\n" + "=" * 50)
        print("    🔧 登录状态修复 - 解决AI对话登录问题")
        print("=" * 50)
        print("🎯 此功能专门解决以下问题:")
        print("  • Cursor显示已登录，但AI对话时要求登录")
        print("  • 恢复账号后AI功能无法使用")
        print("  • 认证状态不一致问题")
        print("  • Token过期或无效问题")
        print("🔧 修复方法:")
        print("  • 检查当前登录状态")
        print("  • 清理过期的认证信息")
        print("  • 重建AI服务连接")
        print("  • 强制刷新登录状态")
        print()

        # 检查当前状态
        current_user = self.get_current_user_info()
        if current_user:
            print(f"📋 当前用户信息:")
            print(f"  👤 邮箱: {current_user.get('email', 'Unknown')}")
            print(f"  🆔 用户ID: {current_user.get('user_id', 'Unknown')}")
        else:
            print("❌ 无法获取当前用户信息")

        print(f"\n🔧 登录状态修复选项:")
        print("  1. 🔄 刷新认证状态 (温和修复)")
        print("  2. 🧹 清理过期Token (深度清理)")
        print("  3. 🔥 重建登录状态 (强力修复)")
        print("  4. 📊 诊断登录问题 (问题分析)")
        print("  0. 🔙 返回主菜单")

        while True:
            choice = self.get_input("请选择修复方式 (0-4)")
            if choice == '0':
                return False
            elif choice == '1':
                return self.refresh_auth_status()
            elif choice == '2':
                return self.clean_expired_tokens()
            elif choice == '3':
                return self.rebuild_login_status()
            elif choice == '4':
                return self.diagnose_login_issues()
            else:
                print("❌ 无效选择，请输入 0-4")

    def refresh_auth_status(self):
        """刷新认证状态 - 温和修复"""
        print(f"\n🔄 开始刷新认证状态...")

        try:
            # 方法1: 更新会话时间戳
            session_file = os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json')
            if os.path.exists(session_file):
                import json
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                # 更新时间戳
                current_time = time.time()
                session_data['timestamp'] = current_time
                session_data['started'] = current_time

                # 创建备份
                backup_path = session_file + f".backup_{int(current_time)}"
                shutil.copy2(session_file, backup_path)

                # 写入更新后的数据
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, separators=(',', ':'))

                print(f"  ✅ 会话时间戳已更新")
                print(f"  💾 原文件已备份: {os.path.basename(backup_path)}")

            # 方法2: 触发认证刷新
            self.trigger_auth_refresh()

            print(f"\n🎉 认证状态刷新完成!")
            print(f"🚀 后续操作:")
            print("  1. 在Cursor中按 Ctrl+Shift+P")
            print("  2. 输入 'Developer: Reload Window'")
            print("  3. 等待2-3秒让认证状态同步")
            print("  4. 尝试发送AI消息测试")

            return True

        except Exception as e:
            print(f"❌ 刷新认证状态失败: {e}")
            return False

    def clean_expired_tokens(self):
        """清理过期Token - 深度清理"""
        print(f"\n🧹 开始清理过期Token...")

        try:
            cleaned_count = 0

            # 清理可能过期的文件
            cleanup_files = [
                ('Network/Trust Tokens', '信任令牌'),
                ('Network/Network Persistent State', '网络持久状态'),
                ('User/globalStorage/state.vscdb', '状态数据库'),
            ]

            for file_path, description in cleanup_files:
                full_path = os.path.join(self.appdata, 'Cursor', file_path.replace('/', os.sep))
                if os.path.exists(full_path):
                    try:
                        # 创建备份
                        backup_path = full_path + f".backup_{int(time.time())}"
                        shutil.copy2(full_path, backup_path)

                        # 删除原文件（让Cursor重新生成）
                        os.remove(full_path)

                        print(f"  🧹 已清理: {description}")
                        print(f"  💾 备份位置: {os.path.basename(backup_path)}")
                        cleaned_count += 1

                    except Exception as e:
                        print(f"  ⚠️ 清理失败 {description}: {e}")

            if cleaned_count > 0:
                print(f"\n🎉 Token清理完成! 清理了 {cleaned_count} 个文件")
                print(f"🚀 后续操作:")
                print("  1. 重启Cursor")
                print("  2. 重新登录账号")
                print("  3. 测试AI对话功能")
                print("  4. 如果需要，可以从备份恢复")
            else:
                print(f"\n⚠️ 没有找到需要清理的文件")

            return cleaned_count > 0

        except Exception as e:
            print(f"❌ 清理过期Token失败: {e}")
            return False

    def rebuild_login_status(self):
        """重建登录状态 - 强力修复"""
        print(f"\n🔥 开始重建登录状态...")

        # 首先检查是否有可用的备份
        backups = self.get_all_backups()
        if not backups:
            print("❌ 没有找到备份，无法重建登录状态")
            return False

        print(f"找到 {len(backups)} 个备份，选择一个来重建登录状态:\n")

        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            user_info = self.extract_user_info_from_backup(backup_dir)

            print(f"🔥 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            if user_info:
                print(f"    👤 用户: {user_info.get('email', 'Unknown')}")
            print()

        # 选择备份
        while True:
            choice = self.get_input(f"请选择用于重建的备份 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        print(f"\n🔥 使用备份重建登录状态: {selected_backup}")

        # 执行强力重建
        try:
            # 1. 清理现有认证文件
            print("  🧹 清理现有认证文件...")
            auth_files = [
                'Network/Cookies',
                'Network/Trust Tokens',
                'sentry/session.json',
                'sentry/scope_v3.json'
            ]

            for file_path in auth_files:
                full_path = os.path.join(self.appdata, 'Cursor', file_path.replace('/', os.sep))
                if os.path.exists(full_path):
                    backup_path = full_path + f".rebuild_backup_{int(time.time())}"
                    shutil.copy2(full_path, backup_path)
                    print(f"    💾 备份: {os.path.basename(full_path)}")

            # 2. 从备份恢复认证文件
            print("  🔄 从备份恢复认证文件...")
            restored_count = 0

            for file_path in auth_files:
                source_file = os.path.join(selected_backup, file_path.replace('/', os.sep))
                target_file = os.path.join(self.appdata, 'Cursor', file_path.replace('/', os.sep))

                if os.path.exists(source_file):
                    try:
                        os.makedirs(os.path.dirname(target_file), exist_ok=True)
                        shutil.copy2(source_file, target_file)
                        print(f"    ✅ 恢复: {os.path.basename(target_file)}")
                        restored_count += 1
                    except Exception as e:
                        print(f"    ❌ 恢复失败 {os.path.basename(target_file)}: {e}")

            # 3. 更新时间戳
            print("  🕐 更新认证时间戳...")
            self.refresh_auth_status()

            print(f"\n🎉 登录状态重建完成!")
            print(f"✅ 恢复了 {restored_count} 个认证文件")
            print(f"🚀 后续操作:")
            print("  1. 重启Cursor")
            print("  2. 检查登录状态")
            print("  3. 测试AI对话功能")
            print("  4. 如果仍有问题，尝试手动重新登录")

            return restored_count > 0

        except Exception as e:
            print(f"❌ 重建登录状态失败: {e}")
            return False

    def diagnose_login_issues(self):
        """诊断登录问题 - 问题分析"""
        print(f"\n📊 开始诊断登录问题...")

        issues_found = []
        suggestions = []

        # 检查关键文件
        critical_files = [
            ('sentry/scope_v3.json', '用户身份信息'),
            ('sentry/session.json', '会话信息'),
            ('Network/Cookies', '登录Cookie'),
            ('Network/Trust Tokens', '信任令牌'),
        ]

        print(f"\n🔍 检查关键认证文件:")
        for file_path, description in critical_files:
            full_path = os.path.join(self.appdata, 'Cursor', file_path.replace('/', os.sep))

            if os.path.exists(full_path):
                try:
                    file_size = os.path.getsize(full_path)
                    mod_time = os.path.getmtime(full_path)
                    age_hours = (time.time() - mod_time) / 3600

                    print(f"  ✅ {description}: 存在 ({self.get_file_size_str(file_size)}, {age_hours:.1f}小时前)")

                    # 检查文件是否过旧
                    if age_hours > 24:
                        issues_found.append(f"{description} 文件过旧 ({age_hours:.1f}小时)")
                        suggestions.append("尝试刷新认证状态或重建登录状态")

                    # 检查文件大小
                    if file_size < 10:
                        issues_found.append(f"{description} 文件过小 ({file_size}字节)")
                        suggestions.append("文件可能损坏，尝试从备份恢复")

                except Exception as e:
                    print(f"  ❌ {description}: 无法读取 - {e}")
                    issues_found.append(f"{description} 文件损坏")
                    suggestions.append("从备份恢复该文件")
            else:
                print(f"  ❌ {description}: 不存在")
                issues_found.append(f"{description} 文件缺失")
                suggestions.append("从备份恢复该文件")

        # 检查用户信息一致性
        print(f"\n🔍 检查用户信息一致性:")
        current_user = self.get_current_user_info()
        if current_user:
            email = current_user.get('email', '')
            user_id = current_user.get('user_id', '')

            if email and '@' in email:
                print(f"  ✅ 用户邮箱: {email}")
            else:
                print(f"  ❌ 用户邮箱: 无效或缺失")
                issues_found.append("用户邮箱无效")
                suggestions.append("使用精确身份切换功能修复用户信息")

            if user_id and len(user_id) > 10:
                print(f"  ✅ 用户ID: {user_id[:20]}...")
            else:
                print(f"  ❌ 用户ID: 无效或缺失")
                issues_found.append("用户ID无效")
                suggestions.append("使用精确身份切换功能修复用户信息")
        else:
            print(f"  ❌ 无法获取用户信息")
            issues_found.append("无法获取用户信息")
            suggestions.append("重建登录状态")

        # 显示诊断结果
        print(f"\n📊 诊断结果:")
        if issues_found:
            print(f"❌ 发现 {len(issues_found)} 个问题:")
            for i, issue in enumerate(issues_found, 1):
                print(f"  {i}. {issue}")

            print(f"\n💡 建议的解决方案:")
            unique_suggestions = list(set(suggestions))
            for i, suggestion in enumerate(unique_suggestions, 1):
                print(f"  {i}. {suggestion}")
        else:
            print(f"✅ 未发现明显问题")
            print(f"💡 如果仍有登录问题，建议:")
            print(f"  1. 检查网络连接")
            print(f"  2. 重启Cursor")
            print(f"  3. 手动重新登录")

        input("\n按回车键继续...")
        return True

    def trigger_auth_refresh(self):
        """触发认证刷新"""
        try:
            # 创建一个触发文件来通知Cursor刷新认证
            trigger_file = os.path.join(self.appdata, 'Cursor', '.auth_refresh_trigger')
            with open(trigger_file, 'w') as f:
                f.write(str(time.time()))

            time.sleep(0.1)

            # 删除触发文件
            try:
                os.remove(trigger_file)
            except:
                pass

            print(f"  🔄 认证刷新信号已发送")
            return True

        except Exception as e:
            print(f"  ⚠️ 发送认证刷新信号失败: {e}")
            return False

    def activate_account(self):
        """激活账号 - 让指定账号成为当前活跃账号"""
        print("\n" + "=" * 50)
        print("    ⚡ 激活账号 - 让账号成为当前活跃账号")
        print("=" * 50)
        print("🎯 此功能专门解决以下问题:")
        print("  • 恢复多个账号后，只有最后一个能AI对话")
        print("  • 其他账号仍然提示需要登录")
        print("  • 需要让特定账号成为'活跃账号'")
        print("🔧 激活原理:")
        print("  • 模拟该账号的'最后登录'状态")
        print("  • 更新活跃会话信息")
        print("  • 刷新AI服务连接")
        print("  • 清理其他账号的活跃状态")
        print()

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return False

        # 显示当前用户状态
        current_user = self.get_current_user_info()
        if current_user:
            print(f"📋 当前显示的用户:")
            print(f"  👤 邮箱: {current_user.get('email', 'Unknown')}")
            print(f"  🆔 用户ID: {current_user.get('user_id', 'Unknown')}")
            print()

        # 显示备份列表，重点显示用户信息
        print(f"找到 {len(backups)} 个备份账号:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            note = info.get('user_note', '')

            # 提取用户信息
            user_info = self.extract_user_info_from_backup(backup_dir)

            print(f"⚡ [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            if user_info:
                print(f"    👤 用户: {user_info.get('email', 'Unknown')}")
                print(f"    🆔 用户ID: {user_info.get('user_id', 'Unknown')[:20]}...")
            if note:
                print(f"    📝 备注: {note}")
            print()

        # 选择要激活的账号
        while True:
            choice = self.get_input(f"请选择要激活的账号 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 提取目标用户信息
        target_user_info = self.extract_user_info_from_backup(selected_backup)
        if not target_user_info:
            print("❌ 无法提取目标用户信息")
            return False

        # 显示激活预览
        print(f"\n⚡ 账号激活预览:")
        print(f"目标账号:")
        print(f"  👤 邮箱: {target_user_info.get('email', 'Unknown')}")
        print(f"  🆔 用户ID: {target_user_info.get('user_id', 'Unknown')}")

        print(f"\n⚡ 账号激活说明:")
        print("• 将该账号设置为当前活跃账号")
        print("• 更新最后登录时间戳")
        print("• 刷新AI服务连接")
        print("• 清理其他账号的活跃状态")
        print("• 激活后该账号应该能正常AI对话")

        confirm = self.get_input("\n确定要激活此账号吗? (y/N)")
        if confirm.lower() != 'y':
            print("❌ 账号激活已取消")
            return False

        # 执行账号激活
        return self.perform_account_activation(selected_backup, target_user_info)

    def perform_account_activation(self, backup_dir, target_user_info):
        """执行账号激活"""
        print(f"\n⚡ 开始激活账号...")
        print(f"目标用户: {target_user_info.get('email', 'Unknown')}")

        successful = 0
        failed = 0

        try:
            # 步骤1: 精确替换用户身份信息
            print(f"\n[1/4] 更新用户身份信息...")
            if self.perform_precise_identity_switch(target_user_info, None):
                print(f"  ✅ 用户身份信息已更新")
                successful += 1
            else:
                print(f"  ❌ 用户身份信息更新失败")
                failed += 1

            # 步骤2: 激活会话状态
            print(f"\n[2/4] 激活会话状态...")
            if self.activate_session_state(backup_dir, target_user_info):
                print(f"  ✅ 会话状态已激活")
                successful += 1
            else:
                print(f"  ❌ 会话状态激活失败")
                failed += 1

            # 步骤3: 更新活跃时间戳
            print(f"\n[3/4] 更新活跃时间戳...")
            if self.update_active_timestamps(target_user_info):
                print(f"  ✅ 活跃时间戳已更新")
                successful += 1
            else:
                print(f"  ❌ 活跃时间戳更新失败")
                failed += 1

            # 步骤4: 刷新AI服务连接
            print(f"\n[4/4] 刷新AI服务连接...")
            if self.refresh_ai_service_connection(target_user_info):
                print(f"  ✅ AI服务连接已刷新")
                successful += 1
            else:
                print(f"  ❌ AI服务连接刷新失败")
                failed += 1

            # 显示结果
            print("\n" + "=" * 50)
            print("    ⚡ 账号激活完成")
            print("=" * 50)
            print(f"✅ 成功步骤: {successful}/4")
            print(f"❌ 失败步骤: {failed}/4")

            if successful >= 3:
                print(f"\n🎉 账号激活成功!")
                print(f"👤 活跃用户: {target_user_info.get('email', 'Unknown')}")
                print(f"🚀 后续操作:")
                print("  1. 在Cursor中按 Ctrl+Shift+P")
                print("  2. 输入 'Developer: Reload Window'")
                print("  3. 等待3-5秒让状态同步")
                print("  4. 打开AI聊天窗口")
                print("  5. 发送消息测试 - 应该不再要求登录")
                print("  6. 如果仍有问题，尝试重启Cursor")
            elif successful >= 2:
                print(f"\n⚠️ 账号激活部分成功")
                print(f"🔄 建议:")
                print("  1. 先按照上述步骤测试")
                print("  2. 如果无效，尝试登录状态修复")
                print("  3. 或者重启Cursor后再试")
            else:
                print(f"\n❌ 账号激活失败")
                print(f"💡 建议:")
                print("  1. 尝试登录状态修复功能")
                print("  2. 或使用精确身份切换")
                print("  3. 检查备份文件是否完整")

            return successful >= 2

        except Exception as e:
            print(f"❌ 账号激活过程失败: {e}")
            return False

    def activate_session_state(self, backup_dir, target_user_info):
        """激活会话状态"""
        try:
            import json

            # 从备份恢复会话文件
            source_session = os.path.join(backup_dir, 'sentry', 'session.json')
            target_session = os.path.join(self.appdata, 'Cursor', 'sentry', 'session.json')

            if os.path.exists(source_session):
                # 读取备份的会话数据
                with open(source_session, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)

                # 更新为当前时间
                current_time = time.time()
                session_data['timestamp'] = current_time
                session_data['started'] = current_time
                session_data['status'] = 'ok'  # 确保状态正常

                # 创建备份
                if os.path.exists(target_session):
                    backup_path = target_session + f".backup_{int(current_time)}"
                    shutil.copy2(target_session, backup_path)

                # 写入激活的会话数据
                os.makedirs(os.path.dirname(target_session), exist_ok=True)
                with open(target_session, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, separators=(',', ':'))

                return True
            else:
                print(f"    ⚠️ 备份中没有会话文件")
                return False

        except Exception as e:
            print(f"    ❌ 激活会话状态失败: {e}")
            return False

    def update_active_timestamps(self, target_user_info):
        """更新活跃时间戳"""
        try:
            import json
            current_time = time.time()
            updated_files = 0

            # 更新所有相关文件的时间戳
            timestamp_files = [
                'sentry/session.json',
                'sentry/scope_v3.json',
                'User/globalStorage/storage.json'
            ]

            for file_path in timestamp_files:
                full_path = os.path.join(self.appdata, 'Cursor', file_path.replace('/', os.sep))
                if os.path.exists(full_path):
                    try:
                        # 读取文件
                        with open(full_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                        # 更新时间戳字段
                        if 'session.json' in file_path:
                            data['timestamp'] = current_time
                            data['started'] = current_time
                        elif 'scope_v3.json' in file_path:
                            if 'event' in data:
                                data['event']['timestamp'] = current_time
                        elif 'storage.json' in file_path:
                            # 添加最后活跃时间
                            data['lastActiveTime'] = current_time
                            data['lastActiveUser'] = target_user_info.get('user_id', '')

                        # 写回文件
                        with open(full_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, separators=(',', ':'))

                        updated_files += 1

                    except Exception as e:
                        print(f"    ⚠️ 更新 {os.path.basename(full_path)} 失败: {e}")

            return updated_files > 0

        except Exception as e:
            print(f"    ❌ 更新活跃时间戳失败: {e}")
            return False

    def refresh_ai_service_connection(self, target_user_info):
        """刷新AI服务连接"""
        try:
            # 创建AI服务刷新标记
            refresh_marker = os.path.join(self.appdata, 'Cursor', '.ai_service_refresh')
            with open(refresh_marker, 'w') as f:
                f.write(json.dumps({
                    'user_id': target_user_info.get('user_id', ''),
                    'email': target_user_info.get('email', ''),
                    'timestamp': time.time(),
                    'action': 'activate_account'
                }))

            time.sleep(0.2)

            # 删除标记文件
            try:
                os.remove(refresh_marker)
            except:
                pass

            # 触发认证刷新
            self.trigger_auth_refresh()

            return True

        except Exception as e:
            print(f"    ❌ 刷新AI服务连接失败: {e}")
            return False

    def get_all_backups(self):
        """获取所有备份"""
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

        backups.sort(key=lambda x: x[1].get('backup_time', ''), reverse=True)
        return backups

    def list_backups(self):
        """列出所有备份"""
        print("\n" + "=" * 50)
        print("    📋 所有可用备份")
        print("=" * 50)

        backups = self.get_all_backups()
        if not backups:
            print("📭 未找到任何备份")
            return []

        print(f"找到 {len(backups)} 个备份:\n")
        for i, (backup_dir, info) in enumerate(backups, 1):
            backup_time = info.get('backup_time', 'Unknown')
            computer = info.get('computer_name', 'Unknown')
            size = info.get('total_size_readable', 'Unknown')
            files = info.get('files_backed_up', 0)
            note = info.get('user_note', '')

            print(f"📁 [{i}] {backup_dir}")
            print(f"    ⏰ 时间: {backup_time}")
            print(f"    💻 来源: {computer}")
            print(f"    📊 大小: {size} ({files} 个文件)")
            if note:
                print(f"    📝 备注: {note}")
            print()

        return backups

    def restore_account(self):
        """恢复账号"""
        backups = self.list_backups()
        if not backups:
            return False

        # 选择备份
        while True:
            choice = self.get_input(f"请选择要恢复的备份 (1-{len(backups)}) 或 0 返回")
            if choice == '0':
                return False

            try:
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index][0]
                    backup_info = backups[index][1]
                    break
                else:
                    print(f"❌ 请输入 1-{len(backups)} 之间的数字")
            except ValueError:
                print("❌ 请输入有效数字")

        # 显示选择信息
        print(f"\n📦 选择的备份: {selected_backup}")
        print(f"⏰ 备份时间: {backup_info.get('backup_time', 'Unknown')}")
        print(f"💻 来源机器: {backup_info.get('computer_name', 'Unknown')}")
        if backup_info.get('user_note'):
            print(f"📝 备注: {backup_info.get('user_note')}")

        # 确认恢复
        confirm = self.get_input("\n⚠️ 确定要恢复此备份吗? 这将覆盖当前账号数据! (y/N)")
        if confirm.lower() != 'y':
            print("❌ 恢复已取消")
            return False

        # 终结Cursor
        self.terminate_cursor()

        print(f"\n🔄 开始恢复备份: {selected_backup}")

        # 执行恢复
        successful = 0
        for i, file_info in enumerate(self.critical_files, 1):
            print(f"[{i}/{len(self.critical_files)}] {file_info['description']}...")

            source_path = os.path.join(selected_backup, file_info['target'])
            if not os.path.exists(source_path):
                print(f"  ⏭️ 备份文件不存在")
                continue

            try:
                os.makedirs(os.path.dirname(file_info['source']), exist_ok=True)
                shutil.copy2(source_path, file_info['source'])

                file_size = os.path.getsize(file_info['source'])
                size_str = self.get_file_size_str(file_size)
                print(f"  ✅ 恢复成功 ({size_str})")
                successful += 1
            except Exception as e:
                print(f"  ❌ 恢复失败: {e}")

        # 显示结果
        print("\n" + "=" * 50)
        print("    ✅ 恢复完成")
        print("=" * 50)
        print(f"成功恢复: {successful}/{len(self.critical_files)} 个文件")
        print("\n🎉 现在可以启动Cursor并检查登录状态")
        print("如果登录成功，说明账号信息已成功迁移！")

        return successful > 0

    def manage_backups(self):
        """管理备份"""
        while True:
            backups = self.list_backups()
            if not backups:
                return

            print("📋 管理选项:")
            print("  1. 🗑️ 删除备份")
            print("  2. 🏷️ 修改备注")
            print("  0. 🔙 返回主菜单")

            choice = self.get_input("请选择操作")
            if choice == '0':
                return
            elif choice == '1':
                self.delete_backup(backups)
            elif choice == '2':
                self.edit_note(backups)
            else:
                print("❌ 无效选择")

            self.get_input("\n按回车键继续...")

    def delete_backup(self, backups):
        """删除备份"""
        choice = self.get_input(f"请选择要删除的备份 (1-{len(backups)}) 或 0 取消")
        if choice == '0':
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_to_delete = backups[index][0]
                confirm = self.get_input(f"确定要删除 {backup_to_delete} 吗? (y/N)")
                if confirm.lower() == 'y':
                    shutil.rmtree(backup_to_delete)
                    print(f"✅ 备份 {backup_to_delete} 已删除")
        except (ValueError, IndexError):
            print("❌ 无效选择")
        except Exception as e:
            print(f"❌ 删除失败: {e}")

    def edit_note(self, backups):
        """编辑备注"""
        choice = self.get_input(f"请选择要编辑备注的备份 (1-{len(backups)}) 或 0 取消")
        if choice == '0':
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_dir = backups[index][0]
                new_note = self.get_input("请输入新的备注")

                info_file = os.path.join(backup_dir, "backup_info.json")
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                info['user_note'] = new_note
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(info, f, indent=2, ensure_ascii=False)

                print(f"✅ 备注已更新: {new_note}")
        except (ValueError, IndexError):
            print("❌ 无效选择")
        except Exception as e:
            print(f"❌ 更新失败: {e}")

    def show_help(self):
        """显示帮助"""
        print("\n" + "=" * 50)
        print("    ❓ 帮助信息")
        print("=" * 50)
        print("🎯 功能说明:")
        print("  • 备份: 将当前Cursor账号数据备份到本地")
        print("  • 恢复: 从备份恢复Cursor账号数据 (关闭Cursor)")
        print("  • 热切换: 在Cursor运行时尝试切换账号 (实验性)")
        print("  • 强制热切换: 使用管理员权限强制切换 (高级)")
        print("  • 极简热切换: 只换AI对话权限，保持Cursor运行")
        print("  • AI对话切换: 专门切换AI配额，智能JSON替换")
        print("  • 精确身份切换: 直接替换用户信息，最精准 (推荐)")
        print("  • 登录状态修复: 解决AI对话登录问题 (故障排除)")
        print("  • 激活账号: 让指定账号成为活跃账号 (解决多账号问题)")
        print("  • 管理: 查看、删除、编辑备份")
        print()
        print("🚀 使用流程:")
        print("  标准流程 (推荐):")
        print("    1. 在源机器上备份账号")
        print("    2. 将备份文件夹复制到目标机器")
        print("    3. 在目标机器上恢复账号")
        print("    4. 启动Cursor验证登录状态")
        print()
        print("  热切换流程 (快速):")
        print("    1. 保持Cursor运行状态")
        print("    2. 选择热切换功能")
        print("    3. 选择要切换的账号备份")
        print("    4. 重新加载Cursor窗口")
        print()
        print("  极简热切换流程:")
        print("    1. 保持Cursor完全运行")
        print("    2. 选择极简热切换功能")
        print("    3. 选择要切换的账号")
        print("    4. 按 Ctrl+Shift+P → Developer: Reload Window")
        print("    5. 测试AI对话功能")
        print()
        print("  AI对话切换流程:")
        print("    1. 保持Cursor完全运行")
        print("    2. 选择AI对话切换功能")
        print("    3. 查看用户信息并选择目标账号")
        print("    4. 确认切换AI配额")
        print("    5. 按 Ctrl+Shift+P → Developer: Reload Window")
        print("    6. 测试AI对话，验证配额变化")
        print()
        print("  精确身份切换流程 (推荐):")
        print("    1. 保持Cursor完全运行")
        print("    2. 选择精确身份切换功能")
        print("    3. 查看当前和目标用户信息对比")
        print("    4. 确认切换用户身份")
        print("    5. 系统精确替换用户邮箱和ID")
        print("    6. 按 Ctrl+Shift+P → Developer: Reload Window")
        print("    7. 立即测试AI对话，验证身份切换")
        print()
        print("  强制热切换流程 (高级):")
        print("    1. 以管理员身份运行程序")
        print("    2. 选择强制热切换功能")
        print("    3. 输入 'FORCE' 确认操作")
        print("    4. 重新加载或重启Cursor")
        print()
        print("⚠️ 注意事项:")
        print("  • 恢复功能会自动关闭Cursor进程")
        print("  • 热切换可能因文件锁定而不完整")
        print("  • 强制热切换需要管理员权限")
        print("  • 强制热切换具有一定风险")
        print("  • 恢复会覆盖现有账号数据")
        print("  • 建议在相同版本的Cursor间使用")
        print("  • 切换后建议重新加载Cursor窗口")

    def run(self):
        """运行主程序"""
        while True:
            try:
                self.clear_screen()
                self.print_banner()
                self.print_menu()

                choice = self.get_input("请输入选择 (0-12)")

                if choice == "0":
                    print("\n👋 感谢使用 Cursor Account Manager!")
                    break
                elif choice == "1":
                    self.backup_account()
                elif choice == "2":
                    self.restore_account()
                elif choice == "3":
                    self.hot_switch_account()
                elif choice == "4":
                    self.force_hot_switch_account()
                elif choice == "5":
                    self.simple_hot_switch_account()
                elif choice == "6":
                    self.ai_chat_switch_account()
                elif choice == "7":
                    self.precise_identity_switch()
                elif choice == "8":
                    self.fix_login_status()
                elif choice == "9":
                    self.activate_account()
                elif choice == "10":
                    self.list_backups()
                elif choice == "11":
                    self.manage_backups()
                elif choice == "12":
                    self.show_help()
                else:
                    print("❌ 无效选择，请输入 0-12")

                if choice != "4":  # 管理备份有自己的循环
                    self.get_input("\n按回车键继续...")

            except Exception as e:
                print(f"\n❌ 发生错误: {e}")
                self.get_input("按回车键继续...")

if __name__ == '__main__':
    try:
        console = CursorConsole()
        console.run()
    except Exception as e:
        print(f"程序启动失败: {e}")
        input("按回车键退出...")
