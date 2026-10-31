# 每张图的英文提示词结构

本结构用于内置图像工具，不是 API 参数格式。默认新制作任务为七张图库＋六组 A+ 双端，共十九张；生成前统一商品锁定信息和一份共享视觉规范，分别写每张的内容与构图，不分成两套独立风格。只填对当前图片有意义的字段，不复制未知事实。明确单套、单张或局部修订时只写指定图片，额外列出编辑范围及必须保留的部分。先按 SKILL.md 的品类建议选择方向；用具体的材质、用光、配色和构图描述品质感。

A+ 任务先按 [双端内容规划](aplus-images.md) 明确组号及购买问题；双端任务每组分别写 desktop 1464×600、mobile 600×450 提示词，移动版写清重新排版方案，不沿用图库画幅。指定单端修订只写该端提示词，另一端沿用原版并记录版本。A+ 图内标题与必要解释按其专门流程处理，主图零文字与图库副图短标题规则不套到 A+。

A+ 的 `Art direction / Lighting / Color palette / Typography / Materials` 必须沿用同 SKU 七图已确认的共享视觉规范，写明参考的七图版本和图片用途。使用已有七图作为风格参考时明确“继承光色、材质、字体和视觉气质，重新设计本组画面，不复制已发布成图”。没有查看旧七图时，不写“已匹配原七图”的结论。

写 A+ 提示词前先执行 [完整内容规定](aplus-content-rules.md)，只把检查后的准确文案送入 `Text (verbatim)`。明确本图是否使用整套唯一的叠加品牌 logo 位置，图标只保留帮助理解所需内容；生成后仍要逐字检查成图，不能凭提示词里的禁止清单宣称已合规。

```text
Use case: product-mockup [or photorealistic-natural / infographic-diagram]
Asset type: Amazon US gallery image [01–07], [role]; or Amazon A+ image [A01–A06/adapted group], [desktop/mobile]
Human scene: [gallery 03/07 by default: distinct setting, verified product use and photorealistic person interacting with it, face excluded; or no person/not a qualifying scene]
Product truth: [same-SKU fact-record path; confirmed color, silhouette, material, structure, dimensions, sold quantity and included accessories]
Claims and evidence: [only verified functions/benefits and their specific sources; unknown or unsupported items to omit]
Reference images: [each supplied image and its role, if available]
Shared visual style: [same-SKU gallery version and shared style record; or clearly marked provisional direction]
Primary request: [the clear purchasing question this image answers]
Art direction: [category-appropriate visual character; intended audience/positioning if known]
Scene/backdrop: [pure white for MAIN; appropriate setting for secondary]
Composition/framing: [immediately recognizable focal point; complete product or a justified detail view]
Materials/textures: [reference-supported surface texture and finish; preserve real material characteristics]
Lighting: [material-appropriate light; retained highlight/shadow detail and accurate product color]
Color palette: [product-derived palette; coordinated backdrop; preserve actual product saturation]
Typography: [consistent font hierarchy, alignment and spacing when added text is needed]
Text (verbatim): [exact approved English copy, or "No added text"]
Numeric text (verbatim): [exact verified values, quantities, steps and units using Arabic digits 0-9 everywhere; never spell numbers out in English, including values below 10]
Output target: [aspect ratio and requested pixel dimensions]
Keep invariant: [specific product geometry, parts/holes/ports/closures, color, count, finish and brand details; do not invent hidden structures or functions]
Constraints: No visible human faces, including reflections or background media.
No gift box, ribbon, gift bag, included gifts, or implied gift packaging.
No unauthorized third-party trademarks, copyrighted characters, or celebrity likeness.
No watermark, promotional badges, prices, ratings, fabricated claims, or invented accessories.
```

`Output target` 是优先请求，不是工具能力或实际像素的证明。图库默认接受原生规格，包括1086×1448，读取首张实际尺寸并核对画幅、商品和清晰度后直接继续整套；不再询问是否接受预览，不因未超过2000px而重试，也不把1086×1448写死成工具永久上限。图库验收明确用 `--gallery-resolution native`，只有本次另行指定严格高分辨率时用 `high`。A+ 首组双端仍须按1464×600和600×450分别通过文件、内容及可读性检查，再批量制作；指定单端修订只预检该端。A+或另行指定的硬指标失败按 SKILL.md 上限纠正。将实测尺寸、采用的验收模式和范围记在 `prompts.md`，不把原生输出报告为已达到高分辨率目标。

在生成记录中另列本图是否含 AI 人物/人体；提示词不要求把 `contains-synthetic-performer` 画在画面上。该关键词在最终导出后按 [AI 人物元数据标记](synthetic-performer.md) 写入文件属性并读回检查。

