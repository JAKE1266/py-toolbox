"""GUI 线程安全回归测试。

GUI 的实际执行在后台线程,但所有 Tk 控件(StringVar / Text 等)只能在主线程读取。
本测试验证 :meth:`ToolBoxApp._run_button` 的 ``before`` 回调在点击时(主线程)
同步取值,并把结果原样交给后台任务函数,从而杜绝跨线程访问控件。
"""

import unittest

try:
    import tkinter as tk
except ImportError:  # 某些无头环境未编译 Tk
    tk = None

from pytoolbox.gui import ToolBoxApp


@unittest.skipIf(tk is None, "当前 Python 未附带 Tkinter")
class GuiThreadSafetyTest(unittest.TestCase):
    def setUp(self):
        self.app = ToolBoxApp()
        self.app.withdraw()  # 不显示窗口,避免测试环境弹窗
        self.addCleanup(self.app.destroy)

    def test_before_captured_value_passed_to_task(self):
        """before() 的返回值应作为唯一参数传给后台任务函数。"""
        frame = tk.Frame(self.app)
        dn = tk.StringVar(value="hello")

        captured = {}

        def task(value):
            captured["value"] = value
            return value.upper()

        btn = self.app._run_button(frame, task, before=lambda: dn.get())

        # 直接调用按钮 command,即 start():它应在主线程执行 before()
        # 然后启动线程执行 task(value)。等待完成。
        btn.invoke()
        deadline = 5.0
        import time
        t0 = time.time()
        while "value" not in captured and time.time() - t0 < deadline:
            self.app.update()
            time.sleep(0.01)

        self.assertEqual(captured.get("value"), "hello")

    def test_task_sees_snapshot_not_variable(self):
        """即使点击后立刻改动变量,后台任务拿到的仍是点击瞬间的值。"""
        frame = tk.Frame(self.app)
        dn = tk.StringVar(value="first")
        captured = {}

        def task(value):
            captured["value"] = value
            return value

        btn = self.app._run_button(frame, task, before=lambda: dn.get())
        btn.invoke()
        dn.set("second")  # 点击后立刻改动
        deadline = 5.0
        import time
        t0 = time.time()
        while "value" not in captured and time.time() - t0 < deadline:
            self.app.update()
            time.sleep(0.01)

        self.assertEqual(captured.get("value"), "first")


if __name__ == "__main__":
    unittest.main()
