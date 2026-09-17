# OpenWrt 25.12.5 在线编译

将本目录作为 GitHub 仓库根目录。工作流在 Actions 中手动启动，使用 Ubuntu 24.04 编译机，产物与失败日志保留 14 天。上传内容仅限本目录，不上传设备证据、备份或凭据。

当前任务编译设备证据明确报告的 qualcommax/ipq60xx 平台内核、工具链和所选软件包。包含中文 LuCI、HTTPS 管理、IPv6、防火墙、磁盘挂载、USB 存储、终端、UPnP、DDNS、SQM、OpenClash、UA3F，以及固定版本的 ARM64 Mihomo 内核。

OpenWrt、OpenClash 和 UA3F 均校验固定 Git 提交；OpenWrt feeds 使用发行版自带的固定提交配置。Mihomo 下载校验官方发行资产 SHA-256。OpenClash v0.47.116 标签中的源码 Makefile 声明版本为 0.47.110，按实际源码保留。

本流程不生成可刷写固件。官方源码没有当前 zn,m2 的设备配置；板级 DTB 的 Linux 6.12 兼容性、网络初始化、无线校准数据以及原有 UBI volume 容量仍需要完成适配。已有设备 DTB 和 FIT 配置名位于项目 reference 目录，不能据此宣称新内核已兼容。不得将其他设备的固件作为当前设备固件。

下一步镜像必须适配既有 Bootloader、ENV、启动链和分区布局。当前 kernel/rootfs/rootfs_data 的容量分别为 5713920、23998464、65265664 字节；所选插件能否装入现有容量需实际构建后评估。禁止自动扩大分区或替换 U-Boot。

## 执行

1. 使用具有写权限的 GitHub 仓库，将本目录内容提交到默认分支。
2. 在 Actions 中选择“OpenWrt 25.12.5 编译验证”，点击 Run workflow。
3. 完成后下载“OpenWrt25.12.5-编译验证”产物；失败时查看 logs/build.log。

也可在独立 Linux 编译机上运行 `bash scripts/build.sh`。脚本拒绝覆盖已有 work/openwrt 目录，不连接路由器。
