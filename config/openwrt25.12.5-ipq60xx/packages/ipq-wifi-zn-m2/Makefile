include $(TOPDIR)/rules.mk

PKG_NAME:=ipq-wifi-zn-m2
PKG_RELEASE:=1
PKG_FLAGS:=nonshared

include $(INCLUDE_DIR)/package.mk

define Package/ipq-wifi-zn-m2
  SECTION:=firmware
  CATEGORY:=Firmware
  TITLE:=Board data read from the current zn,m2 device
  DEPENDS:=+ath11k-firmware-ipq6018
endef

define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./board-2.bin $(PKG_BUILD_DIR)/board-2.bin
endef

define Build/Configure
endef

define Build/Compile
endef

define Package/ipq-wifi-zn-m2/install
	$(INSTALL_DIR) $(1)/lib/firmware/ath11k/IPQ6018/hw1.0
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/board-2.bin $(1)/lib/firmware/ath11k/IPQ6018/hw1.0/board-2.bin
endef

$(eval $(call BuildPackage,ipq-wifi-zn-m2))
