"""
技能热加载模块
支持运行时动态添加、移除和更新技能
"""
import importlib
import sys
import logging
from pathlib import Path
from typing import Optional, Callable
from threading import Thread, Event

logger = logging.getLogger(__name__)


class SkillHotReloader:
    """技能热加载管理器"""

    def __init__(self, registry, skills_dir: str = None):
        """
        初始化热加载管理器

        Args:
            registry: 技能注册中心实例
            skills_dir: 技能目录路径
        """
        self.registry = registry
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self._watcher = None
        self._stop_event = Event()
        self._on_reload_callback: Optional[Callable] = None

    def start_watch(self, skills_dir: str = None):
        """
        启动文件监听

        Args:
            skills_dir: 技能目录路径
        """
        if skills_dir:
            self.skills_dir = Path(skills_dir)

        if not self.skills_dir or not self.skills_dir.exists():
            logger.warning(f"技能目录不存在，无法启动热加载监听")
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent

            class SkillFileHandler(FileSystemEventHandler):
                """技能文件变更处理器"""

                def __init__(self, reloader: 'SkillHotReloader'):
                    self.reloader = reloader

                def on_modified(self, event: FileSystemEvent):
                    if event.src_path.endswith('.py') and not event.src_path.endswith('__init__.py'):
                        logger.info(f"检测到文件变更: {event.src_path}")
                        self.reloader._reload_skill_by_path(event.src_path)

                def on_created(self, event: FileSystemEvent):
                    if event.src_path.endswith('.py') and not event.src_path.endswith('__init__.py'):
                        logger.info(f"检测到新文件: {event.src_path}")
                        self.reloader._load_skill_by_path(event.src_path)

            self._handler = SkillFileHandler(self)
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(self.skills_dir),
                recursive=False
            )
            self._observer.start()
            logger.info(f"已启动技能热加载监听: {self.skills_dir}")

        except ImportError:
            logger.warning("未安装 watchdog 库，热加载功能将使用轮询模式")
            self._start_polling()

    def _start_polling(self):
        """启动轮询模式（当 watchdog 不可用时）"""
        def poll_loop():
            while not self._stop_event.is_set():
                try:
                    self._check_changes()
                except Exception as e:
                    logger.error(f"轮询检查出错: {e}")
                self._stop_event.wait(5)  # 每5秒检查一次

        self._poll_thread = Thread(target=poll_loop, daemon=True)
        self._poll_thread.start()
        logger.info("已启动技能热加载轮询模式")

    def _check_changes(self):
        """检查文件变更"""
        if not self.skills_dir:
            return

        for py_file in self.skills_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            # 简单实现：这里可以添加更复杂的变更检测逻辑
            pass

    def stop_watch(self):
        """停止文件监听"""
        self._stop_event.set()

        if hasattr(self, '_observer') and self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("已停止技能热加载监听")

    def reload_skill(self, skill_name: str) -> bool:
        """
        重新加载指定技能

        Args:
            skill_name: 技能名称

        Returns:
            重载是否成功
        """
        try:
            # 1. 注销旧技能
            self.registry.unregister(skill_name)

            # 2. 查找对应的模块
            module_name = f"skills.implementations.{skill_name}"
            if module_name in sys.modules:
                # 重新加载模块
                importlib.reload(sys.modules[module_name])
                logger.info(f"已重新加载模块: {module_name}")
            else:
                # 导入新模块
                importlib.import_module(module_name)

            # 3. 自动发现并注册
            self.registry.auto_discover()

            logger.info(f"成功重载技能: {skill_name}")
            return True

        except Exception as e:
            logger.error(f"重载技能失败: {skill_name}, 错误: {e}")
            return False

    def _reload_skill_by_path(self, file_path: str):
        """根据文件路径重载技能"""
        path = Path(file_path)
        module_name = f"skills.implementations.{path.stem}"

        try:
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
            else:
                importlib.import_module(module_name)

            # 重新注册
            self.registry.auto_discover()

            if self._on_reload_callback:
                self._on_reload_callback(path.stem)

        except Exception as e:
            logger.error(f"重载技能失败: {file_path}, 错误: {e}")

    def _load_skill_by_path(self, file_path: str):
        """根据文件路径加载新技能"""
        path = Path(file_path)
        module_name = f"skills.implementations.{path.stem}"

        try:
            importlib.import_module(module_name)
            self.registry.auto_discover()

            logger.info(f"成功加载新技能: {path.stem}")

            if self._on_reload_callback:
                self._on_reload_callback(path.stem)

        except Exception as e:
            logger.error(f"加载技能失败: {file_path}, 错误: {e}")

    def add_skill_from_file(self, file_path: str) -> bool:
        """
        从文件动态添加技能

        Args:
            file_path: 技能文件路径

        Returns:
            添加是否成功
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False

            # 复制文件到技能目录
            if self.skills_dir:
                target_path = self.skills_dir / path.name
                import shutil
                shutil.copy2(path, target_path)

                # 加载新技能
                self._load_skill_by_path(str(target_path))
                return True

            return False

        except Exception as e:
            logger.error(f"添加技能失败: {file_path}, 错误: {e}")
            return False

    def remove_skill(self, skill_name: str) -> bool:
        """
        动态移除技能

        Args:
            skill_name: 技能名称

        Returns:
            移除是否成功
        """
        try:
            # 1. 从注册中心注销
            success = self.registry.unregister(skill_name)

            # 2. 移除模块引用
            module_name = f"skills.implementations.{skill_name}"
            if module_name in sys.modules:
                del sys.modules[module_name]

            logger.info(f"成功移除技能: {skill_name}")
            return success

        except Exception as e:
            logger.error(f"移除技能失败: {skill_name}, 错误: {e}")
            return False

    def set_reload_callback(self, callback: Callable):
        """设置重载回调函数"""
        self._on_reload_callback = callback


# 全局热加载管理器实例
hot_reloader: Optional[SkillHotReloader] = None


def init_hot_reloader(registry, skills_dir: str = None) -> SkillHotReloader:
    """初始化全局热加载管理器"""
    global hot_reloader
    hot_reloader = SkillHotReloader(registry, skills_dir)
    return hot_reloader


def get_hot_reloader() -> Optional[SkillHotReloader]:
    """获取全局热加载管理器"""
    return hot_reloader
