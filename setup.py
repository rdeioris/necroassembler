from setuptools import setup

setup(name='necroassembler',
      version='0.2',
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
              'necro_gb=necroassembler.cpu.gameboy:main',
              'necro_gba=necroassembler.platforms.gba:main'
          ],
      },
      zip_safe=True)
