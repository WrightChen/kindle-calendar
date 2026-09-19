# kindle-calendar

把一台越狱后的 Kindle Paperwhite 2（758×1024）变成常显中文日历。

```
render.py                 生成 758x1024 8-bit 灰度 PNG（公历 + 农历 + 节气 + 节日 + 休/班 + 宜忌 + 年进度）
serve.py                  局域网小服务：GET /calendar.png，日期变化或超过 1 小时自动重绘
.github/workflows/        GitHub Actions：每天 00:05（北京时间）+ 每小时重绘，发布到 GitHub Pages
kindle/calendar/          放到 Kindle 根目录 /calendar/：calendar.sh（主循环）、config.sh（URL/间隔）、bin/xh（支持新 TLS 的下载器）
kindle/documents/         放到 Kindle 的 documents/：Calendar-Start.sh / Calendar-Stop.sh 两个 scriptlet
```

## 本地跑

```bash
pip install -r requirements.txt
python render.py --out site/calendar.png            # 今天
python render.py --out x.png --date 2026-10-01      # 任意日期
python serve.py --port 8765                         # 局域网服务
```

## Kindle 端

1. 越狱（WinterBreak）。
2. 把 `kindle/calendar/` 拷到 Kindle 根目录成 `calendar/`，把 `kindle/documents/*.sh` 拷到 `documents/`。
3. 改 `calendar/config.sh` 里的 `IMAGE_URL`（Unix 换行）。
4. 弹出 USB，主页点「日历看板 · 启动」。脚本会停掉 Kindle 自带 UI、禁止休眠、开 Wi-Fi，然后每 `INTERVAL` 分钟拉一次图，图变了才重绘。
5. 想恢复成普通 Kindle：长按电源键 40 秒重启即可（脚本不会自启）。

日志在 Kindle 的 `calendar/calendar.log`，用 USB 接电脑就能看。

## 云端（不用自己开机）

1. 建一个 GitHub 仓库，把本目录推上去（`main` 分支）。
2. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
3. 手动跑一次 Actions「Render calendar」，之后每小时自动更新。
4. 图片地址：`https://<用户名>.github.io/<仓库名>/calendar.png`，填到 `config.sh` 的 `IMAGE_URL`。
   PW2 自带 wget 的 TLS 太老，脚本会自动退回到 `bin/xh` 下载。

## 已知限制

- 法定假日「休/班」标记依赖 `chinesecalendar` 包，国务院每年 11-12 月公布下一年安排后要升级该包，否则下一年不显示休/班。
- 脚本运行期间 Kindle 不能当阅读器用，重启即恢复。
- 设计为插电常显。不插电时 Wi-Fi 常开，大约撑 1～2 天。
