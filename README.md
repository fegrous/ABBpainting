# ABBpainting

**把二维绘图软件的 G-code 转换成 ABB 工业机器人的 RAPID 程序，让机器人代替手去"画画"。**

[![Release](https://img.shields.io/badge/release-v1.2.0-blue)](https://github.com/fegrous/ABBpainting/releases/latest)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)](#下载)
[![Python](https://img.shields.io/badge/python-3.10-3776ab)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> 输入 `.gcode` → 输出 RobotStudio 可直接导入的 `output.mod`，
> 并支持**四点调零**：在工件四角各测一个 Z 值，自动补偿板面不平整带来的高度误差。

---

## 这个项目解决什么问题

把一张二次元线稿交给机器人画出来，中间隔着一大堆不兼容的格式：

```
图片(PNG)  ──描摹/矢量化──▶  矢量路径  ──导出──▶  G-code  ──ABBpainting──▶  RAPID(.mod)
  ↑                                                  ↑                        ↑
线稿素材                                    Inkscape / 雕刻软件          ABB RobotStudio
```

最大的坑在最后一步：**G-code 只认 XY 平面坐标，而真实工件从来不是绝对平的。**
笔尖太靠下会划破纸、太靠上会画不上，几十行下来误差就肉眼可见了。

ABBpainting 就是补这个差：先量四角高度，再按位置插值出每一点的 Z 补偿量，最后生成机器人直接能跑的指令。

---

## 效果 & 素材

`assets/` 里放的是这套流程的实践素材，同一个角色的线稿与上色稿：

| 线稿（描摹源） | 上色稿（参考） |
| :---: | :---: |
| [![murasame](assets/murasame.png)](assets/murasame.png) | [![cy](assets/cy.png)](assets/cy.png) |
| `assets/murasame.png` · 黑白线稿，适合直接描摹 | `assets/cy.png` · 彩色参考稿 |

> 描摹优先选**线稿**：轮廓清晰、路径数量少，机器人走线短、成品干净。彩色图直接描摹会产生大量色块路径，画出来是一团乱麻。

---

## 下载

**Windows 开箱即用，无需安装 Python：**

👉 **[下载 ABBpainting.exe v1.2.0](https://github.com/fegrous/ABBpainting/releases/download/v1.2.0/ABBpainting.exe)**

仓库根目录也放了一份同样的 `ABBpainting.exe`，克隆下来即可运行。

---

## 使用方法

### 1. 准备 G-code

用 Inkscape 打开线稿 → `路径 ▸ 描摹位图` 得到矢量路径 → 用 G-code 导出扩展（Gcodetools、J Tech Laser 等）导出 `.gcode` / `.txt`。

**关键要求**：G-code 的落笔行里，Z 必须写成 `Z0.00`——程序靠这个字符串判断"这一行是在画线，需要做高度补偿"。

### 2. 运行 ABBpainting.exe

**第 ① 步：四点调零**

弹出小窗口，填入工件四角的 Z 值（单位 mm）：

```
四点调零，不会详细方法请点击跳过
  左上Z轴  [ 0.00 ]
  右上Z轴  [ 0.50 ]
  左下Z轴  [ 0.30 ]
  右下Z轴  [ 0.60 ]
        [ 保存 ]    [ 跳过 ]
```

- 四角就是**图纸幅面的四个角**，可以在示教器上逐点对刀读出 Z。
- 不想补偿（工件很平 / 手动对过刀）→ 直接点 **跳过**，四角按 0 处理。
- 输入非数字会提示"只能输入数字"，窗口不关。

**第 ② 步：选文件**

选择上一步导出的 `.gcode` / `.txt`。

**第 ③ 步：拿结果**

转换完成会弹窗提示，输出固定写到 **桌面**：

```
%USERPROFILE%\Desktop\output.mod
```

### 3. 导入 RobotStudio

把 `output.mod` 拖进 RobotStudio 的 RAPID 模块列表，即可仿真 / 下发到真实机器人。

---

## 输出长什么样

```rapid
MODULE MainModule
CONST robtarget DW:=[[296.17,-33.73,500.17],[0.000173257,-0.28718,0.957877,-0.000280338],[-1,-1,-1,0],[9E+09,9E+09,9E+09,9E+09,9E+09,9E+09]];
PROC main()
MoveL Offs(DW,266.00,180.00,0), v50, z0, tool0;
MoveL Offs(DW,266.00,180.00,0.00), v50, z0, tool0;
MoveL Offs(DW,266.00,240.00,0.12), v50, z0, tool0;
MoveL Offs(DW,326.00,240.00,0.24), v50, z0, tool0;
MoveL Offs(DW,326.00,180.00,0.12), v50, z0, tool0;
ENDPROC
ENDMODULE
```

几点说明：

- **`DW` 是硬编码的基准点**（`CONST robtarget`），写死在源码里。换工件 / 换机器人要改 `ABBpainting.py` 里的这一行再重新打包。
- **`Offs(DW, a, b, c)` 里的 `a` 是 G-code 的 Y，`b` 才是 X** —— XY 互换输出（相当于把图纸转 90°）。改工件朝向时注意这一点。
- 所有运动都是 `v50, z0, tool0`（速度 50 mm/s、转弯区 0、工具坐标系 tool0），同样写死在源码里。

---

## 四点调零到底算了什么

这是本项目唯一有点技术含量的部分，值得说清楚。

### 坐标预处理

```
x_value = G-code 的 X + 105          # 105 = A4 宽 210 的一半
y_value = G-code 的 Y + 148          # 148 ≈ A4 高 297 的一半
```

即：把一张 A4 幅面 `(0..210, 0..297)` 的图纸平移到原点附近，机器人画出来正好以 `DW` 为中心。

### 补偿公式

设四角 Z 值为 `LU / RU / LD / RD`（左上 / 右上 / 左下 / 右下），令

```
xPct = x_value / 210
yPct = y_value / 297

z2 = RU - LU
z3 = LD - LU
z4 = RD - LU

x1_z = z2 * xPct
x2_z = (z4 - z3) * xPct
Z    = (x1_z - x2_z) * yPct
```

展开后就是一行：

```
Z = [ (RU - LU) - (RD - LD) ] × xPct × yPct
```

### 关键性质：平板工件恒为 0

如果工件是个**绝对平面**（哪怕它是倾斜的），四个角必然满足

```
RD - RU - LD + LU = 0      ⟺      (RU - LU) - (RD - LD) = 0
```

代入上式 → **`Z ≡ 0`**。

也就是说：**这个算法不补偿工件的整体倾斜，只补偿"对角扭曲"（翘曲、翘边）。**

实际用法上这通常是对的——工件的倾斜交给机器人**工作坐标系（wobj）**去摆正，
四点调零负责的是摆正之后仍然残留的那点不平。如果你的工件确实是个斜面且没建 wobj，
那这个补偿帮不上忙。

> 顺带一提：上面的公式在数学上并不等于严格的"双线性插值"
> （严格式是 `LU + (RU-LU)u + (LD-LU)v + (RD-RU-LD+LU)uv`）。
> 它取的是扭曲项，并额外混入了与扭曲量成正比的线性/常数项。
> 因为扭曲量本身很小，这部分误差在实机上可以忽略，这里如实记录。

---

## 已知问题

| 问题 | 说明 |
| :--- | :--- |
| **带 Z 的行输出两条 `MoveL`** | 先判断 XY 再判断 Z，导致同时含 XY 与 Z 的行写两条指令：一条用插值 Z，一条用 G-code 原始 Z。若 G-code 每行都带 Z，插值结果会被后一条覆盖并残留多余移动。可能是设计如此，也可能是 bug——**用前请自行确认输出**。 |
| **补偿值会被"粘住"** | 只有 `z == '0.00'` 字符串完全相等时才重新计算。一串连续落笔、中途没出现 `Z0.00` 的指令会一直复用第一次的补偿值。 |
| **G-code 必须写 `Z0.00`** | 判断条件是字符串精确相等。写成 `Z0.0`、`Z.00`、`Z 0.00` 都不会触发补偿。 |
| **只能写桌面** | 输出路径硬编码 `%USERPROFILE%\Desktop\output.mod`。桌面被重定向到 OneDrive、或非 Windows 系统会直接失败。 |
| **基准点不可配置** | `DW`、速度 `v50`、转弯区 `z0`、工具 `tool0` 全部写死，换场景必须改源码重新打包。 |
| **无批量** | 一次只能转一个文件，逐个弹窗操作。 |

---

## 从源码运行 / 重新打包

```bash
# 运行（需要 Python 3.10+，只用标准库 re / os / tkinter）
python ABBpainting.py

# 打包成单文件 exe
pip install pyinstaller
pyinstaller -F -w --name ABBpainting ABBpainting.py
```

`ABBpainting.py` 是从 `ABBpainting.exe v1.2` 反编译还原的源码，行为与原版 exe 一致，
方便二次修改（换基准点、改输出路径、加批量等）。

---

## 目录结构

```
ABBpainting/
├── ABBpainting.py        # v1.2 源码（从 exe 反编译还原，Windows 专用）
├── ABBpainting.exe       # v1.2 可直接运行的 Windows 程序
├── assets/
│   ├── murasame.png      # 线稿素材（描摹源）
│   └── cy.png            # 上色稿参考
├── LICENSE
└── README.md
```

---

## 配套工具

原流程里还用到一个**便携版 Inkscape**（用于把 PNG 线稿描摹成矢量路径、再导出 G-code）。
体积约 200 MB，没有放进仓库，需要的话自行从 [inkscape.org](https://inkscape.org/release/) 下载，
或使用任意支持"描摹位图 + 导出 G-code"的软件替代。

---

## License

[MIT](LICENSE) © 2026 fegrous
