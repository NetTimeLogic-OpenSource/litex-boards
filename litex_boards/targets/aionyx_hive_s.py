#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2020 Antmicro <www.antmicro.com>
# Copyright (c) 2022 Victor Suarez Rovere <suarezvictor@gmail.com>
# Copyright (c) 2025 Kevin Schaerer <kevin.schaerer@nettimelogic.com>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *

from litex_boards.platforms import aionyx_hive_s

from litex.soc.cores.clock import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

from litedram.modules import MT41K128M16
from litedram.phy import s7ddrphy

from liteeth.phy.mii import LiteEthPHYMII

# CRG ----------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq, with_dram=True, with_rst=True):
        self.rst    = Signal()
        self.cd_sys = ClockDomain()
        if with_dram:
            self.cd_sys4x     = ClockDomain()
            self.cd_sys4x_dqs = ClockDomain()
            self.cd_idelay    = ClockDomain()

        # # #

        # Clk & Rst
        self.comb += self.cd_sys.clk.eq(platform.request("Mhz100Clk_ClkIn"))
        self.comb += self.rst.eq(~platform.request("SysRstN_RstIn"))
        self.specials += AsyncResetSynchronizer(self.cd_sys, self.rst)

        # PLL.
        if with_dram:
            self.comb += self.cd_sys4x.clk.eq(platform.request("Mhz400Clk_ClkIn"))
            self.comb += self.cd_sys4x_dqs.clk.eq(platform.request("Mhz400Clk90Deg_ClkIn"))
            self.comb += self.cd_idelay.clk.eq(platform.request("Mhz200Clk_ClkIn"))

        # IdelayCtrl.
        if with_dram:
            self.idelayctrl = S7IDELAYCTRL(self.cd_idelay)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, variant="a7-35", toolchain="vivado", sys_clk_freq=100e6,
        with_ethernet   = False,
        eth_ip          = "192.168.1.50",
        remote_ip       = None,
        eth_dynamic_ip  = False,
        with_spi_flash  = False,
        **kwargs):
        platform = aionyx_hive_s.Platform(variant=variant, toolchain=toolchain)

        # CRG --------------------------------------------------------------------------------------
        with_dram = (kwargs.get("integrated_main_ram_size", 0) == 0)
        self.crg  = _CRG(platform, sys_clk_freq, with_dram)

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq, ident="LiteX SoC on NTL Hive-S", **kwargs)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            self.ddrphy = s7ddrphy.A7DDRPHY(platform.request("ddram"),
                memtype        = "DDR3",
                nphases        = 4,
                sys_clk_freq   = sys_clk_freq)
            self.add_sdram("sdram",
                phy           = self.ddrphy,
                module        = MT41K128M16(sys_clk_freq, "1:4"),
                l2_cache_size = kwargs.get("l2_size", 8192)
            )

        # Ethernet --------------------------------------------------------------------------------
        if with_ethernet:
            self.ethphy = LiteEthPHYMII(
                clock_pads = self.platform.request("eth_clocks"),
                pads       = self.platform.request("eth"))
            self.add_ethernet(phy=self.ethphy, dynamic_ip=eth_dynamic_ip, local_ip=eth_ip, remote_ip=remote_ip)

        # SPI Flash --------------------------------------------------------------------------------
        if with_spi_flash:
            from litespi.modules import S25FL128L
            from litespi.opcodes import SpiNorFlashOpCodes as Codes
            self.add_spi_flash(mode="4x", module=S25FL128L(Codes.READ_1_1_4), rate="1:2", with_master=True)

# Build --------------------------------------------------------------------------------------------

def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=aionyx_hive_s.Platform, description="LiteX SoC on Arty A7.")
    parser.add_target_argument("--flash",          action="store_true",       help="Flash bitstream.")
    parser.add_target_argument("--variant",        default="a7-35",           help="Board variant (a7-35 or a7-100).")
    parser.add_target_argument("--sys-clk-freq",   default=100e6, type=float, help="System clock frequency.")
    parser.add_target_argument("--with-ethernet",  action="store_true",       help="Enable Ethernet support.")
    parser.add_target_argument("--eth-ip",         default="192.168.1.50",    help="Ethernet IP address.")
    parser.add_target_argument("--remote-ip",      default="192.168.1.100",   help="Remote IP address of TFTP server.")
    parser.add_target_argument("--eth-dynamic-ip", action="store_true",       help="Enable dynamic Ethernet IP addresses setting.")
    parser.add_target_argument("--with-spi-flash", action="store_true",       help="Enable SPI Flash (MMAPed).")
    args = parser.parse_args()

    soc = BaseSoC(
        variant        = args.variant,
        toolchain      = args.toolchain,
        sys_clk_freq   = args.sys_clk_freq,
        with_ethernet  = args.with_ethernet,
        eth_ip         = args.eth_ip,
        remote_ip      = args.remote_ip,
        eth_dynamic_ip = args.eth_dynamic_ip,
        with_spi_flash = args.with_spi_flash,
        **parser.soc_argdict
    )

    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(builder.get_bitstream_filename(mode="sram"))

    if args.flash:
        prog = soc.platform.create_programmer()
        prog.flash(0, builder.get_bitstream_filename(mode="flash"))

if __name__ == "__main__":
    main()
