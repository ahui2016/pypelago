# ipelago (in Python)

CLI personal microblog (命令行个人微博客)

纯命令行操作，包括两方面功能：

1. 写微博客并生成静态网站 (HTML 和 RSS)
2. 订阅别人的 RSS


## ipelago 之名

ipelago 源于群岛的英文 archipelago, 如果我们每一个人是一座孤岛，那么当我们搭建自己的微博客，大家的微博客聚在一起就可以形成群岛。


## 安装与初始化

安装非常简单，只要 `pip install ipelago` 即可。

安装后，第一次正式使用前，必须执行 'ago init [name]' 进行初始化，其中 name 是你的微博客名称，对外发布时别人可以看到。（避免每次执行命令都要初始化）

