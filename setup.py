from setuptools import setup

setup(name='necroassembler',
      version='0.4',
      description='framework for building assemblers',
      url='https://github.com/rdeioris/necroassembler/',
      author='Roberto De Ioris',
      author_email='roberto.deioris@gmail.com',
      license='MIT',
      packages=['necroassembler', 'necroassembler.cpu',
                'necroassembler.platforms'],
      entry_points={
          'console_scripts': [
              'necro_6502=necroassembler.cpu.mos6502:main',
              'necro_thumb=necroassembler.cpu.thumb:main',
              'necro_nes=necroassembler.platforms.nes:main',
              'necro_gb=necroassembler.platforms.gameboy:main',
              'necro_gba=necroassembler.platforms.gba:main',
              'necro_psx=necroassembler.platforms.psx:main',
              'necro_genesis=necroassembler.platforms.genesis:main'
          ],
      },
      test_suite='tests',
      zip_safe=True)
