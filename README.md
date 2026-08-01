# ABBpainting

G-code → ABB RobotStudio RAPID 转换工具(版本 1.2)

从 `ABBpainting.exe`(PyInstaller 打包, Python 3.10 + Tkinter)反编译还原的源码。

## 功能

- 弹窗输入工件四角 Z 轴值(**四点调零**,可跳过)
- 选择 `.gcode` / `.txt` 文件
- 逐行解析 G-code 中的 X/Y/Z 坐标:
  - X + 105、Y + 148 换算为机器人坐标
  - 四点调零算法(双线性插值 `Zero()`)计算 Z 轴倾斜补偿
- 输出 ABB RobotStudio 的 `MoveL Offs(DW, ...)` 指令到桌面 `output.mod`

## 运行

```bash
python ABBpainting.py
```

依赖:Python 3.10+, 仅标准库(re / os / tkinter)。

## 打包 exe(Windows)

```bash
pip install pyinstaller
pyinstaller -F -w --name ABBpainting ABBpainting.py
```

## 已知问题

读取 G-code 行时先判断 X/Y 再判断 Z——带 Z 的行走行会输出两条 `MoveL`
(一条用插值 Z,一条用 G-code 的 Z)。若 G-code 每行都带 Z,插值结果会被覆盖,
但会残留多余的移动指令。可能是设计如此,也可能是 bug,使用前请自行确认输出。
