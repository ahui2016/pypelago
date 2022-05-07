# ipelago (in Python)

CLI personal microblog (命令行个人微博客)

纯命令行操作，包括两方面功能：

1. 写微博客并生成静态网站 (HTML 和 RSS)
2. 订阅别人的 RSS


## ipelago 之名

ipelago 源于群岛的英文 archipelago, 如果我们每一个人是一座孤岛，那么当我们搭建自己的微博客，大家的微博客聚在一起就可以形成群岛。


## 主要功能 (写微博客、订阅 RSS)

### 写自己的微博客

- 多种方式方便写博文（包括命令行输入、获取剪贴板内容、获取文件内容、通过简陋的 GUI 窗口输入）。
- 可生成静态网站 (包括 HTML 和 RSS), 这些静态文件可通过 GitHub Pages 或类似的免费服务搭建你的私人微博客供别人浏览、订阅。
- 生成 HTML 的模板、样式可以自定义（自带一个简单模板）。
- 可区分公开消息与隐私消息，只有公开消息才会对外发布，隐私消息只能本地浏览。
- 有简单的 #标签 功能与搜索功能。

### 订阅别人的微博客

- 可通过 RSS 订阅别人的微博客。
- 只支持微博客（一条消息只有一两句话），不支持正常博客（长文章），因此数据库体积不会暴涨，长期使用也能一直保持很小的体积。
- 有限订阅（意思是不保存全部订阅消息，看到特别喜欢的内容可执行收藏命令，收藏的消息才会永久保存）。有限订阅可避免储存大量无用信息，避免数据库体积暴涨，减少信息焦虑。
- 可设置 proxy, 方便与翻墙软件搭配使用。

### 减少烦躁和焦虑

一般通过 App 或网页浏览消息时，会一目十行，快速上下滑动消息列表，这种操作有可能使烦躁和焦虑感变得更严重。

ipelago 也可一次列举多条消息，但更提倡使用逐条浏览功能，每次只显示一条消息，并且可以记住位置，随时离开去做别的事情，回头继续从上次中断的地方接着阅读。

因此，有助于减少烦躁与焦虑。


## 安装与初始化

