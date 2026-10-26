# 文件验收与运行环境

生成第一张图前准备好只读验收环境；每张生成后检查像素，最终导出后检查交付文件。运行位置应为技能目录，或使用脚本的绝对路径；不要把当前工作目录误当成脚本所在目录。

## 选择 Python

1. 在 Codex 桌面中优先调用 `load_workspace_dependencies`，取得本次环境提供的 Python 可执行文件路径；不把某台电脑的用户名或缓存版本固定在技能中。
2. Windows 可用 `scripts/verify_images.ps1`。启动器先实际执行 Python/Pillow/ImageCms 探针，跳过 WindowsApps 应用别名，按可用命令和已知桌面运行时位置寻找；也可用 `-PythonPath` 指定工具返回的准确路径。显式指定的路径不可用时会报错，不默默换环境。
3. `-CheckEnvironment` 只输出已确认的 Python 路径、Python 和 Pillow 版本。不能仅凭命令存在或退出码为零判断可用，必须看到探针 JSON 中 `status: ready`。
4. 缺少 Python、Pillow 或 ImageCms 时先尝试应用提供的已安装环境；仍不可用就明确说明文件验收未执行。脚本不会自动安装依赖、调用网络或改图。

Windows 示例（在技能目录执行，尖括号内容须替换为实际值）：

```powershell
# 环境探针；若已通过自动发现，可以省略 -PythonPath
.\scripts\verify_images.ps1 -CheckEnvironment -PythonPath '<工具返回的Python完整路径>'

# 整套七张：明确列出七个实际文件路径
.\scripts\verify_images.ps1 -Category fashion -GalleryResolution native -ExpectedCount 7 -Images @('<图01>', '<图02>', '<图03>', '<图04>', '<图05>', '<图06>', '<图07>')

# 只做或修改一张
.\scripts\verify_images.ps1 -Category other -GalleryResolution native -ExpectedCount 1 -Images @('<本次图片>')

# 两张局部修订
.\scripts\verify_images.ps1 -Category fashion -GalleryResolution native -ExpectedCount 2 -Images @('<修订图03>', '<修订图06>')
```

其他系统或已确认 Python 环境可以直接运行：

```text
<已验证的Python> -B -X utf8 scripts/verify_images.py --category other --gallery-resolution native --expected-count 1 <本次图片路径>
```

Windows 遇到脚本执行策略限制时直接使用已验证的 Python 命令，不更改系统执行策略。退出码：`0` 为本次文件检查通过，`1` 为文件未达标，`2` 为环境/命令参数错误；保留具体原因，不把非零退出码一律当作脚本故障。

## 两项结果分别解读

图库默认明确传入 `--gallery-resolution native`（Windows 为 `-GalleryResolution native`），接受原生尺寸，包括1086×1448，不设最短边门槛；仍检查可解码及品类画幅，实际清晰度由视觉复核。仅用户本次明确要求严格高分辨率时使用 `high`，检查短边严格大于2000px。为兼容旧调用，脚本省略参数仍为 `high`；技能默认调用必须明确传 `native`。JSON 的 `gallery_resolution` 记录本次模式，A+ 为 `null`。

A+ 按 [A+ 双端图片流程](aplus-images.md) 传入 `-AplusLayout desktop/mobile`（Python 为 `--aplus-layout`），精确检查桌面1464×600、移动600×450，以及文件小于2,000,000字节、双向DPI至少72。图库分辨率参数对A+无效，不放宽A+要求。

| 字段 | 含义 | 不通过的例子 |
|---|---|---|
| `pixel_passed` | 所有本次文件可解码，非时尚方图/时尚竖图；`native`接受原生尺寸，`high`另查短边大于2000px | `native`仍拒绝非时尚长方图；1086×1448时尚竖图在`native`可通过，在`high`不通过 |
| `delivery_passed` | 数量正确，无相同文件或相同解码像素凑数，真实 JPEG/PNG 且后缀匹配、RGB 兼容色彩、可验证 sRGB 配置/声明、无透明像素、非动画；指定 AI 人物图的双字段标签正确 | 少图、重复像素、PNG 冒用 .jpg、BMP、CMYK、无色彩声明、损坏或非 sRGB 的 ICC、透明 PNG、动画、人物图披露标签缺失 |
| `passed` | 上述两项均通过 | 只像素合格仍不能报整体文件检查通过 |

