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

安装非常简单，只要 `pip install ipelago` 即可。

安装后，第一次正式使用前，必须执行 'ago init name' 进行初始化，其中 name 是你的微博客名称，对外发布时别人可以看到。


## 帮助

- `ago -h` (查看帮助消息)
- `ago post -h` (每个子命令也有详细的帮助消息)


## 初始化

- `ago init 别有洞天` (初始化，设定微博客名称为“别有洞天”)


## 写博文

- `ago post Hello World!` (写一条公开消息, 可通过 HTML 及 RSS 对外发布)
- `ago post` (发送剪贴板的内容)
- `ago post -pri/--private My password is abcd` (写一条隐私消息, 仅本地可见)
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
以下命令可区分公开/隐私/收藏 (-pub/-pri/-fav)。

- `ago tl -today` (阅读今天的消息，包括公开与隐私，不包括收藏)
- `ago tl -yesterday` (阅读昨天的消息，包括公开与隐私，不包括收藏)
- `ago tl -today -pub/--public` (阅读今天的消息, 限定公开消息)
- `ago tl -today -pri/--private` (阅读今天的消息, 限定隐私消息)
- `ago tl -today -fav/--favorite` (阅读今天的消息, 限定收藏消息)
- `ago tl -date 2022-03-15` (阅读 2022年3月15日 的消息, 默认上限 9 条)
- `ago tl -date 2022-03` (阅读 2022年3月 的消息, 默认上限 9 条)
- `ago tl -date 2022 -pri -limit 20` (阅读 2022年 的隐私消息, 最多只显示上限 20 条)
- `ago tl -count 2022-03` 统计 2022年3月 的消息条数


## 订阅 RSS

- `ago news -follow https://douchi.space/@mtfront.rss` (订阅长毛象)
- `ago news -follow https://v2ex.com/feed/create.xml -p HasTitle` (订阅V站的“分享创造”节点)
- `ago news -follow https://geeknote.net/Rei/feed.atom -p HasSummary` (订阅 geeknote)
- `ago news -follow https://sspai.com/feed -p HasTitle` (订阅少数派)

- `ago news -l/--list` (查看已订阅的 RSS 列表)

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

- `ago news -u all` (批量更新全部源)
- `ago news -u sspai` (更新 feed id 为 sspai 的源)

### 阅读消息

- `ago news` (阅读下一条消息, 完全等同 `ago news --next`)
- `ago news -first` (阅读最新一条消息)
- `ago news -next` (阅读下一条消息)
- `ago news -feed id` (阅读指定 id 的源的消息，默认上限 9 条)
- `ago news -feed id -limit 3` (阅读指定 id 的源的消息，最多显示 3 条)
- `ago news -like id` (收藏指定 id 的消息)
- `ago like id` (完全等同于 `ago news -like id`)
- `ago copy [id] -link` (复制指定 id 的消息的链接)


## 发布微博客

使用 'ago publish' 命令可生成 HTML 文件及 RSS 文件，通过 GitHub Pages 或类似的免费服务即可创建你的个人微博客网站。

第一次发布时，需要填写微博客名称、作者名称等信息。

- `ago publish -info` (显示微博客信息)
- `ago publish -g` (打开 GUI 窗口填写微博客信息)
- `ago publish --set-link` ([必填] 设置 RSS 的链接)
- `ago publish --set-website` ([选填] 设置任意网址, 通常是你的个人网站或博客的网址)

- `ago publish` (默认输出静态文件到当前目录的 'public' 文件夹，默认每页 50 条消息)
- `ago publish -out /path/to/dir -n 25` (输出静态文件指定文件夹, 每页显示 25 条消息)

## 源码

常用命令如上所示，更详细的说明以及源码请看 [https://github.com/ahui2016/pypelago](https://github.com/ahui2016/pypelago)