ipelago 使用了 Python 3.10 的新特性，比如 type union operator, pattern matching 等，因此，如果你的系统中未安装 Python 3.10, 推荐使用 [pyenv](https://github.com/pyenv/pyenv) 或 [miniconda](https://docs.conda.io/en/latest/miniconda.html) 来安装最新版本的 Python。

例如，安装 miniconda 后，可以这样创建 3.10 环境：

```sh
$ conda create --name py310 python=3.10
$ conda activate py310
```

安装非常简单，只要 `pip install ipelago` 即可。

安装后，第一次正式使用前，必须执行 'ago init name' 进行初始化，其中 name 是你的微博客名称，对外发布时别人可以看到。


## 帮助

- `ago -h` (查看帮助消息)
- `ago post -h` (每个子命令也有详细的帮助消息)


## 初始化

- `ago init 别有洞天` (初始化，设定微博客名称为“别有洞天”)


## 写博文

- `ago post Hello World!` (写一条公开消息, 可通过 HTML 及 RSS 对外发布)
- `ago post -pri/--private My password is abcd` (写一条隐私消息, 仅本地可见)
- `ago post` (发送剪贴板的内容)
- `ago post -g/-gui` (弹出一个简陋的 GUI 窗口方便输入)
- `ago post -f/--file ./abc.txt` (发送文件 abc.txt 的内容)

### 切换与删除

- `ago toggle id` (切换公开/隐私，其中 id 是消息的 id)
- `ago delete id` (删除一条消息)

注意，切换公开/隐私、或删除消息后，要重新 publish 发布消息，才能反映到静态网站中（关于发布静态网站，请看后面关于 publish 的章节）。


## Timeline (阅读自己微博客)

- `ago tl` (阅读下一条消息, 完全等同于 `ago tl -next`)
- `ago tl -zen` (阅读下一条消息，专注模式)
- `ago tl -first` (阅读最新一条消息)
- `ago tl -next` (阅读下一条消息)
- `ago tl -go/--goto 2022-03-15` (跳到 2022年3月15日 或最接近这天的消息)
- `ago copy id` (复制指定 id 的博文内容)

以上命令包括（且只包括）公开消息与隐私消息。  
以下命令可区分公开/隐私/收藏
(其中 '-today' 与 '-yesterday' 不可与 '-fav' 搭配使用)
('-date' 与 'count' 可与 '-fav' 搭配使用)。

- `ago tl -today` (阅读今天的消息，包括公开与隐私，不包括收藏)
- `ago tl -yesterday` (阅读昨天的消息，包括公开与隐私，不包括收藏)
- `ago tl -today -pub/--public` (阅读今天的消息, 限定公开消息)
- `ago tl -today -pri/--private` (阅读今天的消息, 限定隐私消息)
- `ago tl -fav/--favorite` (阅读最近几条收藏消息)
- `ago tl -date 2022-03-15` (阅读 2022年3月15日 的消息, 默认上限 9 条)
- `ago tl -date 2022-03` (阅读 2022年3月 的消息, 默认上限 9 条)
- `ago tl -date 2022 -pri -limit 20` (阅读 2022年 的隐私消息, 最多只显示上限 20 条)
- `ago tl -count 2022-03` 统计 2022年3月 的消息条数


## 订阅 RSS

- `ago news -follow https://douchi.space/@mtfront.rss` (订阅长毛象)
- `ago news -follow https://m.cmx.im/@guobetty.rss` (一般来说，长毛象的 rss 地址就是在用户地址后面直接加 '.rss' 即可) (注意，这个源要翻墙，可参考下面 Proxy 章节设置代理)
- `ago news -follow https://v2ex.com/feed/create.xml -p HasTitle` (订阅V站的“分享创造”节点)
- `ago news -follow https://geeknote.net/Rei/feed.atom -p HasSummary` (订阅 geeknote)
- `ago news -follow https://sspai.com/feed --parser HasTitle` (订阅少数派)
- `ago news -l/--list` (查看已订阅的 RSS 列表)
- `ago search -feeds` (完全等同 `ago news -l`)
- `ago search -feeds keyword` (查找源标题里包含 keyword 的源)

### 关于 parser

默认采用 '--parser Base' 解析 RSS 内容，舍弃每篇博文的 title (因为有时 title 与正文重复)。

建议先看看 RSS 源文件，看 title 有没有必要显示，如果需要保留 title, 可使用以下命令订阅：

- `ago news -follow [url] -p/--parser HasTitle`

在订阅后，也可更改解析器：

- `ago news -u/--update [id] -p/--parser HasTitle`

有的 RSS 源文件在提供 `<content>` 的同时也提供 `<summary>`, 对于这种情况，建议采用 '--parser HasSuammry'。

### Proxy (代理)

- `ago -i/--info` 查看当前 proxy 设定。
- `ago --set-proxy [url]` 设置代理网址（有些 rss feed 需要翻墙才能订阅）
- `ago --set-proxy true` 启用代理。
- `ago --set-proxy false` 不使用代理。

例如: `ago --set-proxy http://127.0.0.1:1081` (注意网址要以 http 开头)

### 改名

改名可以让消息看起来更清晰（显示每条消息时，都会注明源的名称）。

```sh
$ ago news -follow https://v2ex.com/feed/create.xml -p HasTitle

[R9DX70] 分享创造
https://v2ex.com/feed/create.xml

$ ago news -feed r9dx70 --set-name 分享创造-V2EX

[R9DX70] 分享创造-V2EX
https://v2ex.com/feed/create.xml
```

### 改 ID

改 ID 可以方便后续操作（比如指定阅读一个源的消息、强制更新指定的源，都需要用到 ID）。

```sh
$ ago news -follow https://sspai.com/feed -p HasTitle

[R9ELEZ] 少数派
https://sspai.com/feed

ago news -feed r9elez --set-id sspai

[sspai] 少数派
https://sspai.com/feed
```

### 更新

默认每个源每 24 小时只能更新一次，可使用 '-force' 参数强制更新，但为了尊重源站节约资源及减少焦虑，建议不要频繁更新。

- 每次只能强制更新一个源，不可强制批量更新
- 而且也不是自动更新，需要手动执行以下命令才会更新
- 一旦更新，未收藏的消息就会被新消息覆盖（即，不保留旧消息）。
- 遇到特别喜欢的消息可使用命令 'ago like id' 收藏，永久保存。

- `ago news -u/--update all` (批量更新全部源)
- `ago news -u sspai` (更新 feed id 为 sspai 的源)
- `ago news -force -u id` (强制更新指定 id 的源)

### 阅读消息

- `ago news` (阅读下一条消息, 完全等同 `ago news --next`)
- `ago news -first` (阅读最新一条消息)
- `ago news -next` (阅读下一条消息)
- `ago news -zen` (阅读下一条消息, 专注模式)
- `ago news -go/--goto 2022-03` (跳到 2022年3月1日 或最接近这天的消息)
- `ago news -feed id` (阅读指定 id 的源的消息，默认上限 9 条)
- `ago news -feed id -limit 3` (阅读指定 id 的源的消息，最多显示 3 条)

- `ago news -like id` (收藏指定 id 的消息)
- `ago like id` (完全等同于 `ago news -like id`)
- `ago news --toggle-link` (显示/隐藏消息本身的链接)
- `ago copy id -link` (复制指定 id 的消息的链接)

### 删除（源/消息）

- `ago news -delete id` (删除一个源及与其相关的消息，已收藏的消息不会被删除，其中 id 是指用 'ago news -l' 看到的 id)
- `ago delete id` (删除一条消息，其中 id 是指 消息的 id)


## 发布微博客

使用 'ago publish' 命令可生成 HTML 文件及 RSS 文件，通过 GitHub Pages 或类似的免费服务即可创建你的个人微博客网站。

第一次发布时，需要填写微博客名称、作者名称等信息。

- `ago publish -info` (显示微博客信息)
- `ago publish -g` (打开 GUI 窗口填写微博客信息)
- `ago publish --set-title` ([必填] 设置 RSS 的标题，即你的微博客名称)
- `ago publish --set-author` ([必填] 设置作者名)
- `ago publish --set-link` ([必填] 设置 RSS 的链接)
- `ago publish --set-website` ([选填] 设置任意网址, 通常是你的个人网站或博客的网址)

- `ago publish` (默认输出静态文件到当前目录的 'public' 文件夹，默认每页 50 条消息)
- `ago publish -out /path/to/dir -n 25` (输出静态文件到指定文件夹, 每页显示 25 条消息)

title, author, link 这三项信息都必须有内容，才能执行 `ago publish` 命令生成网站文件。但可以先随便填，生成后看看效果，以后可以随时修改这些信息。

其中 link 是指别人通过 RSS 订阅这个微博客的网址，请务必后续发布到到网上后找到正确的网址，再回头修改。

生成文件后，双击其中的 'index.html' 即可预览效果（我用了很简单的样式，懂前端的朋友可自行修改样式）。

### 自定义模板

由于 ipelago 只处理微博客（每篇博文一两句话），不处理正常博客（长文章），因此 HTML 模板可以非常简单，自带的模板一共只有 62 行。可见，这个模板是非常容易看懂的，如果有不满意的地方，也就非常容易修改。

执行 'ago publish' 命令，可以看到默认模板 (Templates) 文件夹的位置，把这个文件夹复制粘贴到另一个地方，就可以自由修改了。修改后，使用参数 '-tmpl' (或 '--templates') 指定 templates 文件夹的位置：

- `ago publish -tmpl ..my_tmpl` ('-tmpl' 后面的文件夹可以使用相对路径、也可以使用绝对路径)

注意，模板文件夹内必须包含 'index.html' 和 'atom.xml' 这两个模板文件，内容采用 Jinja2 语法。


## Tags and Search (标签与搜索)

标签必须以“井号”开头，以空格结尾，并且不超过 TagSizeLimit  
(注意：并不是加了井号就一定能形成标签，必须以 "#" 开头，以空格结尾，并且不超过长度上限才能形成标签。)

例：以下命令发表了一条消息，同时关联了标签 'cde', 由于 '#' 是特殊字符，因此消息内容需要用半角双引号括住。推荐使用 'ago post -g' 打开 GUI 窗口方便输入（在 GUI 窗口中不需要用双引号括住内容，可随意输入任何特殊字符）。

```sh
ago post "abc #cde efg"
```

- `ago search keyword` (自动优先采用 '-tag' 方式搜索，如果没有结果再自动改成 '-contain' 方式搜索)
- `ago search -tag/--by-tag [tag]` (通过标签搜索消息，效率较高)
- `ago search -contain keyword` (搜索内容包含 keyword 的消息，效率较低)

以上命令默认包括 公开(public)/隐私(private)/收藏(fav)/订阅(news) 四种消息，但都可以加 '-bucket' 参数限定只搜索其中一的消息，例如：

- `ago search abc -bucket fav` (在收藏消息中查找包含 'abc' 的消息)
- `ago search cde -bucket public` (在我的公开消息在查找包含 'cde' 的消息)

以上命令默认最多列出 9 条结果，可加参数 '-limit' 更改上限，例如：

- `ago search keyword -limit 30`

以上命令是搜索消息内容的，以下命令可搜索源与标签本身。

`ago search --all-tags` 列出全部标签
`ago search --all-tags keyword` 在全部标签中查找包含 keyword 的标签名
`ago search --all-feeds` 列出全部已订阅的源，等同 `ago news --list`
`ago search --all-feeds keyword` 查找源名称中包含 keyword 的源

例如 `ago search --all-tags java` 可以找到标签 'Java' 和 'JavaScript', 而不是查找与这些标签关联的消息。


## 特殊技巧

### 特殊的订阅方法

我遇到了一些 rss feed 受到 Cloudflare 的保护而无法通过 python requests 访问，但可以用浏览器直接访问，比如这个 <https://mstdn.jp/@nekodayo.rss>

对于这种情况，可以用浏览器访问，按 Ctrl+S 保存 rss 到本地，建议保存到一个固定的文件夹，比如我保存在 D:\rss_feeds 里。

然后就可以这样订阅 `ago news -follow D:\rss_feeds\@nekodayo.rss`

但问题也很明显，后续需要手动下载 rss 覆盖同名文件才能更新内容，先这样应付吧，以后再想别的办法。

### Zen Mode (专注模式)

我自己很喜欢这个模式，简单来说只是自动清屏而已，效果是减少浮躁，使人宁静。 'ago tl' 系列命令与 'ago news' 系列命令可使用专注模式，例如：

- `ago tl -zen`
- `ago news -zen`

也可以使用命令 'ago -zen/--toggle-zen' 切换默认开启/默认关闭 zen mode。

### Info (软件信息)

使用命令 'ago -i/--info' 可查看程序位置、版本、数据库文件位置、zen mode 是否默认打开、代理 等信息，例如：

```sh
$ ago -i/--info

[ago] D:\ComputerScience\Python\myprojects\pypelago\src\ipelago\main.py
[version] 0.0.1
[database] C:\Users\ahui\AppData\Local\github-ahui2016\pypelago\pypelago.db
[Zen Mode Always ON] False
[http_proxy] http://127.0.0.1:1081
[use_proxy] False
[repo] https://github.com/ahui2016/pypelago
```

## 参考：我的微博客

我用这个程序生成的微博客，采用自带的极简模板（我实在不擅长前端，但懂前端的人可以看上面 "自定义模板" 的章节，很容易修改）。

[blog.ai42.xyz/i/](https://blog.ai42.xyz/i/)


## 更新日志

### v0.0.5

- **fix** 修复了订阅 news.ycombinator.com/rss 时解析日期格式失败的问题。
- **fix** 修复了 'ago search -feeds' 无结果时提示消息的一个小 bug。

### v0.0.4

- **fix** 在订阅某个博客时 (<https://blog.gimo.me/index.xml>) 发现了 `<a>` 链接的文字描述里含有 `<svg>` 并因此导致提取纯文本后产生多个换行符的问题，已修复。

### v0.0.3

- **fix** 修复了 HTML 与 atom.xml 的更新日期问题（原本以执行 'ago publish' 命令的时间为准，现在以最新一条公开消息的发表日期为准）