`images` 逐张保留宽高、真实格式、色彩模式、`color_status`、透明状态及两项错误列表；原有 `errors` 汇总仍保留。脚本单批数量参数默认仍为 7，仅供图库批次使用，不代表制作任务只做七图。默认两套共十九张须分三批：图库 `--expected-count 7`，A+ 桌面 `--aplus-layout desktop --expected-count 6`，A+ 移动 `--aplus-layout mobile --expected-count 6`；三批结果与跨套视觉/内容检查共同决定整套状态。单套、单张/局部任务显式传入本次该批约定数量，不把十九张放进一个尺寸模式验收。

RGB 模式不等于已验证 sRGB，ICC 配置名称仅作记录，不作为判断依据。脚本使用 Pillow/ImageCms，将有效的矩阵/曲线型 RGB ICC 与内置 sRGB 作相对色度转换对照：检查 17×17×17 RGB 网格及完整灰阶、三通道渐变，共 5,937 个采样点，每通道差异不超过一个 8 位码值才记为 `srgb`。这能识别冒用 sRGB 名称而实际改变原色或色调曲线的配置；真正等效的配置即使改名也可通过。任意输入查找表等超出该保守识别范围的 ICC 记为 `unverified`，不能仅因名称含 sRGB 就放行。

没有 ICC 时，PNG 的合法 sRGB 声明也可通过；没有可验证声明为 `unverified`，不符合对照的配置或其他色彩空间为 `non_srgb`，损坏 ICC 为 `invalid_profile`。有 ICC 时优先检查 ICC，不用 PNG 标签掩盖错误配置。这是本技能的文件交付标准，采样不等于完整色彩认证，也不能证明源图此前已正确转换；不声称 Amazon 一律要求内嵌 ICC。转换方法见 [Pillow ImageCms 官方文档](https://pillow.readthedocs.io/en/stable/reference/ImageCms.html)。

文件名与解码格式必须对应：`.jpg`/`.jpeg` 为 JPEG，`.png` 为 PNG，后缀不区分大小写；只改后缀不算格式转换。去重同时比较文件字节和按 EXIF 显示方向归一化后的尺寸及 RGBA 像素，避免靠改注释、披露元数据、封装格式或不透明 alpha 通道凑数；范围仅为本次传入文件。它只识别完全相同的解码像素，不能识别压缩后像素略变或构图相似的图片，近似重复仍需视觉检查。

带 alpha 通道但全部不透明的 PNG 可以通过；确有透明像素的图片只作母版，另行通过工具支持的流程导出不透明最终文件。脚本不判断纯白背景、商品是否占足画幅、文字/尺寸是否正确，这些仍需视觉检查。脚本也不能判断生成商品是否被改形、增减部件或虚构功能，文件通过后仍须执行 [产品一致性与功能卖点终检](product-consistency.md)，单列核对来源、偏差、修正与结果；不能把 `passed: true` 当成与实物一致的证明。

能力预检每个文件可用 `--expected-count 1`；A+ 双端任务须分别预检首组桌面和移动两个文件，连同内容/可读性检查均通过后再批量制作。指定单端修订只检查该端，另一端原版的路径、版本与已有状态另行记录。部分交付可按实际完成数量检查；这种通过只覆盖传入文件，不能把六张文件通过说成七图完整或 A+ 双端齐全。默认目标尺寸与实际尺寸的差别应在交付中如实记录。

## AI 人物图的披露检查

含 AI 人物/人体的图片须按 [AI 人物元数据标记](synthetic-performer.md) 先写标记，再将这些最终文件通过 `-SyntheticPerformerImages @('<图03>', '<图06>')` 传给 Windows 启动器；Python 入口重复传入 `--synthetic-performer <图片路径>`。总图片列表仍按本次任务数量传入。指定人物文件必须属于本次检查列表，拼错路径会报参数错误，不能悄悄跳过。

逐图 `synthetic_performer` 记录是否要求标记、`windows_keywords`、`xmp_dc_subject` 和验证结果。只有 EXIF `XPKeywords` 与 XMP `dc:subject/rdf:Bag/rdf:li` 同时含精确关键词 `contains-synthetic-performer` 才通过本技能要求；只写文件名、画面水印、XMP 单字段或备注都不能冒充完成。此项影响交付文件结果，不影响真实像素判断。不指定人物文件不代表脚本检测过“无人”，执行者须据生成记录如实选择。
