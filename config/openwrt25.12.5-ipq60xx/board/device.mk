define Device/zn_m2
	$(call Device/FitImage)
	DEVICE_VENDOR := ZN
	DEVICE_MODEL := M2
	SOC := ipq6018
	DEVICE_DTS := ipq6018-zn-m2
	DEVICE_DTS_CONFIG := config@cp03-c1
	KERNEL_INSTALL := 1
	KERNEL_SIZE := 5580k
	IMAGE_SIZE := 98816k
	NAND_SIZE := 128m
	BLOCKSIZE := 128k
	PAGESIZE := 2048
	SUBPAGESIZE := 2048
	VID_HDR_OFFSET := 2048
	SUPPORTED_DEVICES := zn,m2
	DEVICE_PACKAGES := ipq-wifi-zn-m2 -uboot-envtools
	IMAGES := rootfs.squashfs
	IMAGE/rootfs.squashfs := append-rootfs
endef
TARGET_DEVICES += zn_m2
