# Automated Jailhouse configuration

## Getting Started

To install the package in development mode:

    pip install poetry
    git submodule update --init --recursive
	poetry shell
	
	
Then copy external/automate/automate.yml to ~/.automate and adopt the 
configuration to your needs. Metadata should point to the absolute path
of the directory metadata inside external/automate. 

## Commandline interface

Check out jailhouse:

     automate-run update
	 
Build jailhouse for all boards:

     automate-run build 
	 
Build jailhouse for a specific board:

    automate-run build -b jetsontx2
	
Deploy jailhouse:

    automate-run deploy
	
Deploy jailhouse for a specific board:

    automate-run deploy -b jetsontx2

## Usage example 

 A simple example for running a completed test case on jetson-tx2 can be found in examples/jetsontx2/run.sh.
 
 # Status
 
 - Jailhouse runs on Jetson-TX2
 - Initial configuration for Boards is ongoing
 - Master Thesis for Jailhouse-Configuration is started
 
 
 ## Boards      
 
|Board                         | Available | Compatible     | SoC                              | CPU                                     |
|------------------------------|-----------|----------------|----------------------------------|-----------------------------------------|
|Asus Tinker Board S		   |   no	   |  probably	    | RK3288						   | 4x ARM Cortex-A17						 |
|Banana Pi M2 Berry			   |   no	   |  probably	    | Allwinner R40/V40				   | 4x ARM Cortex-A7						 |
|BeagleBone Black			   |   no	   |  probably	    | Sitara AM3359AZCZ100			   | 1x ARM Cortex-A8						 |
|Nvidia Jetson AGX Xavier	   |   yes	   |  probably	    | Nvidia Xavier Series SoC		   | 8x Nvidia Carmel						 |
|Nvidia Jetson TK1			   |   no	   |   yes		    | Nvidia Tegra K1				   | 4(+1) x ARM Cortex-A15					 |
|Nvidia Jetson TX2			   |   yes	   |   yes		    | Nvidia Parker SoC				   | 4x ARM Cortex-A57 + 2 x Nvidia Denver	 |
|ODROID-C1+					   |   no	   |  probably	    | Amlogic S805					   | 4x ARM Cortex-A53						 |
|ODROID-C2					   |   no	   |  probably	    | Amlogic S905					   | 4x ARM Cortex-A53						 |
|ODROID-N2					   |   no	   |  probably	    | Amlogic S922X					   | 4x ARM Cortex-A73 + 4x ARM Cortex-A53	 |
|ODROID-XU4Q				   |   no	   |   yes		    | Samsung Exynos 5422			   | 4x ARM Cortex-A15 + 4x ARM Cortex-A7	 |
|Raspberry Pi 2 Model B v1.1   |   no	   |  probably no 	| BCM2836						   | 4x ARM Cortex-A7						 |
|Raspberry Pi 3B			   |   no	   |  probably no 	| BCM2837						   | 4x ARM Cortex-A53						 |
|Raspberry Pi 3B+			   |   no	   |  probably no 	| BCM2837B0						   | 4x ARM Cortex-A53						 |
|Raspberry Pi 4B			   |   no	   |  probably no 	| BCM2711						   | 4x ARM Cortex-A72						 |
|Zynqberry					   |   yes	   |	yes		    | Xilinx Zynq XC7Z010-1CLG225C	   | 2x ARM Cortex-A9						 |
