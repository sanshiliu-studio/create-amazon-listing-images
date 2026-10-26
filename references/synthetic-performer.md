# AI 人物元数据标记

## 固定交付规则

按用户提供的 Windows 属性截图，本流程生成的带写实人物或人体的图片，必须在“属性 → 详细信息 → 标记”中包含精确关键词：

```text
contains-synthetic-performer
```

这是文件元数据，不是画面文案、水印、标题或文件名。沿用“无人脸”要求，腰部穿搭、背影、手部和 AI 重绘人体也按用户的保守标准标记；不以裁掉脸部或使用真人参考为由省略。纯商品图无此要求；未经本次生成/修改的真实摄影不自动改写。

Windows 的显示字段为 `System.Keywords`。为满足用户指定位置并兼顾平台解析，最终 JPEG 同时保留 EXIF `XPKeywords`（UTF-16LE）与 XMP `dc:subject/rdf:Bag/rdf:li` 中的该关键词。保留已有关键词，不清空作者、版权和来源信息，不替换图像工具自带的披露元数据。

## 写入与复核

1. 在 `prompts.md` 或交付清单逐张记录是否含 AI 人物/人体。检查脚本不能从像素自动判断生成来源，执行者须传入真实的适用图片列表。
2. 完成最后一次编辑、放大、色彩和格式转换后再写入。默认使用最终 JPEG，透明 PNG 等母版另存。仅增加披露元数据不需要重新生图，也不应重新压缩图像。
3. Windows 可运行 `scripts/set_synthetic_performer.ps1`，它通过系统 JPEG 属性处理程序写入“标记”，输出新文件、保留原图和原有关键词、不覆盖已有输出。只支持真实 JPEG，不接受把 PNG 改后缀；失败会报错，不能宣称已标记。非 Windows 或用户明确要求 PNG 最终文件时，用可用且支持该格式的元数据工具写入 XMP，并核实 Windows 标记的可见性；无法核实时明确标为未完成，不假装已支持。
4. 写入后先由系统属性读取 `System.Keywords`，再使用只读验收脚本检查最终文件的 `XPKeywords` 与 XMP。任一缺失或拼写不符，都标为披露待处理。不要依赖原图已经有标记；另存、重新导出或处理后可能丢失。
5. 交付标记后的文件链接。默认接受的原生图库规格（包括1086×1448）也须标记，可按原生规格完成交付，不因低于原高分辨率目标再次询问。用户另行要求严格高分辨率但未满足的文件才保留相应未达标说明。元数据通过不代表平台或法律适用性已全部核验。

在技能目录执行的 Windows 示例：

```powershell
# 写入新版本；原图与既有输出不会被覆盖
.\scripts\set_synthetic_performer.ps1 -Source '<最终人物图.jpg>' -OutputPath '<最终人物图-tagged.jpg>'

# 单张验证：明确该图片需要 AI 人物标记
.\scripts\verify_images.ps1 -Category fashion -ExpectedCount 1 -SyntheticPerformerImages @('<最终人物图-tagged.jpg>') -Images @('<最终人物图-tagged.jpg>')
```

`-Images` 列出本次同规格批次的全部文件，`-SyntheticPerformerImages` 只列出其中含 AI 人物的文件。默认十九张组合任务分图库七张、A+ 桌面六张和 A+ 移动六张三批；两端含人物的文件均须标记并在各自批次指定，不能只检查图库人物图。直接 Python 入口使用可重复的 `--synthetic-performer <图片路径>`，与本批文件列表指向同一最终文件。不适用图片不需要为了通过检查而添加虚假标记。

## 规则来源与法律表述

- [Amazon Product image guide](https://sellercentral.amazon.com/help/hub/reference/external/G1881) 与[另一官方图片指南入口](https://sellercentral.amazon.com/help/hub/reference/external/GGW8U76SSNTRTBX7?locale=en-US) 的官方搜索索引包含 `contains-synthetic-performer`、XMP `dc:subject` 的要求，并说明适用情形包括完全由 AI 生成的写实人物；2026-10-21 直接访问仍返回登录/JavaScript 页面，未完整核实类目细则。这里的更宽人体覆盖范围是用户的固定交付要求，不冒充平台条款原文。
- [纽约州 S8420A](https://www.nysenate.gov/legislation/bills/2025/S8420/amendment/A) 已签署，对广告中的合成人物披露作出规定。不得把某州法律、平台元数据流程与所有美国图片场景混成全国统一结论，也不能声称仅填文件标签就履行一切法定披露义务。
- [Microsoft System.Keywords](https://learn.microsoft.com/en-us/windows/win32/properties/props-system-keywords) 将该字段定义为文件关键词/标记集合。实际交付以读回检查为准。

无论实时规则入口能否访问，用户指定的关键词写入与复核都是本技能的必做交付步骤，不以“法规待核实”为由省略。
