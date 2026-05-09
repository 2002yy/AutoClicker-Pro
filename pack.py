import os
import sys
import subprocess

# ================= 配置区域 =================
# 这里填你的源文件名 (必须带 .py)
SOURCE_FILE = "autoclicker.py"
# 这里填你想生成的 exe 名字
EXE_NAME = "AutoClickerPro"
# ===========================================


def install_deps():
    """检查并自动安装必要的打包库"""
    print("正在检查环境...")
    required = ["pyinstaller", "customtkinter", "pynput"]
    for package in required:
        try:
            __import__(package)
        except ImportError:
            print(f"正在安装缺失的库: {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def build():
    # 0. 检查源文件
    if not os.path.exists(SOURCE_FILE):
        print(f"\n❌ 错误：找不到文件 [{SOURCE_FILE}]")
        print(
            "请确认：\n1. 你的源文件名真的是 'autoclicker.py' 吗？\n2. 此脚本是否和源文件在同一个文件夹里？"
        )
        return

    import PyInstaller.__main__
    import customtkinter

    # 1. 获取 CustomTkinter 的资源路径 (关键步骤)
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"✅ 找到 UI 库路径: {ctk_path}")

    # 2. 组装 PyInstaller 参数
    # 注意：Windows下资源分隔符是分号 ;
    add_data_arg = f"{ctk_path};customtkinter"

    args = [
        SOURCE_FILE,  # 源文件
        f"--name={EXE_NAME}",  # exe名字
        "--noconfirm",  # 覆盖输出不询问
        "--onefile",  # 打包成单文件 exe
        "--windowed",  # 【重要】不显示黑色的控制台窗口
        "--clean",  # 清理临时缓存
        f"--add-data={add_data_arg}",  # 注入 customtkinter 资源
    ]

    # 如果你有图标，把图标放在同级目录叫 icon.ico，然后取消下面这行的注释
    # if os.path.exists("icon.ico"): args.append('--icon=icon.ico')

    print(f"\n🚀 开始打包 [{SOURCE_FILE}] ...")
    print("这可能需要 1-3 分钟，请耐心等待...\n")

    # 3. 执行打包
    try:
        PyInstaller.__main__.run(args)
        print("\n" + "=" * 40)
        print(f"🎉 打包成功！")
        print(f"请在生成的 [dist] 文件夹里找：{EXE_NAME}.exe")
        print("=" * 40)
    except Exception as e:
        print(f"\n❌ 打包出错: {e}")


if __name__ == "__main__":
    try:
        install_deps()
        build()
    except Exception as e:
        print(f"发生未知错误: {e}")

    input("\n按回车键退出...")
