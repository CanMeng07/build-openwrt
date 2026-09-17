# 当前设备 OpenWrt 25.12.5 构建

本目录是构建配置的唯一维护入口。设备事实来自当前192.168.10.1读取结果，见board/known-device.json及项目docs/current-device-facts.md。

源码固定OpenWrt v25.12.5；包含LuCI HTTPS和中文界面、IPv6、终端、UPnP、DDNS、SQM、USB存储、OpenClash、UA3F及内置ARM64 Mihomo。OpenClash标签v0.47.116的源码Makefile自报0.47.110；保留该差异。

板级配置包含设备树、三LAN一WAN、GPIO、NAND、USB及无线校准规则。匹配chip_id=0、board_id=255的board data通过Actions Secret ZN_M2_BOARD_DATA_GZ_B64传入并核对SHA256；不提交二进制。新系统校准规则从原有0:art偏移0x1000读取0x10000字节，原有ART不修改。

## 启动和容量

Bootloader、ENV和MTD布局不可修改。FIT固定config@cp03-c1、ARM64 gzip、load/entry=0x41000000。UBI volume固定kernel=45 LEB、rootfs=189 LEB、rootfs_data=514 LEB，每LEB126976字节；不设置autoresize。

scripts/build.sh执行完整构建，scripts/make-factory.py生成UBI，并由image_gates.py核查FIT字段、哈希、容量、UBI头和卷表CRC、固定卷布局及UBIFS superblock。静态检查通过不等于启动或恢复验证通过。

## 插件与恢复出厂行为

为满足现有容量，Mihomo、UA3F及部分OpenClash/Ruby文件放入预置overlay。清空overlay或恢复出厂设置可能移除这些文件；当前产物不能承诺重置后仍保留全部插件。实际行为未经运行验证，作为最终验收的未通过项。

## 缓存与产物

缓存仅包含公开源码下载和编译器ccache，以源码版本、配置、板级文件、包定义及脚本哈希区分；不缓存设备数据、Secret、完整工作目录或固件。

产物包括完整.ubi、SHA256、构建与容量检查JSON、软件包、最终.config和日志。Actions保留14天，不自动发布Release或刷写。最终验收见项目docs/firmware-acceptance.md。
