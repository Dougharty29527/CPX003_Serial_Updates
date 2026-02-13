from setuptools import setup, find_packages

setup(
    name='vst_gm_control_panel',
    version='0.7.2',
    packages=find_packages(),
    install_requires=[
        'cbor2',
        'kivy',
        'kivymd',
    ]
)