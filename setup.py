from setuptools import setup

setup(name='necroassembler',
      version='0.6.4',
      description='framework for building assemblers',
      url='https://github.com/rdeioris/necroassembler/',
      author='Roberto De Ioris',
      author_email='roberto.deioris@gmail.com',
      license='MIT',
      packages=['necroassembler', 'necroassembler.cpu',
                'necroassembler.platforms'],
      entry_points={
          'console_scripts': [
              'necro_6502=necroassembler.cpu.mos6502:AssemblerMOS6502.main',
              'necro_thumb=necroassembler.cpu.thumb:AssemblerThumb.main',
              'necro_mips32=necroassembler.cpu.thumb:AssemblerMIPS32.main',
              'necro_nes=necroassembler.platforms.nes:main',
              'necro_gb=necroassembler.platforms.gameboy:AssemblerGameboy.main',
              'necro_sms=necroassembler.platforms.sms:AssemblerSegaMasterSystem.main',
              'necro_gba=necroassembler.platforms.gba:main',
              'necro_psx=necroassembler.platforms.psx:main',
              'necro_z80=necroassembler.cpu.z80:AssemblerZ80.main',
              'necro_m68k=necroassembler.cpu.mc68000:AssemblerMC68000.main',
              'necro_8086=necroassembler.cpu.intel8086:AssemblerIntel8086.main',
              'necro_genesis=necroassembler.platforms.genesis:main'
          ],
      },
      test_suite='tests',
      zip_safe=True)
