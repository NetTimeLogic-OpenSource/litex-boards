#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2015 Yann Sionneau <yann.sionneau@gmail.com>
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2025 Kevin Schaerer <kevin.schaerer@nettimelogic.com>
# SPDX-License-Identifier: BSD-2-Clause

from litex.build.generic_platform import *
from litex.build.xilinx import Xilinx7SeriesPlatform
from litex.build.openocd import OpenOCD

# IOs ----------------------------------------------------------------------------------------------

_io = [
    # Clk / Rst
    ("Mhz100Clk_ClkIn",    0, Pins(1)),
    ("Mhz50Clk_ClkIn", 0, Pins(1)),
    ("Mhz200Clk_ClkIn", 0, Pins(1)),
    ("Mhz400Clk_ClkIn", 0, Pins(1)),
    ("Mhz400Clk90Deg_ClkIn", 0, Pins(1)),
    ("SysRstN_RstIn", 0, Pins(1)),

    # Serial
    ("serial", 0,
        Subsignal("tx", Pins("D10")),
        Subsignal("rx", Pins("A9")),
        IOStandard("LVCMOS33")
    ),

    # SPIFlash
    ("spiflash", 0,
        Subsignal("cs_n", Pins("L13")),
        Subsignal("clk",  Pins("L16")),
        Subsignal("mosi", Pins("K17")),
        Subsignal("miso", Pins("K18")),
        Subsignal("wp",   Pins("L14")),
        Subsignal("hold", Pins("M14")),
        IOStandard("LVCMOS33"),
    ),
    ("spiflash4x", 0,
        Subsignal("cs_n", Pins("L13")),
        Subsignal("clk",  Pins("L16")),
        Subsignal("dq",   Pins("K17 K18 L14 M14")),
        IOStandard("LVCMOS33")
    ),

    # DDR3 SDRAM
    ("ddram", 0,
        Subsignal("a", Pins(
            "R2 M6 N4 T1 N6 R7 V6 U7",
            "R8 V7 R6 U6 T6 T8"),
            IOStandard("SSTL135")),
        Subsignal("ba",    Pins("R1 P4 P2"), IOStandard("SSTL135")),
        Subsignal("ras_n", Pins("P3"), IOStandard("SSTL135")),
        Subsignal("cas_n", Pins("M4"), IOStandard("SSTL135")),
        Subsignal("we_n",  Pins("P5"), IOStandard("SSTL135")),
        Subsignal("cs_n",  Pins("U8"), IOStandard("SSTL135")),
        Subsignal("dm", Pins("L1 U1"), IOStandard("SSTL135")),
        Subsignal("dq", Pins(
            "K5 L3 K3 L6 M3 M1 L4 M2",
            "V4 T5 U4 V5 V1 T3 U3 R3"),
            IOStandard("SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_p", Pins("N2 U2"),
            IOStandard("DIFF_SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("dqs_n", Pins("N1 V2"),
            IOStandard("DIFF_SSTL135"),
            Misc("IN_TERM=UNTUNED_SPLIT_40")),
        Subsignal("clk_p", Pins("U9"), IOStandard("DIFF_SSTL135")),
        Subsignal("clk_n", Pins("V9"), IOStandard("DIFF_SSTL135")),
        Subsignal("cke",   Pins("N5"), IOStandard("SSTL135")),
        Subsignal("odt",   Pins("R5"), IOStandard("SSTL135")),
        Subsignal("reset_n", Pins("K6"), IOStandard("SSTL135")),
        Misc("SLEW=FAST"),
    ),

    # MII Ethernet
    ("eth_clocks", 0,
        Subsignal("tx", Pins("H16")),
        Subsignal("rx", Pins("F15")),
        IOStandard("LVCMOS33"),
    ),
    ("eth", 0,
        Subsignal("rx_dv",   Pins("G16")),
        Subsignal("rx_er",   Pins("C17")),
        Subsignal("rx_data", Pins("D18 E17 E18 G17")),
        Subsignal("tx_en",   Pins("H15")),
        Subsignal("tx_data", Pins("H14 J14 J13 H17")),
        Subsignal("col",     Pins("D17")),
        Subsignal("crs",     Pins("G14")),
        IOStandard("LVCMOS33"),
    ),
]

# Connectors ---------------------------------------------------------------------------------------

_connectors = []

# Platform -----------------------------------------------------------------------------------------

class Platform(Xilinx7SeriesPlatform):
    default_clk_name   = "Mhz100Clk_ClkIn"
    default_clk_period = 1e9/100e6

    def __init__(self, variant="a7-35", toolchain="vivado"):
        device = {
            "a7-35":  "xc7a35ticsg324-1L",
            "a7-100": "xc7a100tcsg324-1"
        }[variant]
        Xilinx7SeriesPlatform.__init__(self, device, _io, _connectors, toolchain=toolchain)
        self.toolchain.bitstream_commands = \
            ["set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]"]
        self.toolchain.additional_commands = \
            ["write_cfgmem -force -format bin -interface spix4 -size 16 "
             "-loadbit \"up 0x0 {build_name}.bit\" -file {build_name}.bin"]
        self.add_platform_command("set_property INTERNAL_VREF 0.675 [get_iobanks 34]")

    def create_programmer(self):
        bscan_spi = "bscan_spi_xc7a100t.bit" if "xc7a100t" in self.device else "bscan_spi_xc7a35t.bit"
        return OpenOCD("openocd_xc7_ft2232.cfg", bscan_spi)

    def do_finalize(self, fragment):
        Xilinx7SeriesPlatform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("Mhz100Clk_ClkIn", loose=True), 1e9/100e6, keep=False)
