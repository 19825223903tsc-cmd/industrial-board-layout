# 可执行线框数据

新项目使用 `elements` 模式，不使用旧 `blocks` 的固定图片区结构。渲染入口：

```text
python scripts/render_wireframe.py /absolute/project/layout.json --out /absolute/output
```

此模式需要 Pillow；如当前 Python 缺少它，先检查环境可用运行时，或报告依赖，不能声称已生成 PNG 或测量文字。渲染仅绘制版式与真实文本，不生成或编辑产品图。

## 顶层

- `canvas`：`width`、`height`，均为屏幕预览 px；可设置 `font_path` 指向支持当前语言的实际字体。未指定时尝试已知系统字体，找不到则报错。打印尺寸另记录，不混用单位。
- `intent`：本板主题、产品特征、构图理由与阅读顺序。避免只写“高级感”。
- `content_inventory`：真实素材、文字状态与允许的概念演绎；素材路径不代表已授权新的外部操作。
- `delivery_mode`：默认 `composition-guide`。历史 `wireframe` 仍可读；其他值只记录用户已明确要求的下游测试，不构成自动执行指令。
- `language_profiles`：可按 `zh-CN`、`en` 等语言标识配置 `font_path`。文本元素的 `language` 优先于 `canvas.language`；未定义时沿用画布字体。混排段落应选完整支持所需文字的字体或拆分元素，不假定自动字体回退。
- `typography`：按角色定义 `font_size`、`line_height`、`color`，数值为 px。角色名称与层级数量自由。
- `elements`：自由安排文本、图片区和分隔线，不限定模块数量或位置。
- `alignments`：需要测量的对齐关系。`axis` 可为 `left/right/top/bottom/baseline/first-baseline/last-baseline/ink-left/ink-right/ink-top/ink-bottom`，`ids` 至少两个元素；`tolerance` 为 px。baseline 与 first-baseline 都指第一行；last-baseline 指最后一行。ink-* 为实际字体字形包围框估算，不能代替光学检查。
- `allowed_overlaps`：仅列出有意叠放的元素ID对，例如 `[["hero","callout"]]`，并在 intent 说明原因。不要用它掩盖越界或无意遮挡。

## 元素

共同字段：`id`、`type`、`x/y/w/h`。文本坐标是预留行框左上角，非字形最上缘。矩形元素宽高为正；水平 `rule` 可 `h=0`。

- `text`：`text` 为实际文字，`style` 引用 typography；可覆盖 `font_size/line_height/color/font_path`，语言字体的优先级是元素/样式 font_path → language_profiles → canvas font_path，可设 `max_lines`。附加 `role`、`associated_with` 描述内容与图片的关系。英文按词换行，中文按字初排；孤行、标点和字形仍需目视复核。
- `image-box`：记录 `role`、`source`、`fit`、`view` 和可选的 `crop_note`。脚本画占位框，不嵌入素材；`contain`用于完整主体，`crop`仅用于明确的细节区域。原图周边空白、产品轮廓和实际视觉尺度在后续排版时另查。
- `rule`：从 `(x,y)` 到 `(x+w,y+h)` 的细线，可设 `color`；不参与框重叠检测。复杂引线可拆为线段，端点是否指向真实部位需目视核对。

## 输出与边界

输出 `wireframe-image-input.svg/png`、`wireframe-annotated.svg/png`、`layout.json` 与 `layout-checks.json`。SVG中标题、正文和图注保留为文字；PNG预览使用当前实际字体。

报告包含各块实际字体、语言、行数与高度、首末行基线、字形边界、英文孤词提示及声明锚线差值、画布越界、重复ID和未声明的框重叠。它不证明文案正确、字体拥有全部字形、图片关系合理或构图优秀，也不检查未声明的所有潜在对齐关系。SVG在其他软件打开后需复核字体与版面。

`assets/example-board-wireframe.json` 仅说明字段与文字初排，内容和坐标不构成默认展板模板。旧 `blocks` 模式为兼容历史线框保留，新项目不得以它规避文字设计。

## 跨模块对齐与重复间距

新项目有多个图文区时，先决定共同起止线，再用 `alignment_bands` 分组声明。每项有 `id`、可选 `heading_ids`、`image_ids`、`caption_ids`、`image_edge`（默认bottom，可设top）与 `tolerance`。同带标题检查首行基线，图片检查选定边界，图注检查首行和末行基线。不同顶端的图片可通过底边收齐；不要误要求全部元素顶端相同。若确有意错落，记录理由，不把没有声明当作已验证。

`gap_rules` 每项包含 `id`、`pairs`（前后元素ID对）、`axis`（vertical或horizontal）、可选 `expected` 与 `tolerance`。例如多个图片与其图注的垂直间距设为同一值。未指定expected时检查各对是否一致。测量结果写入 `gap_checks`。

这些关系由设计者明确规划，脚本不会自动理解所有视觉同排关系。输出前仍需逐行目视核对，报告检查覆盖范围。

## 五轮审查记录

线框与提示词完成后执行 [five-pass-review.md](five-pass-review.md)。`qa-review.json`由review_gate.py init生成，默认所有检查pending，不能把示例检查结论复制为真实记录。每轮记录具体检查项、证据和问题修复；check通过生成handoff-ready.json。文件指纹绑定当前布局、两类PNG、SVG、测量报告、提示词和已存在的素材。任何相关修改需重新审查当前版本。

## 产品证据与细节取景（新项目必填）

每个image-box增加 `evidence_status`（provided-view/visible-crop/unsupported-placeholder）及 `evidence_note`。有实际依据的区域必须指定可读取原图；占位不伪装为真实产品视角。`fit=crop`或visible-crop须提供source_region、target_feature与非空exclude_features。详见 [product-evidence.md](product-evidence.md) 和 [detail-framing.md](detail-framing.md)。

source_region为完整原图的归一化[x,y,w,h]。脚本检查有限数值、边界、原图尺寸与区域记录，并输出source-regions.json和含实际原图/区域框的source-map.svg。构图线框对应区显示同一元素ID，以建立取景映射。SVG源图标记需要通过实际可用的矢量预览工具查看；不能把坐标校验当作部位正确的证明。

相对source路径基于输入layout.json目录；建议输出同一项目目录，并保持产品原图与源图标记文件一起交接。审核门槛还会绑定标记说明；有局部区域时，第一轮必须留source-map证据。


## 本独立版的语言边界

CLI会读取assets/language-policy.json，补充本版主语言和实际可用字体。英文版拒绝未声明的中文正文；中文版拒绝英文主语言。显式外文品牌/专名可按元素记录language_exception_note，不能用它放行整篇反向语言正文。语言检查只是输入约束，不能证明断行美观或生图文字准确。