完整七图至少规划两张不同的写实人物使用场景，默认 03、07，第 07 固定为使用场景。说明每张人物如何实际使用商品及场景差异，不编造功能；以合理取景避开脸部。人物标记适用范围比场景计数更宽，孤立手部特写虽需标记却不能自动算合格真人场景。最终查看实际文件并记录合格图号，不能靠提示词或两张适配图凑数。单张/局部修订仍按指定范围执行。

提示词写出商品约束不代表实际成图已遵守。逐张生成后先核对商品；最后导出后按 [产品一致性与功能卖点终检](product-consistency.md) 查看最终文件与实拍/事实来源，记录外观和卖点是否被改动，修正后重新检查。后续图片不得把首张 AI 图的错误当作新的商品标准。

## 皮带白底主图

皮带图库 01 的构图字段默认使用以下内容，并同时填入本款实拍来源与不可改动细节；仅主图使用，不套到其他图片。完整规则见 [皮带白底主图默认构图](../SKILL.md#皮带白底主图默认构图)。

```text
Belt MAIN composition: Arrange the actual belt in a natural, horizontally elongated oval loop. Photograph from the front at a slightly elevated angle, showing the front of the buckle, the open loop and the rear arc. Place the buckle at the front center, facing the camera. Extend the tail along the front toward the image right only if the actual threading direction permits. Preserve the real fastening mechanism, keepers, holes, thickness and proportions. Keep the whole belt visible, horizontally centered and slightly below the canvas center, with balanced margins and an appropriate product scale. Use a pure white RGB 255,255,255 background, soft studio lighting and a subtle contact shadow. No added text, people or props. Transfer only the reference arrangement and camera angle; reproduce all product details from the actual SKU photos, never the composition reference's brand, decorative buckle, color or texture. Do not mirror branding or deform the belt to force the pose.
```

## 尺寸图

明确测量对象、方向与端点，使用同一批真实数据。先锁定实际应显示的数字、精度和单位，再把完整文字填入 `Text (verbatim)` 与 `Numeric text (verbatim)`，例如 `Strap Width: 1.50 in / 3.8 cm`、`Height: 7.9 in / 20 cm`；示例数值不能替代本款资料。

所有地方的数字都用阿拉伯数字，包括普通数量和步骤，如 `2 pieces`、`Step 1`。不要把小数逐位拼读，不要将小于 10 的数字改成英文单词；不得在新提示词中沿用旧“拼写小数字”的指令。保留已确认精度，不擅加小数位或改变换算值。最后直接查看成图，对照原始数据与锁定文案检查数字、小数点、单位及尺寸线端点；出现英文拼读、漏字、错值或乱码都先修正再通过。改提示词不等于改好了既有图片。

## 一致性

商品照片有多角度时指定每张的参考用途。不要以“参考风格”为由把竞品产品形状带入用户商品。首图生成的猜测细节不能自动升级成商品事实。

全套保持同一光色方向、背景色系及排版体系，各张可用不同角度和景别承担不同用途。主图仍以白底和该类目要求为准；不能把场景图的配景搬进主图。

一致性范围包括七图与 A+ 的桌面、移动版本。收尾时对照共同视觉规范和实际七图检查，而不是只比较新生成的 A+ 图片。

## 将视觉方向写具体

例如已确认的奶油白哑光陶瓷花瓶副图，可描述为：

```text
Art direction: Warm, understated home styling with the vase as the clear focal point.
Scene/backdrop: A light wood side table against a warm white wall; restrained supporting decor.
Materials/textures: Preserve the reference vase's matte ceramic finish and subtle surface variation.
Lighting: Soft directional side light revealing surface and silhouette; retain highlight and shadow detail.
Color palette: True cream-white product color, coordinated wood and warm-white surroundings.
Composition/framing: Clearly show the vase at a believable table-scale; keep its silhouette unobstructed.
Text (verbatim): No added text.
```

只适用于用户资料支持的材质、颜色和外形。对鲜艳的运动或儿童商品另选合适方向，不沿用这套暖白配色。

## 常见错误

- 七宫格代替七张文件：分别生成和保存。
- 每张都贴卖点与尺寸：主图无叠加文案，双单位集中在尺寸图。
- 用 `4K` 或 300 DPI 代替验收：读取真实宽高像素。
- 没照片就完全不启动：可先生成明确标记的概念图，并索要核实所需资料。
- 把装饰花、鞋、首饰或收纳袋暗示为附送：通过构图、实际包含物说明及必要短注释消除误解。
- 只写 premium/luxury，或一律米色、黑金、低饱和：按品类落实光线、材质和构图，保留商品本色。
- 图很精致却看不清商品或用途：完成手机缩略图、放大细节和购买判断三项视觉验收。
