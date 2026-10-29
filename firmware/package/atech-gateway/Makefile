include $(TOPDIR)/rules.mk

PKG_NAME:=atech-gateway
PKG_VERSION:=0.1.0
PKG_RELEASE:=1

include $(INCLUDE_DIR)/package.mk

define Package/atech-gateway
  SECTION:=net
  CATEGORY:=Network
  TITLE:=ATECH Walchem gateway interface and carrier control
  DEPENDS:=+luci +luci-ssl +luci-proto-qmi +uqmi +kmod-usb-net-qmi-wwan +kmod-usb-serial-option +kmod-usb2 +kmod-i2c-mt7628 +kmod-i2c-dev +i2c-tools +rpcd +jsonfilter +lrzsz
endef

define Build/Compile
endef

define Package/atech-gateway/install
	$(CP) ./files/* $(1)/
	chmod 0755 $(1)/etc/uci-defaults/99-atech-gateway
	chmod 0755 $(1)/etc/init.d/gateway-hardware
	chmod 0755 $(1)/usr/sbin/gateway-hardware
	chmod 0755 $(1)/usr/libexec/rpcd/atech.gateway
endef

$(eval $(call BuildPackage,atech-gateway))
