include $(TOPDIR)/rules.mk

PKG_NAME:=mihomo-builtin
PKG_VERSION:=1.19.31
PKG_RELEASE:=1
PKG_SOURCE:=mihomo-linux-arm64-v$(PKG_VERSION).gz
PKG_SOURCE_URL:=https://github.com/MetaCubeX/mihomo/releases/download/v$(PKG_VERSION)/
PKG_HASH:=9e0f11afbf38426b8bd88fdc594678f8161c57eccb4e1b77acb12b493904f1d4
PKG_LICENSE:=GPL-3.0-only

include $(INCLUDE_DIR)/package.mk

define Package/mihomo-builtin
  SECTION:=net
  CATEGORY:=Network
  TITLE:=Pinned ARM64 Mihomo core for OpenClash
  DEPENDS:=@aarch64 +ca-bundle
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	gzip -dc $(DL_DIR)/$(PKG_SOURCE) > $(PKG_BUILD_DIR)/clash_meta
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/mihomo-builtin/install
	$(INSTALL_DIR) $(1)/etc/openclash/core
	$(INSTALL_BIN) $(PKG_BUILD_DIR)/clash_meta $(1)/etc/openclash/core/clash_meta
endef

$(eval $(call BuildPackage,mihomo-builtin))
