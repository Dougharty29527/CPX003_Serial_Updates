/boot/config.txt:

# CPi-C070WR4C

# LCD display settings
hdmi_group=2
hdmi_mode=87
hdmi_cvt 800 480 60 6 0 0 0

# Disable pcie
dtparam=pcie=off

# RTC
dtparam=i2c_arm=on
dtoverlay=i2c-rtc,ds3231

# Serial ports
dtoverlay=disable-bt
dtparam=uart0=on
dtoverlay=uart2,txd2_pin=0,rxd2_pin=1

# Configure serial ports for CP-IO board
dtoverlay=uart3,txd3_pin=4,rxd5_pin=5
dtoverlay=uart4,txd4_pin=8,rxd9_pin=9

# Audio
dtparam=audio=on
dtoverlay=audremap,pins_12_13

# USB peripherals
dtoverlay=dwc2,dr_mode=host

# Configure GPIO for CP-IO board
gpio=6-7=ip
gpio=10-11=ip
gpio=16-18=ip
gpio=19-24=op,pd,dl
gpio=45=op,pd,dl

# Enable the VC4 display driver
dtoverlay=vc4-kms-v3d,noaudio

# Disable CM4's Ethernet
# Uncomment for CPi-C070WR4C v1.0
# dtoverlay=noeth

# Remove the rainbow pattern when booting
disable_splash=1

# Remove the warnings overlay
avoid_warnings=1
dtparam=spi=on
dtoverlay=w1-gpio
enable_uart=1

# Disable cursor
cursor_blanking=1



/boot/cmdline.txt:

console=tty3 console=serial0,115200 root=PARTUUID=5a94f090-02 rootfstype=ext4 fsck.repair=yes rootwait dwc_otg.lpm_enable=0 vt.global_cursor_default=0 fbcon=map:10 quiet consoleblank=1 logo.nologo




/etc/systemd/system/gm_control_panel.service:

[Unit]
Description=Green Machine Control Panel Service
After=network.target

[Service]
WorkingDirectory=/home/cpx003/vst_gm_control_panel/vst_gm_control_panel
ExecStartPre=/bin/sleep 10
ExecStart=/home/cpx003/vst_gm_control_panel/env/bin/python3 /home/cpx003/vst_gm_control_panel/vst_gm_control_panel/main.py
Type=idle
User=cpx003
StandardOutput=inherit
Environment="DISPLAY=:0"
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
