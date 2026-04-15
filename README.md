# 电商商拍复刻 Chrome 插件

这个项目包含一个 Chrome 扩展和一个本地中转后端，用于在小红书、Pinterest、淘宝等平台看到参考图后，上传自己的商品图并生成新的电商素材。

核心目标是：参考图负责场景、构图、姿态、光影和氛围，商品图负责主体一致性。真正的 Ark API Key 只保存在本地后端，不会写入浏览器扩展。

## 当前流程

1. 在小红书 / Pinterest / 淘宝页面 hover 一张参考图。
2. 点击 `替换成我的商品`。
3. 上传自己的商品图。
4. 可选填写商品主体说明和补充要求。
5. 选择画面比例：跟随原图比例，或选择 4:3、3:4、16:9、9:16、1:1、2.35:1。
6. 后端只调用一次 `doubao-seed-1-6-251015`，同时理解参考图、商品图和文字要求，输出最终生图 Prompt。
7. 后端把最终 Prompt 和用户上传的商品图一起发给 `doubao-seedream-4-5-251128` 生图。
8. 扩展展示生成结果，支持下载，并可展开查看本次最终生图 Prompt。

说明：商品图会作为生图阶段的参考输入；参考图不会直接作为生图参考输入，只通过 seed1.6 输出的 Prompt 影响生成结果。

## 目录说明

- `manifest.json`：Chrome 扩展清单
- `src/content.js`：页面 hover 按钮、弹窗、上传商品图和结果展示
- `src/content.css`：弹窗和按钮样式
- `src/background.js`：扩展设置读取和本地后端调用
- `src/options.html`：扩展设置页
- `src/options.js`：设置页保存和读取逻辑
- `server/proxy.py`：推荐使用的 Python 本地中转服务
- `server/proxy.js`：Node 版本中转服务
- `server/.env.example`：服务端环境变量示例

## 启动本地后端

真正的 `ARK_API_KEY` 只放在后端环境变量里。

```bash
cd /Users/bytedance/Documents/复刻插件
export ARK_API_KEY='你的 Ark Key'
export PROXY_TOKEN='你自己定义一个口令'
python3 server/proxy.py
```

如果暂时不想加访问口令，可以不设置 `PROXY_TOKEN`。

默认启动地址：

```text
http://127.0.0.1:8787
```

健康检查地址：

```text
http://127.0.0.1:8787/health
```

## 加载 Chrome 扩展

1. 打开 `chrome://extensions`。
2. 打开右上角“开发者模式”。
3. 点击“加载已解压的扩展程序”。
4. 选择本项目目录。
5. 打开扩展设置页。
6. 填写后端地址和访问口令。
7. 保存设置。

设置保存使用 `chrome.storage.local`，可以保存较长的 SP 提示词。

## 设置项

- `后端地址`：默认 `http://127.0.0.1:8787`
- `访问口令`：如果后端设置了 `PROXY_TOKEN`，这里填同样的值
- `模型名`：默认生图模型
- `识图模型`：默认多模态理解模型
- `SP 提示词`：控制唯一一次 seed1.6 如何生成最终生图 Prompt
- `默认附加 Prompt`：每次生成时附加的补充要求
- `图片尺寸`：默认尺寸，当弹窗未覆盖比例时使用
- `返回图片路径`：默认 `data[0].url`
- `额外请求体 JSON`：传给 Ark 生图接口的额外参数

## 后端接口

扩展会向本地代理发送：

```http
POST /replicate
```

请求体包含参考图地址、商品图 data URL、商品主体说明、补充要求、模型配置和画面尺寸。

后端返回：

```json
{
  "imageUrl": "生成后的图片地址或 base64 data url",
  "prompt": "最终送去生图模型的 Prompt"
}
```

## 注意事项

- 如果页面报 `Failed to fetch`，通常是本地后端没有启动，先检查 `http://127.0.0.1:8787/health`。
- 如果页面报 `Proxy token invalid`，说明扩展设置页里的访问口令和后端 `PROXY_TOKEN` 不一致。
- 如果页面报 `ARK_API_KEY is missing`，说明启动后端时没有设置 `ARK_API_KEY`。
- 不要把真实 Ark Key 写入扩展代码或提交到 GitHub。
